"""
Step 11.2 — Permission boundary tests.

Covers every cell in the RBAC matrix (docs/rbac.md):
  - owner-can, admin-can, member-can/cannot, viewer-cannot, non-member-cannot
  - 403 (not 404) for non-members and insufficient-role actors
"""
import pytest
from fastapi import status


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════

def _headers(token: str, workspace_id: int | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-ID"] = str(workspace_id)
    return h


def _create_project(client, token: str, workspace_id: int, title: str = "Test Project") -> int:
    r = client.post(
        "/api/projects",
        headers=_headers(token, workspace_id),
        json={"title": title, "prompt": "test prompt"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ════════════════════════════════════════════════════════════════
# Workspace access — non-member
# ════════════════════════════════════════════════════════════════

class TestNonMemberAccess:
    """Non-members must receive 403, not 404."""

    def test_non_member_cannot_view_workspace(self, client, owner, second_user):
        ws_id = owner["workspace_id"]
        r = client.get(
            f"/api/workspaces/{ws_id}",
            headers=_headers(second_user["token"], ws_id),
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_non_member_cannot_list_projects(self, client, owner, second_user):
        ws_id = owner["workspace_id"]
        r = client.get("/api/projects",
                       headers=_headers(second_user["token"], ws_id))
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_non_member_cannot_create_project(self, client, owner, second_user):
        ws_id = owner["workspace_id"]
        r = client.post(
            "/api/projects",
            headers=_headers(second_user["token"], ws_id),
            json={"title": "Hack", "prompt": "p"},
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_non_member_cannot_access_project_directly(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])

        # Register a totally new user
        client.post("/api/auth/register",
                    json={"email": "outsider@example.com", "password": "x"})
        r = client.post("/api/auth/login",
                        json={"email": "outsider@example.com", "password": "x"})
        outsider_token = r.json()["access_token"]

        r = client.get(
            f"/api/projects/{pid}",
            headers=_headers(outsider_token, ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN


# ════════════════════════════════════════════════════════════════
# Project CRUD by role
# ════════════════════════════════════════════════════════════════

class TestProjectPermissions:

    # ── Create ──────────────────────────────────────────────────

    def test_owner_can_create_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"], "Owner Project")
        assert pid > 0

    def test_admin_can_create_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["admin_token"], ws["workspace_id"], "Admin Project")
        assert pid > 0

    def test_member_can_create_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["member_token"], ws["workspace_id"], "Member Project")
        assert pid > 0

    def test_viewer_cannot_create_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.post(
            "/api/projects",
            headers=_headers(ws["viewer_token"], ws["workspace_id"]),
            json={"title": "Viewer Try", "prompt": "p"},
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    # ── Read ────────────────────────────────────────────────────

    def test_viewer_can_read_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.get(f"/api/projects/{pid}",
                       headers=_headers(ws["viewer_token"], ws["workspace_id"]))
        assert r.status_code == 200

    def test_viewer_can_list_projects(self, client, workspace_with_roles):
        ws = workspace_with_roles
        _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.get("/api/projects",
                       headers=_headers(ws["viewer_token"], ws["workspace_id"]))
        assert r.status_code == 200
        assert len(r.json()) >= 1

    # ── Update ──────────────────────────────────────────────────

    def test_owner_can_update_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.put(f"/api/projects/{pid}",
                       headers=_headers(ws["owner_token"], ws["workspace_id"]),
                       json={"title": "Updated"})
        assert r.status_code == 200
        assert r.json()["title"] == "Updated"

    def test_admin_can_update_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.put(f"/api/projects/{pid}",
                       headers=_headers(ws["admin_token"], ws["workspace_id"]),
                       json={"title": "Admin Updated"})
        assert r.status_code == 200

    def test_member_can_update_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.put(f"/api/projects/{pid}",
                       headers=_headers(ws["member_token"], ws["workspace_id"]),
                       json={"title": "Member Updated"})
        assert r.status_code == 200

    def test_viewer_cannot_update_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.put(f"/api/projects/{pid}",
                       headers=_headers(ws["viewer_token"], ws["workspace_id"]),
                       json={"title": "Viewer Try"})
        assert r.status_code == status.HTTP_403_FORBIDDEN

    # ── Delete ──────────────────────────────────────────────────

    def test_owner_can_delete_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.delete(f"/api/projects/{pid}",
                          headers=_headers(ws["owner_token"], ws["workspace_id"]))
        assert r.status_code == status.HTTP_204_NO_CONTENT

    def test_admin_can_delete_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.delete(f"/api/projects/{pid}",
                          headers=_headers(ws["admin_token"], ws["workspace_id"]))
        assert r.status_code == status.HTTP_204_NO_CONTENT

    def test_member_cannot_delete_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.delete(f"/api/projects/{pid}",
                          headers=_headers(ws["member_token"], ws["workspace_id"]))
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_delete_project(self, client, workspace_with_roles):
        ws = workspace_with_roles
        pid = _create_project(client, ws["owner_token"], ws["workspace_id"])
        r = client.delete(f"/api/projects/{pid}",
                          headers=_headers(ws["viewer_token"], ws["workspace_id"]))
        assert r.status_code == status.HTTP_403_FORBIDDEN


# ════════════════════════════════════════════════════════════════
# Workspace member management by role
# ════════════════════════════════════════════════════════════════

class TestMemberManagementPermissions:

    def test_viewer_can_list_members(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.get(f"/api/workspaces/{ws['workspace_id']}/members",
                       headers=_headers(ws["viewer_token"], ws["workspace_id"]))
        assert r.status_code == 200
        assert len(r.json()) >= 4  # owner, admin, member, viewer

    def test_member_cannot_invite(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.post(
            f"/api/workspaces/{ws['workspace_id']}/invites",
            headers=_headers(ws["member_token"], ws["workspace_id"]),
            json={"email": "newguy@example.com", "role": "viewer"},
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_invite(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.post(
            f"/api/workspaces/{ws['workspace_id']}/invites",
            headers=_headers(ws["viewer_token"], ws["workspace_id"]),
            json={"email": "newguy2@example.com", "role": "viewer"},
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_invite_viewer(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.post(
            f"/api/workspaces/{ws['workspace_id']}/invites",
            headers=_headers(ws["admin_token"], ws["workspace_id"]),
            json={"email": "newviewer@example.com", "role": "viewer"},
        )
        assert r.status_code in (200, 201)

    def test_admin_cannot_invite_owner(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.post(
            f"/api/workspaces/{ws['workspace_id']}/invites",
            headers=_headers(ws["admin_token"], ws["workspace_id"]),
            json={"email": "tryowner@example.com", "role": "owner"},
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_member_cannot_remove_member(self, client, workspace_with_roles, second_user):
        ws = workspace_with_roles
        # Get viewer user_id
        r = client.get(f"/api/workspaces/{ws['workspace_id']}/members",
                       headers=_headers(ws["owner_token"], ws["workspace_id"]))
        viewer_entry = next(m for m in r.json() if "viewer" in str(m["role"]))
        viewer_user_id = viewer_entry["user_id"]

        r = client.delete(
            f"/api/workspaces/{ws['workspace_id']}/members/{viewer_user_id}",
            headers=_headers(ws["member_token"], ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_remove_member(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.get(f"/api/workspaces/{ws['workspace_id']}/members",
                       headers=_headers(ws["owner_token"], ws["workspace_id"]))
        viewer_entry = next(m for m in r.json() if "viewer" in str(m["role"]))
        viewer_user_id = viewer_entry["user_id"]

        r = client.delete(
            f"/api/workspaces/{ws['workspace_id']}/members/{viewer_user_id}",
            headers=_headers(ws["admin_token"], ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_remove_owner(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.get(f"/api/workspaces/{ws['workspace_id']}/members",
                       headers=_headers(ws["owner_token"], ws["workspace_id"]))
        owner_entry = next(m for m in r.json() if "owner" in str(m["role"]))
        owner_user_id = owner_entry["user_id"]

        r = client.delete(
            f"/api/workspaces/{ws['workspace_id']}/members/{owner_user_id}",
            headers=_headers(ws["admin_token"], ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN


# ════════════════════════════════════════════════════════════════
# Workspace settings by role
# ════════════════════════════════════════════════════════════════

class TestWorkspaceSettingsPermissions:

    def test_owner_can_rename_workspace(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.patch(
            f"/api/workspaces/{ws['workspace_id']}",
            headers=_headers(ws["owner_token"], ws["workspace_id"]),
            json={"name": "New Name"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_admin_can_rename_workspace(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.patch(
            f"/api/workspaces/{ws['workspace_id']}",
            headers=_headers(ws["admin_token"], ws["workspace_id"]),
            json={"name": "Admin Renamed"},
        )
        assert r.status_code == 200

    def test_member_cannot_rename_workspace(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.patch(
            f"/api/workspaces/{ws['workspace_id']}",
            headers=_headers(ws["member_token"], ws["workspace_id"]),
            json={"name": "Member Try"},
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_rename_workspace(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.patch(
            f"/api/workspaces/{ws['workspace_id']}",
            headers=_headers(ws["viewer_token"], ws["workspace_id"]),
            json={"name": "Viewer Try"},
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_cannot_delete_workspace(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.delete(
            f"/api/workspaces/{ws['workspace_id']}",
            headers=_headers(ws["admin_token"], ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_owner_can_delete_workspace(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.delete(
            f"/api/workspaces/{ws['workspace_id']}",
            headers=_headers(ws["owner_token"], ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_204_NO_CONTENT


# ════════════════════════════════════════════════════════════════
# Usage rollup permissions
# ════════════════════════════════════════════════════════════════

class TestUsagePermissions:

    def test_admin_can_view_workspace_usage(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.get(
            f"/api/workspaces/{ws['workspace_id']}/usage",
            headers=_headers(ws["admin_token"], ws["workspace_id"]),
        )
        assert r.status_code == 200
        data = r.json()
        assert "total_cost_usd" in data
        assert "workspace_id" in data

    def test_owner_can_view_workspace_usage(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.get(
            f"/api/workspaces/{ws['workspace_id']}/usage",
            headers=_headers(ws["owner_token"], ws["workspace_id"]),
        )
        assert r.status_code == 200

    def test_member_cannot_view_workspace_usage(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.get(
            f"/api/workspaces/{ws['workspace_id']}/usage",
            headers=_headers(ws["member_token"], ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_view_workspace_usage(self, client, workspace_with_roles):
        ws = workspace_with_roles
        r = client.get(
            f"/api/workspaces/{ws['workspace_id']}/usage",
            headers=_headers(ws["viewer_token"], ws["workspace_id"]),
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN


# ════════════════════════════════════════════════════════════════
# Invite flow end-to-end (Step 11.3)
# ════════════════════════════════════════════════════════════════

class TestInviteFlow:

    def test_full_invite_accept_member_appears(self, client, owner):
        """owner invites → invitee registers → accepts → appears in member list."""
        ws_id = owner["workspace_id"]

        # Owner invites a new email
        r = client.post(
            f"/api/workspaces/{ws_id}/invites",
            headers=_headers(owner["token"], ws_id),
            json={"email": "newbie@example.com", "role": "member"},
        )
        assert r.status_code in (200, 201), r.text
        invite_token = r.json()["token"]

        # Invitee registers
        client.post("/api/auth/register",
                    json={"email": "newbie@example.com", "password": "pass"})
        r = client.post("/api/auth/login",
                        json={"email": "newbie@example.com", "password": "pass"})
        newbie_token = r.json()["access_token"]

        # Invitee accepts
        r = client.post(
            f"/api/workspaces/invites/{invite_token}/accept",
            headers={"Authorization": f"Bearer {newbie_token}"},
        )
        assert r.status_code in (200, 201), r.text
        assert r.json()["role"] == "member"

        # Member now appears in member list
        r = client.get(f"/api/workspaces/{ws_id}/members",
                       headers=_headers(owner["token"], ws_id))
        emails = [m.get("user_id") for m in r.json()]
        assert len(r.json()) == 2  # owner + newbie

    def test_invite_wrong_email_rejected(self, client, owner):
        ws_id = owner["workspace_id"]
        r = client.post(
            f"/api/workspaces/{ws_id}/invites",
            headers=_headers(owner["token"], ws_id),
            json={"email": "alice@example.com", "role": "viewer"},
        )
        token_val = r.json()["token"]

        # Register and login as a *different* user
        client.post("/api/auth/register",
                    json={"email": "bob@example.com", "password": "pass"})
        r = client.post("/api/auth/login",
                        json={"email": "bob@example.com", "password": "pass"})
        bob_token = r.json()["access_token"]

        r = client.post(
            f"/api/workspaces/invites/{token_val}/accept",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_invite_token_single_use(self, client, owner):
        ws_id = owner["workspace_id"]
        r = client.post(
            f"/api/workspaces/{ws_id}/invites",
            headers=_headers(owner["token"], ws_id),
            json={"email": "once@example.com", "role": "viewer"},
        )
        token_val = r.json()["token"]

        client.post("/api/auth/register",
                    json={"email": "once@example.com", "password": "pass"})
        r = client.post("/api/auth/login",
                        json={"email": "once@example.com", "password": "pass"})
        user_token = r.json()["access_token"]

        # First accept: OK
        r = client.post(f"/api/workspaces/invites/{token_val}/accept",
                        headers={"Authorization": f"Bearer {user_token}"})
        assert r.status_code in (200, 201)

        # Second accept: conflict
        r = client.post(f"/api/workspaces/invites/{token_val}/accept",
                        headers={"Authorization": f"Bearer {user_token}"})
        assert r.status_code == status.HTTP_409_CONFLICT

    def test_revoke_invite(self, client, owner):
        ws_id = owner["workspace_id"]
        r = client.post(
            f"/api/workspaces/{ws_id}/invites",
            headers=_headers(owner["token"], ws_id),
            json={"email": "revoked@example.com", "role": "viewer"},
        )
        invite_id = r.json()["id"]

        r = client.delete(
            f"/api/workspaces/{ws_id}/invites/{invite_id}",
            headers=_headers(owner["token"], ws_id),
        )
        assert r.status_code == status.HTTP_204_NO_CONTENT

        # Invite should no longer be in pending list
        r = client.get(f"/api/workspaces/{ws_id}/invites",
                       headers=_headers(owner["token"], ws_id))
        ids = [i["id"] for i in r.json()]
        assert invite_id not in ids


# ════════════════════════════════════════════════════════════════
# Workspace switching
# ════════════════════════════════════════════════════════════════

class TestWorkspaceSwitching:

    def test_user_can_belong_to_multiple_workspaces(self, client, owner, second_user):
        """A user invited to another workspace can switch between them."""
        ws1 = owner["workspace_id"]
        ws2 = second_user["workspace_id"]

        # Second user invites owner to their workspace
        r = client.post(
            f"/api/workspaces/{ws2}/invites",
            headers=_headers(second_user["token"], ws2),
            json={"email": "owner@example.com", "role": "member"},
        )
        invite_token = r.json()["token"]

        # Owner accepts
        r = client.post(f"/api/workspaces/invites/{invite_token}/accept",
                        headers={"Authorization": f"Bearer {owner['token']}"})
        assert r.status_code in (200, 201)

        # Owner lists their workspaces — should see both
        r = client.get("/api/workspaces",
                       headers={"Authorization": f"Bearer {owner['token']}"})
        assert r.status_code == 200
        ids = [w["id"] for w in r.json()]
        assert ws1 in ids
        assert ws2 in ids

        # Owner switches to ws2 via header
        r = client.get("/api/projects",
                       headers=_headers(owner["token"], ws2))
        assert r.status_code == 200  # projects in ws2 (empty list is fine)
