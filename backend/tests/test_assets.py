"""Tests for asset library routes."""
import pytest
from io import BytesIO
from fastapi import status


class TestAssetRoutes:
    """Asset endpoint tests."""

    def get_auth_token(self, client):
        """Helper to get auth token."""
        client.post(
            "/api/auth/register",
            json={"email": "assetuser@example.com", "password": "pass"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "assetuser@example.com", "password": "pass"},
        )
        return response.json()["access_token"]

    def test_create_asset_success(self, client):
        """Test successful asset creation."""
        token = self.get_auth_token(client)

        # Create a mock .blend file
        file_content = b"PK\x03\x04"  # ZIP header (fake blend file)

        response = client.post(
            "/api/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test-asset.blend", BytesIO(file_content), "application/octet-stream")},
            data={
                "name": "test-anchor",
                "category": "anchor",
                "tags": '["maritime", "equipment"]',
                "file_format": "blend",
                "version": "1.0",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test-anchor"
        assert data["category"] == "anchor"

    def test_create_asset_duplicate(self, client):
        """Test that duplicate asset names are rejected."""
        token = self.get_auth_token(client)
        file_content = b"PK\x03\x04"

        # Create first asset
        client.post(
            "/api/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.blend", BytesIO(file_content))},
            data={
                "name": "duplicate-asset",
                "category": "anchor",
                "tags": "[]",
                "file_format": "blend",
            },
        )

        # Try to create another with same name
        response = client.post(
            "/api/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test2.blend", BytesIO(file_content))},
            data={
                "name": "duplicate-asset",
                "category": "rope",
                "tags": "[]",
                "file_format": "blend",
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_asset_invalid_format(self, client):
        """Test that non-3D files are rejected."""
        token = self.get_auth_token(client)
        file_content = b"PDF-1.4"  # PDF header

        response = client.post(
            "/api/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(file_content))},
            data={
                "name": "invalid-asset",
                "category": "anchor",
                "tags": "[]",
                "file_format": "pdf",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_assets(self, client):
        """Test listing assets."""
        # Should return stub assets from Phase 3
        response = client.get("/api/assets")

        assert response.status_code == status.HTTP_200_OK
        assets = response.json()
        assert isinstance(assets, list)

    def test_list_assets_by_category(self, client):
        """Test filtering assets by category."""
        response = client.get("/api/assets?category=anchor")

        assert response.status_code == status.HTTP_200_OK
        assets = response.json()
        for asset in assets:
            assert asset["category"] == "anchor"

    def test_list_assets_by_tags(self, client):
        """Test filtering assets by tags."""
        response = client.get("/api/assets?tags=maritime")

        assert response.status_code == status.HTTP_200_OK
        assets = response.json()
        # All returned should have "maritime" tag
        for asset in assets:
            assert "maritime" in asset["tags"]

    def test_list_assets_by_search(self, client):
        """Test searching assets by name."""
        response = client.get("/api/assets?search=anchor")

        assert response.status_code == status.HTTP_200_OK
        assets = response.json()
        # Should find assets with "anchor" in name
        assert len(assets) > 0
        assert any("anchor" in asset["name"].lower() for asset in assets)

    def test_get_asset(self, client):
        """Test getting a specific asset."""
        # List assets first to get an ID
        list_response = client.get("/api/assets")
        assets = list_response.json()

        if assets:
            asset_id = assets[0]["id"]

            response = client.get(f"/api/assets/{asset_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == asset_id

    def test_get_asset_not_found(self, client):
        """Test getting nonexistent asset."""
        response = client.get("/api/assets/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_asset_requires_auth(self, client):
        """Test that delete requires authentication."""
        response = client.delete("/api/assets/1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_asset_not_found(self, client):
        """Test deleting nonexistent asset."""
        token = self.get_auth_token(client)

        response = client.delete(
            "/api/assets/99999",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
