"""
Workspace management routes — Phase 11.

Covers:
  - Workspace CRUD
  - Member management (list, remove, change role)
  - Invite flow (send, accept, revoke)
  - Ownership transfer
  - Workspace-level usage rollup (Step 11.4)
"""
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import (
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceInvite,
    WorkspaceRoleEnum,
    InviteStatusEnum,
    Project,
    UsageLog,
)
from backend.permissions import WorkspaceContext, get_workspace_context, require_workspace_role
from backend.routes.auth import get_current_user
from backend.schemas import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceMemberResponse,
    WorkspaceInviteCreate,
    WorkspaceInviteResponse,
    MemberRoleUpdate,
    WorkspaceUsageStats,
)
from backend.notifications import notification_manager, NotificationType

INVITE_EXPIRY_DAYS = 7

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ── Role rank helper ─────────────────────────────────────────────

ROLE_RANK = {
    WorkspaceRoleEnum.VIEWER: 1,
    WorkspaceRoleEnum.MEMBER: 2,
    WorkspaceRoleEnum.ADMIN: 3,
    WorkspaceRoleEnum.OWNER: 4,
}


def _rank(role: WorkspaceRoleEnum) -> int:
    return ROLE_RANK[role]


# ════════════════════════════════════════════════════════════════
# Workspace CRUD
# ════════════════════════════════════════════════════════════════

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new workspace. The caller becomes its owner."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    workspace = Workspace(name=payload.name, owner_id=user.id)
    db.add(workspace)
    db.flush()  # get workspace.id

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRoleEnum.OWNER,
        invited_by=None,
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("", response_model=List[WorkspaceResponse])
async def list_my_workspaces(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all workspaces the current user belongs to."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    memberships = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user.id)
        .all()
    )
    workspace_ids = [m.workspace_id for m in memberships]
    workspaces = db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all()
    return workspaces


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.VIEWER)),
):
    """Get workspace details. Requires viewer role."""
    return ctx.workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """Update workspace name. Requires admin role."""
    if payload.name is not None:
        ctx.workspace.name = payload.name
    db.commit()
    db.refresh(ctx.workspace)
    return ctx.workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.OWNER)),
):
    """Delete workspace. Owner only. All projects in the workspace are also deleted."""
    db.delete(ctx.workspace)
    db.commit()


# ════════════════════════════════════════════════════════════════
# Member Management
# ════════════════════════════════════════════════════════════════

@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.VIEWER)),
):
    """List workspace members. Requires viewer role."""
    members = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .all()
    )
    return members


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberResponse)
async def change_member_role(
    workspace_id: int,
    user_id: int,
    payload: MemberRoleUpdate,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """Change a member's role. Requires admin role. Cannot promote to owner or demote owner."""
    if payload.role == WorkspaceRoleEnum.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the /transfer endpoint to transfer ownership",
        )

    target = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if target.role == WorkspaceRoleEnum.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change the owner's role via this endpoint — use /transfer instead",
        )

    # Admin cannot elevate someone to a role above their own
    if _rank(payload.role) > _rank(ctx.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign a role higher than your own",
        )

    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """Remove a member from the workspace. Requires admin role. Cannot remove owner."""
    if user_id == ctx.workspace.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove the workspace owner",
        )

    target = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    db.delete(target)
    db.commit()


@router.post("/{workspace_id}/transfer", response_model=WorkspaceResponse)
async def transfer_ownership(
    workspace_id: int,
    new_owner_user_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.OWNER)),
):
    """Transfer workspace ownership to another member. Owner only."""
    new_owner_member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == new_owner_user_id,
        )
        .first()
    )
    if not new_owner_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user is not a member of this workspace",
        )

    # Demote current owner → admin
    ctx.member.role = WorkspaceRoleEnum.ADMIN
    # Promote new owner
    new_owner_member.role = WorkspaceRoleEnum.OWNER
    # Update workspace.owner_id
    ctx.workspace.owner_id = new_owner_user_id

    db.commit()
    db.refresh(ctx.workspace)
    return ctx.workspace


# ════════════════════════════════════════════════════════════════
# Invite Flow (Step 11.3)
# ════════════════════════════════════════════════════════════════

