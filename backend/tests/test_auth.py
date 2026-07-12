"""Tests for authentication routes."""
import pytest
from fastapi import status


class TestAuthRoutes:
    """Auth endpoint tests."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "secure_password123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] is True
        assert "created_at" in data

    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email fails."""
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "password123",
            },
        )
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "different_password",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_login_success(self, client):
        """Test successful login."""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "mypassword",
            },
        )
        # Then login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "login@example.com",
                "password": "mypassword",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client):
        """Test login with wrong password fails."""
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "correctpassword",
            },
        )
        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_authenticated(self, client):
        """Test /me endpoint returns current user."""
        # Register
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "me@example.com",
                "password": "password",
                "full_name": "Me User",
            },
        )
        user_id = register_response.json()["id"]

        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "me@example.com",
                "password": "password",
            },
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == "me@example.com"

    def test_get_me_unauthenticated(self, client):
        """Test /me without token fails."""
        response = client.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_invalid_email(self, client):
        """Test registration with invalid email fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "password",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
