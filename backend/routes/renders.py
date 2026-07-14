"""Render job routes — workspace-scoped (Phase 11)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import RenderJob, RenderJobStatusEnum, WorkspaceRoleEnum
from backend.permissions import WorkspaceContext, get_project_workspace_context, require_workspace_role
from backend.schemas import RenderJobResponse, RenderJobWithScenes
from backend.celery_app import app as celery_app
from backend.tasks.dummy_task import planning_task

router = APIRouter(prefix="/api/renders", tags=["renders"])


def _get_render_and_project(render_job_id: int, ctx: WorkspaceContext, db: Session):
    """Fetch render job and verify its project belongs to the active workspace."""
    render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
    if not render_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Render job not found")
    # Verify ownership via workspace
    get_project_workspace_context(render_job.project_id, ctx, db)
    return render_job


@router.post("/{project_id}/start", response_model=RenderJobResponse)
async def start_render(
    project_id: int,
    render_mode: str = "full",
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.MEMBER)),
):
    """Start a new render job. Requires member role."""
    project = get_project_workspace_context(project_id, ctx, db)

    if render_mode not in ("preview", "full"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="render_mode must be 'preview' or 'full'",
        )

    render_job = RenderJob(
        project_id=project_id,
        status=RenderJobStatusEnum.QUEUED,
        render_mode=render_mode,
    )
    db.add(render_job)
    db.commit()
    db.refresh(render_job)

    celery_task = planning_task.delay(render_job.id, project.prompt)
    render_job.celery_task_id = celery_task.id
    db.commit()
    db.refresh(render_job)
    return render_job


@router.get("/{render_job_id}", response_model=RenderJobWithScenes)
async def get_render_job(
    render_job_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.VIEWER)),
):
    """Get render job status. Requires viewer role."""
    return _get_render_and_project(render_job_id, ctx, db)


@router.post("/{render_job_id}/cancel", response_model=RenderJobResponse)
async def cancel_render(
    render_job_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.MEMBER)),
):
    """Cancel a running render. Requires member role."""
    render_job = _get_render_and_project(render_job_id, ctx, db)

    if render_job.status in (RenderJobStatusEnum.DONE, RenderJobStatusEnum.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel job with status {render_job.status}",
        )

    if render_job.celery_task_id:
        celery_app.control.revoke(render_job.celery_task_id, terminate=True)

    render_job.status = RenderJobStatusEnum.FAILED
    render_job.error_message = "Cancelled by user"
    db.commit()
    db.refresh(render_job)
    return render_job
