"""
Dry-run script: shows what Phase 11 migration 004 would do without writing anything.

Usage:
  python scripts/dry_run_migration.py
  python scripts/dry_run_migration.py postgresql://maritime_user:maritime_pass@localhost:5432/maritime_studio
"""
import sys
import sqlalchemy as sa


def dry_run(database_url: str) -> None:
    engine = sa.create_engine(database_url)
    with engine.connect() as conn:
        users = conn.execute(
            sa.text("""
                SELECT u.id, u.email, u.full_name, COUNT(p.id) AS project_count
                FROM users u
                LEFT JOIN projects p ON p.user_id = u.id
                GROUP BY u.id, u.email, u.full_name
                ORDER BY u.id
            """)
        ).fetchall()

    print("\n" + "=" * 72)
    print("DRY-RUN: Phase 11 — workspaces migration (no data written)")
    print("=" * 72)

    if not users:
        print("No users found in database.")
        return

    print(f"\n{'ID':<6} {'Email':<36} {'Workspace Name':<30} {'Projects'}")
    print("-" * 72)

    workspaces_to_create = 0
    total_projects = 0
    no_projects = []

    for u in users:
        if u.project_count == 0:
            no_projects.append(u)
            continue
        workspace_name = f"{u.full_name or u.email}'s Workspace"
        print(f"{u.id:<6} {u.email:<36} {workspace_name:<30} {u.project_count}")
        workspaces_to_create += 1
        total_projects += u.project_count

    print("-" * 72)
    print(f"\n✅ Would CREATE:   {workspaces_to_create} workspace(s)")
    print(f"✅ Would CREATE:   {workspaces_to_create} workspace_members row(s) (role=owner)")
    print(f"✅ Would UPDATE:   {total_projects} project(s) with workspace_id")
    print(f"✅ Would UPDATE:   usage_logs rows backfilled with workspace_id")

    if no_projects:
        print(f"\nℹ️  {len(no_projects)} user(s) with no projects — no workspace created:")
        for u in no_projects:
            print(f"   - {u.email}")

    print("\n✅ REVERSIBLE: migration 004 downgrade clears workspace_id and")
    print("   deletes created workspaces/members.")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else \
        "postgresql://maritime_user:maritime_pass@localhost:5432/maritime_studio"
    dry_run(url)
