"""Admin routes for project overview and monitoring."""
import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Project, RenderJob, RenderJobStatusEnum, UsageLog
from backend.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/projects")
async def list_all_projects(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Admin: List all projects with stats (minimal security check for demo).

    Returns:
        List of all projects with render job counts and costs.
    """
    # In production, check if user is admin role
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    projects = db.query(Project).all()

    result = []
    for project in projects:
        render_count = db.query(RenderJob).filter(RenderJob.project_id == project.id).count()
        total_cost = (
            db.query(func.sum(UsageLog.cost))
            .filter(UsageLog.project_id == project.id)
            .scalar() or 0.0
        )

        result.append({
            "id": project.id,
            "title": project.title,
            "owner_email": project.owner.email,
            "render_count": render_count,
            "total_cost": round(total_cost, 4),
            "created_at": project.created_at.isoformat(),
        })

    return result


@router.get("/render-jobs")
async def list_all_render_jobs(
    status_filter: Optional[str] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Admin: List all render jobs with status filtering.

    Args:
        status_filter: Filter by status (e.g., "done", "failed")

    Returns:
        List of render jobs across all projects.
    """
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    query = db.query(RenderJob).order_by(RenderJob.created_at.desc())

    if status_filter:
        try:
            status_enum = RenderJobStatusEnum(status_filter)
            query = query.filter(RenderJob.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status: {status_filter}",
            )

    renders = query.limit(100).all()

    result = []
    for render in renders:
        result.append({
            "id": render.id,
            "project_id": render.project_id,
            "project_title": render.project.title,
            "status": render.status.value,
            "progress_percent": render.progress_percent,
            "render_mode": render.render_mode,
            "created_at": render.created_at.isoformat(),
            "started_at": render.started_at.isoformat() if render.started_at else None,
            "completed_at": render.completed_at.isoformat() if render.completed_at else None,
        })

    return result


@router.get("/stats")
async def get_system_stats(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Admin: Get system-wide statistics.

    Returns:
        Summary stats on projects, renders, costs.
    """
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Total projects and users
    total_projects = db.query(Project).count()
    total_users = db.query(User).count()
    total_renders = db.query(RenderJob).count()

    # Render status distribution
    done_count = db.query(RenderJob).filter(RenderJob.status == RenderJobStatusEnum.DONE).count()
    failed_count = db.query(RenderJob).filter(RenderJob.status == RenderJobStatusEnum.FAILED).count()
    in_progress_count = total_renders - done_count - failed_count

    # Total costs
    total_cost = db.query(func.sum(UsageLog.cost)).scalar() or 0.0

    # Average cost per project
    avg_cost_per_project = (
        db.query(func.avg(func.coalesce(UsageLog.cost, 0)))
        .filter(UsageLog.project_id.isnot(None))
        .scalar() or 0.0
    )

    # Renders in last 24 hours
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    renders_24h = db.query(RenderJob).filter(RenderJob.created_at >= one_day_ago).count()

    return {
        "summary": {
            "total_users": total_users,
            "total_projects": total_projects,
            "total_renders": total_renders,
            "renders_in_24h": renders_24h,
        },
        "render_status_distribution": {
            "done": done_count,
            "failed": failed_count,
            "in_progress": in_progress_count,
        },
        "costs": {
            "total_cost_usd": round(total_cost, 2),
            "avg_cost_per_project_usd": round(avg_cost_per_project, 4),
        },
    }


@router.get("/costs")
async def get_cost_summary(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Admin: Get cost breakdown by component.

    Returns:
        Costs split by GPT, TTS, and rendering.
    """
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    total_gpt_tokens = db.query(func.sum(UsageLog.gpt_tokens)).scalar() or 0
    total_tts_chars = db.query(func.sum(UsageLog.tts_characters)).scalar() or 0
    total_render_mins = db.query(func.sum(UsageLog.render_minutes)).scalar() or 0

    # Cost calculations
    gpt_cost = (total_gpt_tokens / 1000.0) * 0.015
    tts_cost = (total_tts_chars / 1000.0) * 0.015
    render_cost = 0.0  # Local rendering

    return {
        "usage": {
            "gpt_tokens": total_gpt_tokens,
            "tts_characters": total_tts_chars,
            "render_minutes": total_render_mins,
        },
        "costs": {
            "gpt_cost_usd": round(gpt_cost, 4),
            "tts_cost_usd": round(tts_cost, 4),
            "render_cost_usd": round(render_cost, 4),
            "total_cost_usd": round(gpt_cost + tts_cost + render_cost, 4),
        },
    }