@router.post("/{workspace_id}/invites", response_model=WorkspaceInviteResponse,
             status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: int,
    payload: WorkspaceInviteCreate,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """
    Invite a user by email. Requires admin role.
    Invited role must be ≤ inviter's own role.
    Reuses Phase 9 notification infrastructure to send the invite email.
    """
    if payload.role == WorkspaceRoleEnum.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite someone directly as owner — use /transfer",
        )

    if _rank(payload.role) > _rank(ctx.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot invite someone to a role higher than your own",
        )

    # Check if already a member
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        already_member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == existing_user.id,
            )
            .first()
        )
        if already_member:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace",
            )

    # Expire/cancel any existing pending invite for same email+workspace
    db.query(WorkspaceInvite).filter(
        WorkspaceInvite.workspace_id == workspace_id,
        WorkspaceInvite.email == payload.email,
        WorkspaceInvite.status == InviteStatusEnum.PENDING,
    ).update({"status": InviteStatusEnum.REVOKED})

    invite = WorkspaceInvite(
        email=payload.email,
        workspace_id=workspace_id,
        role=payload.role,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(days=INVITE_EXPIRY_DAYS),
        invited_by=ctx.user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # Send invite email via Phase 9 notification infra
    try:
        import asyncio
        asyncio.create_task(
            notification_manager.send_notification(
                notification_type=NotificationType.WORKSPACE_INVITE,
                render_job_id=0,
                project_id=0,
                data={
                    "invite_email": payload.email,
                    "workspace_name": ctx.workspace.name,
                    "role": payload.role.value,
                    "invite_token": invite.token,
                    "expires_at": invite.expires_at.isoformat(),
                    "invited_by": ctx.user.email,
                },
            )
        )
    except Exception:
        pass  # Notification failure does not block invite creation

    return invite


@router.post("/invites/{token}/accept", response_model=WorkspaceMemberResponse)
async def accept_invite(
    token: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Accept a workspace invite. The caller must be authenticated.
    Token is single-use; expires after INVITE_EXPIRY_DAYS days.
    """
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    invite = (
        db.query(WorkspaceInvite)
        .filter(WorkspaceInvite.token == token)
        .first()
    )
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    if invite.status != InviteStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invite already {invite.status.value}",
        )

    if invite.expires_at < datetime.utcnow():
        invite.status = InviteStatusEnum.EXPIRED
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite has expired")

    if invite.email.lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invite was sent to a different email address",
        )

    # Check not already a member
    existing = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == invite.workspace_id,
            WorkspaceMember.user_id == user.id,
        )
        .first()
    )
    if existing:
        invite.status = InviteStatusEnum.ACCEPTED
        db.commit()
        return existing

    member = WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=user.id,
        role=invite.role,
        invited_by=invite.invited_by,
    )
    db.add(member)
    invite.status = InviteStatusEnum.ACCEPTED
    db.commit()
    db.refresh(member)
    return member


@router.get("/{workspace_id}/invites", response_model=List[WorkspaceInviteResponse])
async def list_invites(
    workspace_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """List all pending invites. Requires admin role."""
    invites = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.workspace_id == workspace_id,
            WorkspaceInvite.status == InviteStatusEnum.PENDING,
        )
        .all()
    )
    return invites


@router.delete("/{workspace_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    workspace_id: int,
    invite_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """Revoke a pending invite. Requires admin role."""
    invite = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.id == invite_id,
            WorkspaceInvite.workspace_id == workspace_id,
        )
        .first()
    )
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    if invite.status != InviteStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invite is already {invite.status.value}",
        )

    invite.status = InviteStatusEnum.REVOKED
    db.commit()


# ════════════════════════════════════════════════════════════════
# Workspace-Level Usage Rollup (Step 11.4)
# ════════════════════════════════════════════════════════════════

@router.get("/{workspace_id}/usage", response_model=WorkspaceUsageStats)
async def get_workspace_usage(
    workspace_id: int,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_workspace_role(WorkspaceRoleEnum.ADMIN)),
):
    """
    Aggregate usage across all projects in this workspace.
    Requires admin role (viewers/members cannot see cost rollup — see rbac.md).
    """
    result = (
        db.query(
            func.coalesce(func.sum(UsageLog.gpt_tokens), 0).label("total_gpt_tokens"),
            func.coalesce(func.sum(UsageLog.tts_characters), 0).label("total_tts_characters"),
            func.coalesce(func.sum(UsageLog.render_minutes), 0).label("total_render_minutes"),
            func.coalesce(func.sum(UsageLog.cost), 0.0).label("total_cost_usd"),
        )
        .filter(UsageLog.workspace_id == workspace_id)
        .first()
    )

    project_count = (
        db.query(func.count(Project.id))
        .filter(Project.workspace_id == workspace_id)
        .scalar()
    )

    return WorkspaceUsageStats(
        workspace_id=workspace_id,
        total_gpt_tokens=result.total_gpt_tokens,
        total_tts_characters=result.total_tts_characters,
        total_render_minutes=result.total_render_minutes,
        total_cost_usd=float(result.total_cost_usd),
        project_count=project_count,
    )
