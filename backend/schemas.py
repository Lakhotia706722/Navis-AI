"""Pydantic schemas for API request/response contracts — Phase 11."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr

from backend.models import WorkspaceRoleEnum


# ============ Auth ============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Workspaces ============

class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    plan_tier: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    invited_by: Optional[int]
    joined_at: datetime

    class Config:
        from_attributes = True


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRoleEnum


class WorkspaceInviteCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRoleEnum


class WorkspaceInviteResponse(BaseModel):
    id: int
    email: str
    workspace_id: int
    role: str
    token: str
    expires_at: datetime
    status: str
    invited_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceUsageStats(BaseModel):
    workspace_id: int
    total_gpt_tokens: int = 0
    total_tts_characters: int = 0
    total_render_minutes: int = 0
    total_cost_usd: float = 0.0
    project_count: int = 0


# ============ Projects ============

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    prompt: str


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    workspace_id: int
    title: str
    description: Optional[str]
    prompt: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Render Jobs ============

class RenderJobResponse(BaseModel):
    id: int
    project_id: int
    status: str
    progress_percent: int
    render_mode: str
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
    id: int
    render_job_id: int
    scene_number: int
    name: str
    duration_seconds: float
    scene_json: dict
    created_at: datetime

    class Config:
        from_attributes = True


class RenderJobWithScenes(RenderJobResponse):
    scenes: List["SceneResponse"] = []


class ProjectWithRenders(ProjectResponse):
    render_jobs: List["RenderJobResponse"] = []


RenderJobWithScenes.model_rebuild()
ProjectWithRenders.model_rebuild()


# ============ Assets ============

class AssetCreate(BaseModel):
    name: str
    category: str
    tags: List[str] = []
    file_format: str
    version: str = "1.0"
    licensing_info: Optional[str] = None


class AssetResponse(BaseModel):
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
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = None


# ============ Usage & Cost ============

class UsageLogResponse(BaseModel):
    id: int
    project_id: int
    workspace_id: Optional[int]
    gpt_tokens: int
    tts_characters: int
    render_minutes: int
    cost: float
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectUsageStats(BaseModel):
    project_id: int
    total_gpt_tokens: int = 0
    total_tts_chars: int = 0
    total_render_minutes: int = 0
    estimated_cost_usd: float = 0.0
    usage_logs: List[UsageLogResponse] = []


# ============ Notifications ============

class NotificationHookCreate(BaseModel):
    event_type: str
    hook_type: str
    destination: str
    project_id: Optional[int] = None


class NotificationHookResponse(BaseModel):
    id: int
    project_id: Optional[int]
    event_type: str
    hook_type: str
    destination: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Errors ============

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
