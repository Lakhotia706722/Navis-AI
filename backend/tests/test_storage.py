"""Tests for S3/MinIO storage client."""
import pytest
from unittest.mock import patch, MagicMock
from backend.storage import S3Client


class TestS3Client:
    """S3 storage client tests."""

    def test_s3_client_init(self):
        """Test S3 client initialization."""
        client = S3Client()
        assert client.bucket == "maritime-studio"
        assert client.client is not None

    @patch("backend.storage.boto3.client")
    def test_upload_file_success(self, mock_boto_client):
        """Test successful file upload."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        client = S3Client()
        client.client = mock_s3

        # Mock upload success
        result = client.upload_file("/local/file.mp4", "renders/video-1.mp4")

        assert result == "s3://maritime-studio/renders/video-1.mp4"
        mock_s3.upload_file.assert_called_once()

    @patch("backend.storage.boto3.client")
    def test_upload_file_failure(self, mock_boto_client):
        """Test file upload failure."""
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.upload_file.side_effect = ClientError({"Error": {"Code": "404"}}, "upload")

        client = S3Client()
        client.client = mock_s3

        result = client.upload_file("/local/file.mp4", "renders/video-1.mp4")

        assert result is None

    @patch("backend.storage.boto3.client")
    def test_download_file_success(self, mock_boto_client):
        """Test successful file download."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        client = S3Client()
        client.client = mock_s3

        result = client.download_file("renders/video-1.mp4", "/local/file.mp4")

        assert result is True
        mock_s3.download_file.assert_called_once()

    @patch("backend.storage.boto3.client")
    def test_delete_file_success(self, mock_boto_client):
        """Test successful file deletion."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        client = S3Client()
        client.client = mock_s3

        result = client.delete_file("renders/video-1.mp4")

        assert result is True
        mock_s3.delete_object.assert_called_once()

    @patch("backend.storage.boto3.client")
    def test_get_file_url(self, mock_boto_client):
        """Test generating presigned URL."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://minio.local/download?token=xyz"

        client = S3Client()
        client.client = mock_s3

        result = client.get_file_url("renders/video-1.mp4")

        assert result == "https://minio.local/download?token=xyz"
        mock_s3.generate_presigned_url.assert_called_once()

    @patch("backend.storage.boto3.client")
    def test_list_files(self, mock_boto_client):
        """Test listing files in bucket."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "renders/video-1.mp4"},
                {"Key": "renders/video-2.mp4"},
                {"Key": "assets/anchor.blend"},
            ]
        }

        client = S3Client()
        client.client = mock_s3

        result = client.list_files(prefix="renders/")

        assert len(result) == 3
        assert "renders/video-1.mp4" in result

    @patch("backend.storage.boto3.client")
    def test_ensure_bucket_exists(self, mock_boto_client):
        """Test bucket existence check."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        client = S3Client()
        client.client = mock_s3

        result = client.ensure_bucket_exists()

        assert result is True
        mock_s3.head_bucket.assert_called_once()
