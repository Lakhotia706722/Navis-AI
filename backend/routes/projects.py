"""Project routes — workspace-scoped (Phase 11)."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project, RenderJob, WorkspaceRoleEnum
from backend.permissions import (
    WorkspaceContext,
    get_project_workspace_context,
    require_workspace_role,
)
from backend.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithRenders,
    RenderJobResponse,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ── helpers ──────────────────────────────────────────────────────

def _get_project(project_id: int, ctx: WorkspaceContext, db: Session) -> Project:
    """Fetch project and verify it belongs to the active workspace."""
    return get_project_workspace_context(project_id, ctx, db)


# ── routes ───────────────────────────────────────────────────────

@router.post("", response_model=ProjectResponse)
async def create_project(
    project_create: ProjectCreate,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.MEMBER)),
):
    """Create a new project in the active workspace. Requires member role."""
    project = Project(
        user_id=ctx.user.id,
        workspace_id=ctx.workspace.id,
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
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.VIEWER)),
):
    """List all projects in the active workspace. Requires viewer role."""
    projects = (
        db.query(Project)
        .filter(Project.workspace_id == ctx.workspace.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return projects


@router.get("/{project_id}", response_model=ProjectWithRenders)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.VIEWER)),
):
    """Get a specific project with its render jobs. Requires viewer role."""
    return _get_project(project_id, ctx, db)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.MEMBER)),
):
    """Update a project. Requires member role."""
    project = _get_project(project_id, ctx, db)

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
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """Delete a project. Requires admin role."""
    project = _get_project(project_id, ctx, db)
    db.delete(project)
    db.commit()


@router.get("/{project_id}/renders", response_model=List[RenderJobResponse])
async def list_render_jobs(
    project_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.VIEWER)),
):
    """List all render jobs for a project. Requires viewer role."""
    _get_project(project_id, ctx, db)
    return (
        db.query(RenderJob)
        .filter(RenderJob.project_id == project_id)
        .order_by(RenderJob.created_at.desc())
        .all()
    )
