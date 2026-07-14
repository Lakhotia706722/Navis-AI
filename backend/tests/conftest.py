"""Test fixtures and configuration — Phase 11."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.main import app

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ─── Workspace-aware fixtures ────────────────────────────────────

def _register_and_login(client, email: str, password: str = "pass123",
                         full_name: str = "Test User") -> dict:
    """Register a user and return {"token": ..., "user_id": ..., "workspace_id": ...}."""
    r = client.post("/api/auth/register",
                    json={"email": email, "password": password, "full_name": full_name})
    assert r.status_code in (200, 201), r.text
    user_id = r.json()["id"]

    r = client.post("/api/auth/login",
                    json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    # Fetch the auto-created workspace id
    r = client.get("/api/workspaces",
                   headers={"Authorization": f"Bearer {token}"})
    workspace_id = r.json()[0]["id"]

    return {"token": token, "user_id": user_id, "workspace_id": workspace_id}


@pytest.fixture()
def owner(client):
    return _register_and_login(client, "owner@example.com", full_name="Owner User")


@pytest.fixture()
def second_user(client):
    return _register_and_login(client, "second@example.com", full_name="Second User")


def _add_member(client, owner_token: str, workspace_id: int,
                member_email: str, role: str) -> str:
    """Invite + accept a member. Returns the new member's token."""
    # Invite
    r = client.post(
        f"/api/workspaces/{workspace_id}/invites",
        headers={"Authorization": f"Bearer {owner_token}",
                 "X-Workspace-ID": str(workspace_id)},
        json={"email": member_email, "role": role},
    )
    assert r.status_code in (200, 201), r.text
    token_val = r.json()["token"]

    # Accept (member must be registered first)
    password = "pass123"
    client.post("/api/auth/register",
                json={"email": member_email, "password": password, "full_name": role.title()})
    r = client.post("/api/auth/login",
                    json={"email": member_email, "password": password})
    member_token = r.json()["access_token"]

    r = client.post(f"/api/workspaces/invites/{token_val}/accept",
                    headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code in (200, 201), r.text
    return member_token


@pytest.fixture()
def workspace_with_roles(client, owner):
    """
    Returns dict with tokens for all four roles in the same workspace:
      owner_token, admin_token, member_token, viewer_token, workspace_id
    """
    ws_id = owner["workspace_id"]
    admin_token  = _add_member(client, owner["token"], ws_id, "admin@example.com",  "admin")
    member_token = _add_member(client, owner["token"], ws_id, "member@example.com", "member")
    viewer_token = _add_member(client, owner["token"], ws_id, "viewer@example.com", "viewer")

    return {
        "workspace_id": ws_id,
        "owner_token":  owner["token"],
        "admin_token":  admin_token,
        "member_token": member_token,
        "viewer_token": viewer_token,
    }
