"""Celery task for Blender headless rendering."""
import logging
import subprocess
import os
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from backend.celery_app import app
from backend.database import engine
from backend.models import RenderJob, RenderJobStatusEnum, Scene
from backend.config import settings
from backend.storage import s3_client

logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@app.task(bind=True, name="render_task")
def render_task(self, render_job_id: int):
    """
    Blender headless rendering task.

    Renders all scenes for a render job to PNG frames.

    Args:
        render_job_id: Render job to process
    """
    db = SessionLocal()
    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        if not render_job:
            logger.error(f"Render job {render_job_id} not found")
            return

        logger.info(f"Starting render task for render_job {render_job_id}")

        # Move to rendering stage
        render_job.status = RenderJobStatusEnum.RENDERING
        render_job.progress_percent = 60
        db.commit()
        logger.info(f"Render job {render_job_id} moved to RENDERING (60%)")

        # Get all scenes for this render job
        scenes = db.query(Scene).filter(Scene.render_job_id == render_job_id).order_by(Scene.scene_number).all()

        if not scenes:
            logger.warning(f"No scenes found for render job {render_job_id}")
            render_job.status = RenderJobStatusEnum.FAILED
            render_job.error_message = "No scenes to render"
            render_job.completed_at = datetime.utcnow()
            db.commit()
            return

        logger.info(f"Found {len(scenes)} scenes to render")

        # Create output directory
        output_dir = f"/render_output/render-{render_job_id}"
        os.makedirs(output_dir, exist_ok=True)

        total_frames = 0

        # Render each scene
        for scene_idx, scene in enumerate(scenes):
            try:
                logger.info(f"Rendering scene {scene.scene_number}: {scene.name}")

                scene_output_dir = os.path.join(output_dir, f"scene-{scene.scene_number:02d}")
                os.makedirs(scene_output_dir, exist_ok=True)

                # Call Blender headless renderer
                success = render_scene_with_blender(
                    scene_json=scene.scene_json,
                    output_dir=scene_output_dir,
                    render_job_id=render_job_id,
                    scene_number=scene.scene_number,
                )

                if not success:
                    raise Exception(f"Blender render failed for scene {scene.scene_number}")

                # Count output frames
                frames = len([f for f in os.listdir(scene_output_dir) if f.endswith(".png")])
                total_frames += frames
                logger.info(f"✓ Scene {scene.scene_number} rendered: {frames} frames")

                # Update progress
                progress = 60 + int(30 * (scene_idx + 1) / len(scenes))
                render_job.progress_percent = progress
                db.commit()

            except Exception as e:
                logger.error(f"Failed to render scene {scene.scene_number}: {e}")
                render_job.status = RenderJobStatusEnum.FAILED
                render_job.error_message = f"Scene {scene.scene_number} render failed: {str(e)}"
                render_job.completed_at = datetime.utcnow()
                db.commit()
                raise

        # Move to assembling stage (FFmpeg will compose in Phase 7)
        render_job.status = RenderJobStatusEnum.ASSEMBLING
        render_job.progress_percent = 90
        db.commit()
        logger.info(f"Render job {render_job_id} moved to ASSEMBLING (90%), {total_frames} total frames")

        # Enqueue compose task (Phase 7)
        from backend.tasks.compose_task import compose_task
        compose_task.delay(render_job_id)

        return {
            "render_job_id": render_job_id,
            "status": "rendering_complete",
            "total_frames": total_frames,
            "scenes": len(scenes),
        }

    except Exception as e:
        logger.error(f"Error in render_task: {e}", exc_info=True)
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        if render_job:
            render_job.status = RenderJobStatusEnum.FAILED
            render_job.error_message = f"Rendering failed: {str(e)}"
            render_job.completed_at = datetime.utcnow()
            db.commit()
        raise

    finally:
        db.close()


def render_scene_with_blender(
    scene_json: dict,
    output_dir: str,
    render_job_id: int,
    scene_number: int,
) -> bool:
    """
    Invoke headless Blender to render a scene.

    Args:
        scene_json: Scene definition (from database)
        output_dir: Directory to save PNG frames
        render_job_id: For logging
        scene_number: For logging

    Returns:
        True if successful, False otherwise
    """
    # Write scene JSON to temp file
    temp_json = f"/tmp/scene-{render_job_id}-{scene_number}.json"
    with open(temp_json, "w") as f:
        json.dump(scene_json, f)

    try:
        # Call Blender Python script
        blender_script = os.path.join(os.path.dirname(__file__), "..", "blender", "render_scene.py")

        cmd = [
            settings.blender_executable,
            "--background",  # Headless
            "--factory-startup",  # No user settings
            "--python-exit-code", "1",  # Exit with code on error
            "--python", blender_script,  # Run script
            "--",  # Separator for script args
            temp_json,
            output_dir,
            str(render_job_id),
            str(scene_number),
        ]

        logger.info(f"Running Blender: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.render_timeout_seconds,
        )

        if result.returncode != 0:
            logger.error(f"Blender render failed: {result.stderr}")
            return False

        logger.info(f"Blender render succeeded")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"Blender render timed out after {settings.render_timeout_seconds}s")
        return False

    except Exception as e:
        logger.error(f"Failed to invoke Blender: {e}")
        return False

    finally:
        if os.path.exists(temp_json):
            os.remove(temp_json)
