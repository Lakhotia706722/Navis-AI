"""Project routes (CRUD + render management)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project, RenderJob, User
from backend.routes.auth import get_current_user
from backend.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithRenders,
    RenderJobResponse,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_or_404(project_id: int, user: User, db: Session) -> Project:
    """Helper to get project and verify ownership."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    if project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        )
    return project


@router.post("", response_model=ProjectResponse)
async def create_project(
    project_create: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new project."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    project = Project(
        user_id=user.id,
        title=project_create.title,
        description=project_create.description,
        prompt=project_create.prompt,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all projects for the current user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    projects = db.query(Project).filter(Project.user_id == user.id).all()
    return projects


@router.get("/{project_id}", response_model=ProjectWithRenders)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific project with render jobs."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    project = get_project_or_404(project_id, user, db)
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a project."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    project = get_project_or_404(project_id, user, db)

    if project_update.title is not None:
        project.title = project_update.title
    if project_update.description is not None:
        project.description = project_update.description
    if project_update.prompt is not None:
        project.prompt = project_update.prompt

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a project (cascades to render_jobs, scenes, usage_logs)."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    project = get_project_or_404(project_id, user, db)
    db.delete(project)
    db.commit()
    return None


@router.get("/{project_id}/renders", response_model=List[RenderJobResponse])
async def list_render_jobs(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all render jobs for a project."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    project = get_project_or_404(project_id, user, db)
    render_jobs = db.query(RenderJob).filter(RenderJob.project_id == project_id).all()
    return render_jobs
