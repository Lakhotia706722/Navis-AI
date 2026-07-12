"""Tests for project routes."""
import pytest
from fastapi import status


class TestProjectRoutes:
    """Project endpoint tests."""

    def setup_method(self):
        """Setup: register and login a user."""
        self.email = "projectuser@example.com"
        self.password = "password123"

    def test_create_project_success(self, client):
        """Test successful project creation."""
        # Register user
        client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
        )

        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        token = login_response.json()["access_token"]

        # Create project
        response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "My First Video",
                "description": "A test maritime video",
                "prompt": "Create a video about anchor handling",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "My First Video"
        assert data["description"] == "A test maritime video"
        assert data["prompt"] == "Create a video about anchor handling"
        assert data["status"] == "queued"

    def test_create_project_unauthenticated(self, client):
        """Test project creation without auth fails."""
        response = client.post(
            "/api/projects",
            json={
                "title": "My Video",
                "prompt": "Some prompt",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_projects(self, client):
        """Test listing projects for user."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        token = login_response.json()["access_token"]

        # Create two projects
        client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Project 1", "prompt": "Prompt 1"},
        )
        client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Project 2", "prompt": "Prompt 2"},
        )

        # List projects
        response = client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        projects = response.json()
        assert len(projects) == 2
        assert projects[0]["title"] == "Project 1"
        assert projects[1]["title"] == "Project 2"

    def test_get_project(self, client):
        """Test getting a specific project."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        token = login_response.json()["access_token"]

        # Create project
        create_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Get Me", "prompt": "Test prompt"},
        )
        project_id = create_response.json()["id"]

        # Get project
        response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == project_id
        assert data["title"] == "Get Me"

    def test_get_project_not_found(self, client):
        """Test getting nonexistent project."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        token = login_response.json()["access_token"]

        # Try to get nonexistent project
        response = client.get(
            "/api/projects/99999",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_project_unauthorized(self, client):
        """Test that user cannot access another user's project."""
        # Register and login user 1
        client.post(
            "/api/auth/register",
            json={"email": "user1@example.com", "password": "pass"},
        )
        login1 = client.post(
            "/api/auth/login",
            json={"email": "user1@example.com", "password": "pass"},
        )
        token1 = login1.json()["access_token"]

        # Create project with user 1
        create_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token1}"},
            json={"title": "User 1 Project", "prompt": "Prompt"},
        )
        project_id = create_response.json()["id"]

        # Register and login user 2
        client.post(
            "/api/auth/register",
            json={"email": "user2@example.com", "password": "pass"},
        )
        login2 = client.post(
            "/api/auth/login",
            json={"email": "user2@example.com", "password": "pass"},
        )
        token2 = login2.json()["access_token"]

        # User 2 tries to access user 1's project
        response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_project(self, client):
        """Test updating a project."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        token = login_response.json()["access_token"]

        # Create project
        create_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Old Title", "prompt": "Old prompt"},
        )
        project_id = create_response.json()["id"]

        # Update project
        response = client.put(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "New Title"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "New Title"
        assert data["prompt"] == "Old prompt"  # Unchanged

    def test_delete_project(self, client):
        """Test deleting a project."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        token = login_response.json()["access_token"]

        # Create project
        create_response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Delete Me", "prompt": "Prompt"},
        )
        project_id = create_response.json()["id"]

        # Delete project
        response = client.delete(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
