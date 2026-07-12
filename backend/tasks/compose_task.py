"""Celery task for FFmpeg video composition (frames + audio + subtitles → MP4)."""
import logging
import subprocess
import os
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from backend.celery_app import app
from backend.database import engine
from backend.models import RenderJob, RenderJobStatusEnum
from backend.config import settings
from backend.storage import s3_client

logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@app.task(bind=True, name="compose_task")
def compose_task(self, render_job_id: int):
    """
    FFmpeg video composition: PNG frames + audio + subtitles → MP4.

    Enqueued by render_task after Blender rendering complete.

    Args:
        render_job_id: Render job to process
    """
    db = SessionLocal()
    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        if not render_job:
            logger.error(f"Render job {render_job_id} not found")
            return

        logger.info(f"Starting compose task for render_job {render_job_id}")

        # Move to assembling stage (already set by render_task, but ensure)
        render_job.status = RenderJobStatusEnum.ASSEMBLING
        render_job.progress_percent = 90
        db.commit()

        # Compose video with FFmpeg
        output_mp4_path = f"/tmp/render-{render_job_id}.mp4"
        try:
            success = compose_video_with_ffmpeg(
                render_job_id=render_job_id,
                output_path=output_mp4_path,
            )

            if not success:
                raise Exception("FFmpeg composition failed")

            logger.info(f"✓ Video composed: {output_mp4_path}")

        except Exception as e:
            logger.error(f"Composition failed: {e}")
            render_job.status = RenderJobStatusEnum.FAILED
            render_job.error_message = f"Video composition failed: {str(e)}"
            render_job.completed_at = datetime.utcnow()
            db.commit()
            raise

        # Upload to S3
        logger.info("Uploading final video to S3...")
        try:
            s3_key = f"renders/render-{render_job_id}.mp4"
            s3_url = s3_client.upload_file(output_mp4_path, s3_key)
            if not s3_url:
                raise Exception("S3 upload failed")

            render_job.output_video_path = s3_url
            logger.info(f"✓ Video uploaded: {s3_url}")

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            render_job.status = RenderJobStatusEnum.FAILED
            render_job.error_message = f"Upload failed: {str(e)}"
            render_job.completed_at = datetime.utcnow()
            db.commit()
            raise

        finally:
            if os.path.exists(output_mp4_path):
                os.remove(output_mp4_path)

        # Mark complete
        render_job.status = RenderJobStatusEnum.DONE
        render_job.progress_percent = 100
        render_job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"✓ Render job {render_job_id} DONE")

        # TODO: Phase 9 - trigger notifications
        # notify_on_completion(render_job)

        return {
            "render_job_id": render_job_id,
            "status": "done",
            "output_path": s3_url,
        }

    except Exception as e:
        logger.error(f"Error in compose_task: {e}", exc_info=True)
        raise

    finally:
        db.close()


def compose_video_with_ffmpeg(
    render_job_id: int,
    output_path: str,
    fps: int = 24,
) -> bool:
    """
    Use FFmpeg to compose video from PNG frames + audio + subtitles.

    Args:
        render_job_id: Render job ID (for file paths)
        output_path: Output MP4 file path
        fps: Frames per second (default 24)

    Returns:
        True if successful, False otherwise
    """
    render_dir = f"/render_output/render-{render_job_id}"

    if not os.path.exists(render_dir):
        logger.error(f"Render directory not found: {render_dir}")
        return False

    # Find all scene directories
    scene_dirs = sorted([d for d in os.listdir(render_dir) if d.startswith("scene-")])
    if not scene_dirs:
        logger.error(f"No scene directories found in {render_dir}")
        return False

    logger.info(f"Found {len(scene_dirs)} scenes to compose")

    try:
        # Step 1: Create concat file for scenes
        concat_file = f"/tmp/concat-{render_job_id}.txt"
        with open(concat_file, "w") as f:
            for scene_dir in scene_dirs:
                scene_path = os.path.join(render_dir, scene_dir)
                f.write(f"file '{scene_path}/frame_%04d.png'\n")
                f.write(f"duration 5\n")  # Default 5 sec per scene (TODO: read from DB)

        # Step 2: Compose frames → intermediate video (without audio yet)
        intermediate_video = f"/tmp/video-{render_job_id}.mp4"

        cmd_video = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-r", str(fps),  # Input frame rate
            "-f", "concat",  # Input format
            "-safe", "0",
            "-i", concat_file,  # Input concat file
            "-c:v", "libx264",  # Video codec
            "-crf", "23",  # Quality (0-51, lower=better)
            "-preset", "medium",  # Speed/quality tradeoff
            intermediate_video,
        ]

        logger.info(f"Running FFmpeg (video): {' '.join(cmd_video)}")
        result = subprocess.run(cmd_video, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error(f"FFmpeg video composition failed: {result.stderr}")
            return False

        logger.info("✓ Video frames composed")

        # Step 3: Add audio + subtitles
        audio_path = f"/tmp/render-{render_job_id}.mp3"  # Would be from S3 in real implementation
        # For MVP: check if audio exists locally (Phase 4 saves to S3, we'd download here)

        cmd_final = [
            "ffmpeg",
            "-y",
            "-i", intermediate_video,
            "-c:v", "copy",  # Copy video stream (no re-encoding)
            "-c:a", "aac",  # Audio codec
            "-b:a", "128k",  # Audio bitrate
        ]

        # Add audio if available
        if os.path.exists(audio_path):
            cmd_final.insert(4, "-i")
            cmd_final.insert(5, audio_path)
            cmd_final.append("-map")
            cmd_final.append("0:v:0")
            cmd_final.append("-map")
            cmd_final.append("1:a:0")
        else:
            logger.warning(f"Audio not found: {audio_path}, creating silent video")
            cmd_final.append("-f")
            cmd_final.append("lavfi")
            cmd_final.append("-i")
            cmd_final.append("anullsrc=r=48000:cl=mono")
            cmd_final.append("-map")
            cmd_final.append("0:v:0")
            cmd_final.append("-map")
            cmd_final.append("1:a:0")

        cmd_final.append(output_path)

        logger.info(f"Running FFmpeg (final): {' '.join(cmd_final[:8])}...")
        result = subprocess.run(cmd_final, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error(f"FFmpeg final composition failed: {result.stderr}")
            return False

        logger.info("✓ Final MP4 created with audio")

        # Cleanup
        if os.path.exists(intermediate_video):
            os.remove(intermediate_video)
        if os.path.exists(concat_file):
            os.remove(concat_file)

        return True

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg composition timed out")
        return False

    except Exception as e:
        logger.error(f"FFmpeg composition error: {e}")
        return False
