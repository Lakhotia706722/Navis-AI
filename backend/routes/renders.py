"""Render job routes (start, status, cancel)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project, RenderJob, RenderJobStatusEnum, User
from backend.routes.auth import get_current_user
from backend.routes.projects import get_project_or_404
from backend.schemas import RenderJobResponse, RenderJobWithScenes
from backend.celery_app import app as celery_app
from backend.tasks.dummy_task import planning_task

router = APIRouter(prefix="/api/renders", tags=["renders"])


@router.post("/{project_id}/start", response_model=RenderJobResponse)
async def start_render(
    project_id: int,
    render_mode: str = "full",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a new render job for a project.
    
    Args:
        project_id: Project to render
        render_mode: "preview" (fast, 16 samples) or "full" (production, 128 samples)
        
    Returns:
        RenderJobResponse with job ID and status
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Verify project exists and user owns it
    project = get_project_or_404(project_id, user, db)

    # Validate render_mode
    if render_mode not in ["preview", "full"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="render_mode must be 'preview' or 'full'",
        )

    # Create render job
    render_job = RenderJob(
        project_id=project_id,
        status=RenderJobStatusEnum.QUEUED,
        render_mode=render_mode,
    )
    db.add(render_job)
    db.commit()
    db.refresh(render_job)

    # Enqueue Celery task (Phase 3: now uses real planning pipeline)
    celery_task = planning_task.delay(render_job.id, project.prompt)
    render_job.celery_task_id = celery_task.id
    db.commit()
    db.refresh(render_job)

    return render_job


@router.get("/{render_job_id}", response_model=RenderJobWithScenes)
async def get_render_job(
    render_job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get render job status and details."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
    if not render_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Render job not found",
        )

    # Verify ownership via project
    project = get_project_or_404(render_job.project_id, user, db)

    return render_job


@router.post("/{render_job_id}/cancel", response_model=RenderJobResponse)
async def cancel_render(
    render_job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cancel a running render job."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
    if not render_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Render job not found",
        )

    # Verify ownership
    project = get_project_or_404(render_job.project_id, user, db)

    # Only cancel if not already done or failed
    if render_job.status in [RenderJobStatusEnum.DONE, RenderJobStatusEnum.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel job with status {render_job.status}",
        )

    # Revoke Celery task if in queue
    if render_job.celery_task_id:
        celery_app.control.revoke(render_job.celery_task_id, terminate=True)

    render_job.status = RenderJobStatusEnum.FAILED
    render_job.error_message = "Cancelled by user"
    db.commit()
    db.refresh(render_job)

    return render_job
