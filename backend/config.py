"""Configuration and settings."""
import os
from datetime import timedelta

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings from environment variables."""

    # Database
    database_url: str = "postgresql://maritime_user:maritime_pass@localhost:5432/maritime_studio"
    database_echo: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # JWT
    jwt_secret_key: str = "your-super-secret-key-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo"
    openai_tts_model: str = "tts-1-hd"
    openai_tts_voice: str = "nova"

    # S3/MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "maritime-studio"
    s3_region: str = "us-east-1"

    # Blender
    blender_executable: str = "/usr/bin/blender"
    blender_render_backend: str = "CPU"  # CPU or CUDA

    # Rendering
    preview_render_samples: int = 16
    full_render_samples: int = 128
    render_timeout_seconds: int = 3600

    # Logging
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # Feature flags
    enable_preview_mode: bool = True
    enable_cost_tracking: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def jwt_expiration(self) -> timedelta:
        """JWT token expiration."""
        return timedelta(hours=self.jwt_expiration_hours)


settings = Settings()
