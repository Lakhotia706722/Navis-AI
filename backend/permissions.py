"""
Workspace RBAC permission middleware — Phase 11.

Enforcement boundary: route-level FastAPI dependency injection.

Design rationale:
  Every protected route declares `Depends(require_workspace_role(minimum_role))`.
  This returns a WorkspaceContext (user + workspace + member row) that the route
  can use freely. The check is done BEFORE the handler body runs — no service-layer
  checks needed, existing Phase 2 routes are wrapped by adding one Depends() param.

403 vs 404 policy (see docs/rbac.md):
  - Non-member accessing any workspace resource → 403 (prevents ID enumeration)
  - Resource genuinely not found → 404
  - Insufficient role for the action → 403
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Workspace, WorkspaceMember, WorkspaceRoleEnum
from backend.routes.auth import get_current_user


# ─────────────────────────────────────────────────────────────────
# Context object passed into route handlers after permission check
# ─────────────────────────────────────────────────────────────────

@dataclass
class WorkspaceContext:
    """Carries authenticated user + resolved workspace + their membership role."""

    user: User
    workspace: Workspace
    member: WorkspaceMember

    @property
    def role(self) -> WorkspaceRoleEnum:
        return self.member.role

    def has_role(self, minimum: WorkspaceRoleEnum) -> bool:
        return self.role >= minimum


# ─────────────────────────────────────────────────────────────────
# Core dependency: resolve workspace from X-Workspace-ID header
# ─────────────────────────────────────────────────────────────────

def get_workspace_context(
    x_workspace_id: Optional[int] = Header(None, alias="X-Workspace-ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceContext:
    """
    Resolve the active workspace from the X-Workspace-ID request header.

    If X-Workspace-ID is omitted the user's first owned workspace is used,
    which means single-workspace users never need to pass the header (backward compat).
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated")

    if x_workspace_id is not None:
        workspace = db.query(Workspace).filter(Workspace.id == x_workspace_id).first()
        if not workspace:
            # 403, not 404 — avoids confirming whether the workspace ID exists
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Workspace not found or access denied")
    else:
        # Default: first workspace where the user is owner
        member_row = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.role == WorkspaceRoleEnum.OWNER,
            )
            .order_by(WorkspaceMember.workspace_id)
            .first()
        )
        if not member_row:
            # User has no workspace yet — this can happen right after registration
            # before migration 004 ran for them. Return a 403 with a helpful message.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No workspace found. Please create or join a workspace.",
            )
        workspace = db.query(Workspace).filter(
            Workspace.id == member_row.workspace_id
        ).first()

    # Verify user is a member of that workspace
    member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Workspace not found or access denied")

    return WorkspaceContext(user=user, workspace=workspace, member=member)


# ─────────────────────────────────────────────────────────────────
# Role-check dependency factory
# ─────────────────────────────────────────────────────────────────

def require_workspace_role(minimum_role: WorkspaceRoleEnum):
    """
    FastAPI dependency factory.

    Usage:
        @router.post("/projects")
        def create(ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.MEMBER))):
            ...
    """
    def _check(ctx: WorkspaceContext = Depends(get_workspace_context)) -> WorkspaceContext:
        if not ctx.has_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return ctx
    return _check


# ─────────────────────────────────────────────────────────────────
# Pre-built role dependencies (shorthand for common checks)
# ─────────────────────────────────────────────────────────────────

# Any authenticated workspace member (viewer+)
RequireViewer  = Depends(require_workspace_role(WorkspaceRoleEnum.VIEWER))
# Can create projects, start renders (member+)
RequireMember  = Depends(require_workspace_role(WorkspaceRoleEnum.MEMBER))
# Can invite, remove members, delete projects (admin+)
RequireAdmin   = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN))
# Workspace destructive actions (owner only)
RequireOwner   = Depends(require_workspace_role(WorkspaceRoleEnum.OWNER))


# ─────────────────────────────────────────────────────────────────
# Project-scoped context (resolves project AND verifies workspace membership)
# ─────────────────────────────────────────────────────────────────

def get_project_workspace_context(
    project_id: int,
    ctx: WorkspaceContext,
    db: Session,
):
    """
    Verify that a project belongs to the active workspace.
    Returns the project or raises 404/403.
    """
    from backend.models import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Project not found")
    if project.workspace_id != ctx.workspace.id:
        # Project exists but not in this workspace → 403 (not 404)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Workspace not found or access denied")
    return project
