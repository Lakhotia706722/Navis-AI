"""Initial schema: users, projects, renders, assets, usage tracking

Revision ID: 001
Revises: 
Create Date: 2026-07-12 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    # Projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("queued", "planning", "composing", "rendering", "assembling", "done", "failed", name="renderjobstatusenum"), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_user_id"), "projects", ["user_id"], unique=False)

    # Render jobs table
    op.create_table(
        "render_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.Enum("queued", "planning", "composing", "rendering", "assembling", "done", "failed", name="renderjobstatusenum"), nullable=False, server_default="queued"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("render_mode", sa.String(length=50), nullable=False, server_default="full"),
        sa.Column("output_video_path", sa.String(length=512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("celery_task_id"),
    )
    op.create_index(op.f("ix_render_jobs_id"), "render_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_render_jobs_project_id"), "render_jobs", ["project_id"], unique=False)

    # Scenes table
    op.create_table(
        "scenes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("render_job_id", sa.Integer(), nullable=False),
        sa.Column("scene_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("scene_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["render_job_id"], ["render_jobs.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scenes_id"), "scenes", ["id"], unique=False)
    op.create_index(op.f("ix_scenes_render_job_id"), "scenes", ["render_job_id"], unique=False)

    # Assets table
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_format", sa.String(length=10), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False, server_default="1.0"),
        sa.Column("licensing_info", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_assets_category"), "assets", ["category"], unique=False)
    op.create_index(op.f("ix_assets_id"), "assets", ["id"], unique=False)
    op.create_index(op.f("ix_assets_name"), "assets", ["name"], unique=True)

    # Usage logs table
    op.create_table(
        "usage_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("usage_type", sa.String(length=50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_logs_id"), "usage_logs", ["id"], unique=False)
    op.create_index(op.f("ix_usage_logs_usage_type"), "usage_logs", ["usage_type"], unique=False)

    # Notification hooks table
    op.create_table(
        "notification_hooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("hook_type", sa.String(length=50), nullable=False),
        sa.Column("destination", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_hooks_id"), "notification_hooks", ["id"], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f("ix_notification_hooks_id"), table_name="notification_hooks")
    op.drop_table("notification_hooks")
    op.drop_index(op.f("ix_usage_logs_usage_type"), table_name="usage_logs")
    op.drop_index(op.f("ix_usage_logs_id"), table_name="usage_logs")
    op.drop_table("usage_logs")
    op.drop_index(op.f("ix_assets_name"), table_name="assets")
    op.drop_index(op.f("ix_assets_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_category"), table_name="assets")
    op.drop_table("assets")
    op.drop_index(op.f("ix_scenes_render_job_id"), table_name="scenes")
    op.drop_index(op.f("ix_scenes_id"), table_name="scenes")
    op.drop_table("scenes")
    op.drop_index(op.f("ix_render_jobs_project_id"), table_name="render_jobs")
    op.drop_index(op.f("ix_render_jobs_id"), table_name="render_jobs")
    op.drop_table("render_jobs")
    op.drop_index(op.f("ix_projects_user_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
