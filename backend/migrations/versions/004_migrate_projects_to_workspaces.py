"""Phase 11: Backfill projects into workspaces and make workspace_id NOT NULL.

For every user who owns at least one project, this migration:
  1. Creates a personal workspace  "{name}'s Workspace"
  2. Inserts a workspace_members row with role=owner
  3. Sets workspace_id on all their projects
  4. Backfills workspace_id on usage_logs via project
  5. Alters projects.workspace_id to NOT NULL

Revision ID: 004
Revises: 003
Create Date: 2026-07-14 00:00:00.000000

DRY-RUN: Before running against real data, call the dry_run() helper:
  from backend.migrations.versions.004_migrate_projects_to_workspaces import dry_run
  dry_run("postgresql://maritime_user:maritime_pass@localhost:5432/maritime_studio")
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────────────────
# Dry-run helper — call this manually before applying migration to real data
# ─────────────────────────────────────────────────────────────────────────────

def dry_run(database_url: str | None = None) -> None:
    """Print what the migration WOULD do without writing anything."""
    if database_url:
        engine = sa.create_engine(database_url)
        conn = engine.connect()
    else:
        conn = op.get_bind()

    users = conn.execute(
        sa.text("""
            SELECT u.id, u.email, u.full_name, COUNT(p.id) AS project_count
            FROM users u
            LEFT JOIN projects p ON p.user_id = u.id
            GROUP BY u.id, u.email, u.full_name
            ORDER BY u.id
        """)
    ).fetchall()

    print("\n" + "=" * 70)
    print("DRY-RUN: Phase 11 workspace migration")
    print("=" * 70)
    print(f"{'ID':<6} {'Email':<35} {'Name':<25} {'Projects':<10}")
    print("-" * 70)

    total_workspaces = 0
    total_members = 0
    total_projects = 0

    for u in users:
        workspace_name = f"{u.full_name or u.email}'s Workspace"
        print(f"{u.id:<6} {u.email:<35} {workspace_name:<25} {u.project_count:<10}")
        if u.project_count > 0:
            total_workspaces += 1
            total_members += 1
            total_projects += u.project_count

    print("-" * 70)
    print(f"Would create:  {total_workspaces} workspaces")
    print(f"Would create:  {total_members} workspace_members (all owner role)")
    print(f"Would migrate: {total_projects} projects → workspace_id")

    # Users with NO projects (won't get a workspace in this migration)
    no_project_users = [u for u in users if u.project_count == 0]
    if no_project_users:
        print(f"\nNOTE: {len(no_project_users)} user(s) have no projects — no workspace created for them.")
        for u in no_project_users:
            print(f"  - {u.email}")

    print("=" * 70 + "\n")

    if database_url:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Actual migration
# ─────────────────────────────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()

    # Fetch every user who has at least one project
    rows = conn.execute(
        sa.text("""
            SELECT DISTINCT u.id, u.email, u.full_name
            FROM users u
            INNER JOIN projects p ON p.user_id = u.id
            ORDER BY u.id
        """)
    ).fetchall()

    now = datetime.utcnow()

    for user in rows:
        workspace_name = f"{user.full_name or user.email}'s Workspace"

        # 1. Create workspace
        result = conn.execute(
            sa.text("""
                INSERT INTO workspaces (name, owner_id, plan_tier, created_at)
                VALUES (:name, :owner_id, 'free', :created_at)
                RETURNING id
            """),
            {"name": workspace_name, "owner_id": user.id, "created_at": now},
        )
        workspace_id = result.fetchone()[0]

        # 2. Create owner membership
        conn.execute(
            sa.text("""
                INSERT INTO workspace_members (workspace_id, user_id, role, invited_by, joined_at)
                VALUES (:workspace_id, :user_id, 'owner', NULL, :joined_at)
            """),
            {"workspace_id": workspace_id, "user_id": user.id, "joined_at": now},
        )

        # 3. Assign workspace_id to all projects belonging to this user
        conn.execute(
            sa.text("""
                UPDATE projects
                SET workspace_id = :workspace_id
                WHERE user_id = :user_id
            """),
            {"workspace_id": workspace_id, "user_id": user.id},
        )

        # 4. Backfill workspace_id on usage_logs via project
        conn.execute(
            sa.text("""
                UPDATE usage_logs ul
                SET workspace_id = :workspace_id
                FROM projects p
                WHERE ul.project_id = p.id
                  AND p.user_id = :user_id
            """),
            {"workspace_id": workspace_id, "user_id": user.id},
        )

    # 5. Make projects.workspace_id NOT NULL now that all rows are filled
    op.alter_column("projects", "workspace_id", nullable=False)


def downgrade() -> None:
    conn = op.get_bind()

    # Revert NOT NULL constraint
    op.alter_column("projects", "workspace_id", nullable=True)

    # Clear backfilled values
    conn.execute(sa.text("UPDATE projects SET workspace_id = NULL"))
    conn.execute(sa.text("UPDATE usage_logs SET workspace_id = NULL"))

    # Drop workspace_members and workspaces rows created by this migration
    # (workspace_members will cascade-delete when workspace rows are deleted)
    conn.execute(sa.text("DELETE FROM workspaces"))
