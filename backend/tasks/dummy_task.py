"""Celery tasks for planning + composing pipelines."""
import logging
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from backend.celery_app import app
from backend.database import engine
from backend.models import RenderJob, RenderJobStatusEnum
from ai.orchestrator import run_planning_pipeline
from ai.composing_orchestrator import run_composing_pipeline

logger = logging.getLogger(__name__)

# Create a session factory for Celery tasks
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@app.task(bind=True, name="planning_task")
def planning_task(self, render_job_id: int, prompt: str):
    """
    Planning pipeline task: script → storyboard → scene plan → scenes in DB.

    Replaces dummy_planning_task in Phase 3.

    Args:
        render_job_id: Render job to process
        prompt: User's video request prompt
    """
    db = SessionLocal()
    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        if not render_job:
            logger.error(f"Render job {render_job_id} not found")
            return

        logger.info(f"Starting planning task for render_job {render_job_id}")

        # Move to planning stage
        render_job.status = RenderJobStatusEnum.PLANNING
        render_job.progress_percent = 10
        render_job.started_at = datetime.utcnow()
        db.commit()
        logger.info(f"Render job {render_job_id} moved to PLANNING (10%)")

        # Run the planning pipeline
        output, cost_stats = run_planning_pipeline(render_job, prompt, db)

        logger.info(f"Planning complete: {len(output.scene_plan.scenes)} scenes")

        # Enqueue composing task (Phase 4)
        composing_task.delay(render_job_id, output.script.dict())

        return {
            "render_job_id": render_job_id,
            "status": "planning_complete",
            "scenes": len(output.scene_plan.scenes),
            "gpt_tokens": cost_stats["gpt_tokens"],
        }

    except Exception as e:
        logger.error(f"Error in planning_task: {e}", exc_info=True)
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        if render_job:
            render_job.status = RenderJobStatusEnum.FAILED
            render_job.error_message = f"Planning failed: {str(e)}"
            render_job.completed_at = datetime.utcnow()
            db.commit()
        raise

    finally:
        db.close()


@app.task(bind=True, name="composing_task")
def composing_task(self, render_job_id: int, script_dict: dict):
    """
    Composing pipeline task: TTS + subtitles.

    Enqueued after planning_task completes.

    Args:
        render_job_id: Render job to process
        script_dict: Script object (as dict, from planning_task)
    """
    db = SessionLocal()
    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        if not render_job:
            logger.error(f"Render job {render_job_id} not found")
            return

        logger.info(f"Starting composing task for render_job {render_job_id}")

        # Move to composing stage
        render_job.status = RenderJobStatusEnum.COMPOSING
        render_job.progress_percent = 30
        db.commit()
        logger.info(f"Render job {render_job_id} moved to COMPOSING (30%)")

        # Convert dict back to Script object
        from ai.schemas import Script

        script = Script(**script_dict)

        # Run composing pipeline
        output, cost_stats = run_composing_pipeline(render_job, script, db)

        logger.info(
            f"Composing complete: {cost_stats['tts_chars']} TTS chars, "
            f"audio={output['audio_path']}, srt={output['srt_path']}"
        )

        # Enqueue rendering task (Phase 6)
        from backend.tasks.render_task import render_task
        render_task.delay(render_job_id)

        return {
            "render_job_id": render_job_id,
            "status": "composing_complete",
            "tts_chars": cost_stats["tts_chars"],
            "audio_path": output["audio_path"],
        }

    except Exception as e:
        logger.error(f"Error in composing_task: {e}", exc_info=True)
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        if render_job:
            render_job.status = RenderJobStatusEnum.FAILED
            render_job.error_message = f"Composing failed: {str(e)}"
            render_job.completed_at = datetime.utcnow()
            db.commit()
        raise

    finally:
        db.close()
