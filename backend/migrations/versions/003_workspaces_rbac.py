"""Phase 11: Workspaces, workspace_members, workspace_invites + workspace_id on projects.

Revision ID: 003
Revises: 002
Create Date: 2026-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

# Role enum values
ROLE_VALUES = ("owner", "admin", "member", "viewer")
INVITE_STATUS_VALUES = ("pending", "accepted", "revoked", "expired")


def upgrade() -> None:
    # ── 1. workspaces ──────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "plan_tier",
            sa.String(50),
            nullable=False,
            server_default="free",
            comment="Billing tier stub — enforced in Phase 12",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_workspaces_id", "workspaces", ["id"])
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # ── 2. workspace_members ────────────────────────────────────────
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(*ROLE_VALUES, name="workspacerole"),
            nullable=False,
        ),
        sa.Column(
            "invited_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index("ix_workspace_members_id", "workspace_members", ["id"])
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    # ── 3. workspace_invites ────────────────────────────────────────
    op.create_table(
        "workspace_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(*ROLE_VALUES, name="workspacerole"),
            nullable=False,
        ),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*INVITE_STATUS_VALUES, name="invitestatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "invited_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_workspace_invites_id", "workspace_invites", ["id"])
    op.create_index("ix_workspace_invites_token", "workspace_invites", ["token"], unique=True)
    op.create_index("ix_workspace_invites_email", "workspace_invites", ["email"])

    # ── 4. projects.workspace_id (nullable first for migration) ─────
    op.add_column(
        "projects",
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=True,   # temporarily nullable; backfilled below; made NOT NULL in 004
        ),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])

    # ── 5. usage_logs.workspace_id (denormalised, nullable) ─────────
    op.add_column(
        "usage_logs",
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_usage_logs_workspace_id", "usage_logs", ["workspace_id"])


def downgrade() -> None:
    # Reverse in dependency order
    op.drop_index("ix_usage_logs_workspace_id", "usage_logs")
    op.drop_column("usage_logs", "workspace_id")

    op.drop_index("ix_projects_workspace_id", "projects")
    op.drop_column("projects", "workspace_id")

    op.drop_index("ix_workspace_invites_email", "workspace_invites")
    op.drop_index("ix_workspace_invites_token", "workspace_invites")
    op.drop_index("ix_workspace_invites_id", "workspace_invites")
    op.drop_table("workspace_invites")

    op.drop_index("ix_workspace_members_user_id", "workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", "workspace_members")
    op.drop_index("ix_workspace_members_id", "workspace_members")
    op.drop_table("workspace_members")

    op.drop_index("ix_workspaces_owner_id", "workspaces")
    op.drop_index("ix_workspaces_id", "workspaces")
    op.drop_table("workspaces")

    # Drop custom enums (PostgreSQL only)
    sa.Enum(name="workspacerole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="invitestatus").drop(op.get_bind(), checkfirst=True)
