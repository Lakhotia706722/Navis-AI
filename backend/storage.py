"""S3/MinIO object storage client wrapper."""
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from backend.config import settings


class S3Client:
    """Wrapper around boto3 S3 client for MinIO/S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self.bucket = settings.s3_bucket_name

    def ensure_bucket_exists(self) -> bool:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
                return True
            except ClientError as e:
                print(f"Error creating bucket: {e}")
                return False

    def upload_file(self, local_path: str, remote_key: str) -> Optional[str]:
        """Upload a file to S3.
        
        Args:
            local_path: Path to local file
            remote_key: S3 object key (path in bucket)
            
        Returns:
            S3 URL if successful, None otherwise
        """
        try:
            self.client.upload_file(local_path, self.bucket, remote_key)
            return f"s3://{self.bucket}/{remote_key}"
        except ClientError as e:
            print(f"Error uploading file: {e}")
            return None

    def download_file(self, remote_key: str, local_path: str) -> bool:
        """Download a file from S3.
        
        Args:
            remote_key: S3 object key
            local_path: Path to save locally
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.download_file(self.bucket, remote_key, local_path)
            return True
        except ClientError as e:
            print(f"Error downloading file: {e}")
            return False

    def delete_file(self, remote_key: str) -> bool:
        """Delete a file from S3.
        
        Args:
            remote_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=remote_key)
            return True
        except ClientError as e:
            print(f"Error deleting file: {e}")
            return False

    def get_file_url(self, remote_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for a file.
        
        Args:
            remote_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL if successful, None otherwise
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": remote_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None

    def list_files(self, prefix: str = "") -> list:
        """List files in bucket with optional prefix.
        
        Args:
            prefix: Prefix to filter by
            
        Returns:
            List of object keys
        """
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            if "Contents" in response:
                return [obj["Key"] for obj in response["Contents"]]
            return []
        except ClientError as e:
            print(f"Error listing files: {e}")
            return []


# Singleton instance
s3_client = S3Client()
