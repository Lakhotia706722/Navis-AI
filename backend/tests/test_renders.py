"""Tests for render job routes."""
import pytest
from fastapi import status


class TestRenderRoutes:
    """Render job endpoint tests."""

    def setup_method(self):
        """Setup: register and login a user."""
        self.email = "renderuser@example.com"
        self.password = "password123"

    def get_auth_token(self, client):
        """Helper to get auth token."""
        client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        return response.json()["access_token"]

    def test_start_render_success(self, client):
        """Test starting a render job."""
        token = self.get_auth_token(client)

        # Create project
        project_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Project", "prompt": "Test prompt"},
        )
        project_id = project_response.json()["id"]

        # Start render
        response = client.post(
            f"/api/renders/{project_id}/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"render_mode": "preview"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_id"] == project_id
        assert data["status"] == "queued"
        assert data["render_mode"] == "preview"
        assert data["progress_percent"] == 0
        assert "celery_task_id" not in data or data.get("celery_task_id") is None or data["celery_task_id"] is not None

    def test_start_render_invalid_mode(self, client):
        """Test starting render with invalid mode."""
        token = self.get_auth_token(client)

        # Create project
        project_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Project", "prompt": "Test prompt"},
        )
        project_id = project_response.json()["id"]

        # Start render with invalid mode
        response = client.post(
            f"/api/renders/{project_id}/start?render_mode=invalid",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_render_job(self, client):
        """Test getting render job status."""
        token = self.get_auth_token(client)

        # Create project
        project_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Project", "prompt": "Test prompt"},
        )
        project_id = project_response.json()["id"]

        # Start render
        start_response = client.post(
            f"/api/renders/{project_id}/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"render_mode": "full"},
        )
        render_id = start_response.json()["id"]

        # Get render job
        response = client.get(
            f"/api/renders/{render_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == render_id
        assert data["status"] == "queued"

    def test_get_render_job_not_found(self, client):
        """Test getting nonexistent render job."""
        token = self.get_auth_token(client)

        response = client.get(
            "/api/renders/99999",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_render(self, client):
        """Test canceling a render job."""
        token = self.get_auth_token(client)

        # Create project
        project_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Project", "prompt": "Test prompt"},
        )
        project_id = project_response.json()["id"]

        # Start render
        start_response = client.post(
            f"/api/renders/{project_id}/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"render_mode": "full"},
        )
        render_id = start_response.json()["id"]

        # Cancel render
        response = client.post(
            f"/api/renders/{render_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "failed"
        assert "Cancelled by user" in data["error_message"]

    def test_list_render_jobs(self, client):
        """Test listing render jobs for a project."""
        token = self.get_auth_token(client)

        # Create project
        project_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Project", "prompt": "Test prompt"},
        )
        project_id = project_response.json()["id"]

        # Start two renders
        client.post(
            f"/api/renders/{project_id}/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"render_mode": "preview"},
        )
        client.post(
            f"/api/renders/{project_id}/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"render_mode": "full"},
        )

        # List renders
        response = client.get(
            f"/api/projects/{project_id}/renders",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        renders = response.json()
        assert len(renders) == 2
        assert renders[0]["render_mode"] == "preview"
        assert renders[1]["render_mode"] == "full"
