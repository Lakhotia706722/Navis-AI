"""Pydantic schemas for API request/response contracts."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr


# ============ Auth ============


class UserCreate(BaseModel):
    """Request to create a user."""

    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Request to login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info response."""

    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Projects ============


class ProjectCreate(BaseModel):
    """Request to create a project."""

    title: str
    description: Optional[str] = None
    prompt: str  # The original user prompt


class ProjectUpdate(BaseModel):
    """Request to update a project."""

    title: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None


class ProjectResponse(BaseModel):
    """Project info response."""

    id: int
    user_id: int
    title: str
    description: Optional[str]
    prompt: Optional[str]
    status: str  # RenderJobStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Render Jobs ============


class RenderJobResponse(BaseModel):
    """Render job info response."""

    id: int
    project_id: int
    status: str  # RenderJobStatusEnum
    progress_percent: int
    render_mode: str  # "preview" or "full"
    output_video_path: Optional[str]
    error_message: Optional[str]
    estimated_duration_seconds: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Scenes ============


class SceneResponse(BaseModel):
    """Scene info response."""

    id: int
    render_job_id: int
    scene_number: int
    name: str
    duration_seconds: float
    scene_json: dict  # Full scene definition
    created_at: datetime

    class Config:
        from_attributes = True


class RenderJobWithScenes(RenderJobResponse):
    """Render job with scenes."""

    scenes: List["SceneResponse"] = []


class ProjectWithRenders(ProjectResponse):
    """Project with render jobs."""

    render_jobs: List["RenderJobResponse"] = []


# Rebuild all models with forward references AFTER all models are defined
RenderJobWithScenes.model_rebuild()
ProjectWithRenders.model_rebuild()


# ============ Assets ============


class AssetCreate(BaseModel):
    """Request to create/upload an asset."""

    name: str
    category: str
    tags: List[str] = []
    file_format: str  # "blend", "fbx", "glb"
    version: str = "1.0"
    licensing_info: Optional[str] = None


class AssetResponse(BaseModel):
    """Asset info response."""

    id: int
    name: str
    category: str
    tags: List[str]
    file_path: str
    file_format: str
    version: str
    licensing_info: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetSearchParams(BaseModel):
    """Query params for asset search."""

    category: Optional[str] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = None  # Name/keyword search


# ============ Usage & Cost ============


class UsageLogResponse(BaseModel):
    """Usage log info response."""

    id: int
    project_id: int
    usage_type: str  # "gpt_tokens", "tts_chars", "render_minutes"
    quantity: int
    cost_usd: Optional[float]
    metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectUsageStats(BaseModel):
    """Aggregate usage stats for a project."""

    project_id: int
    total_gpt_tokens: int = 0
    total_tts_chars: int = 0
    total_render_minutes: int = 0
    estimated_cost_usd: float = 0.0
    usage_logs: List[UsageLogResponse] = []


# ============ Notifications ============


class NotificationHookCreate(BaseModel):
    """Request to create a notification hook."""

    event_type: str  # "render_complete", "render_failed"
    hook_type: str  # "webhook", "email"
    destination: str  # URL or email
    project_id: Optional[int] = None  # None = global


class NotificationHookResponse(BaseModel):
    """Notification hook info response."""

    id: int
    project_id: Optional[int]
    event_type: str
    hook_type: str
    destination: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Error Responses ============


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None
