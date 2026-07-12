"""SQLAlchemy ORM models."""
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
    JSON,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class RoleEnum(str, Enum):
    """User roles (MVP: owner only, extensible for teams later)."""

    OWNER = "owner"
    # ADMIN = "admin"  # Future
    # EDITOR = "editor"  # Future
    # VIEWER = "viewer"  # Future


class RenderJobStatusEnum(str, Enum):
    """Render job status state machine."""

    QUEUED = "queued"
    PLANNING = "planning"
    COMPOSING = "composing"
    RENDERING = "rendering"
    ASSEMBLING = "assembling"
    DONE = "done"
    FAILED = "failed"


class User(Base):
    """User account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class Project(Base):
    """Project (owns all downstream assets/renders)."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)  # Original user prompt
    status = Column(
        SQLEnum(RenderJobStatusEnum),
        default=RenderJobStatusEnum.QUEUED,
        nullable=False,
    )
    cost_threshold = Column(Float, default=10.0, nullable=False)  # Cost alert threshold in USD
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="projects")
    render_jobs = relationship("RenderJob", back_populates="project", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.id} - {self.title}>"


class Scene(Base):
    """Individual scene within a project (from scene JSON)."""

    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    render_job_id = Column(Integer, ForeignKey("render_jobs.id"), nullable=False)
    scene_number = Column(Integer, nullable=False)  # Order in project
    name = Column(String(255), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    scene_json = Column(JSON, nullable=False)  # Full scene definition (objects, camera, timing)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    render_job = relationship("RenderJob", back_populates="scenes")

    def __repr__(self):
        return f"<Scene {self.id} - {self.name}>"


class RenderJob(Base):
    """Top-level render job (one per project submission)."""

    __tablename__ = "render_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    celery_task_id = Column(String(255), unique=True, nullable=True)  # Celery task UUID
    status = Column(
        SQLEnum(RenderJobStatusEnum),
        default=RenderJobStatusEnum.QUEUED,
        nullable=False,
    )
    progress_percent = Column(Integer, default=0, nullable=False)  # 0-100
    render_mode = Column(String(50), default="full", nullable=False)  # "preview" or "full"
    output_video_path = Column(String(512), nullable=True)  # S3 path to final MP4
    error_message = Column(Text, nullable=True)
    estimated_duration_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="render_jobs")
    scenes = relationship("Scene", back_populates="render_job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RenderJob {self.id} - {self.status}>"


class Asset(Base):
    """3D asset in the library (uploaded or indexed)."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)  # e.g., "anchor", "rope", "vessel"
    tags = Column(JSON, default=list, nullable=False)  # ["maritime", "equipment"]
    file_path = Column(String(512), nullable=False)  # S3 path (.blend, .fbx, .glb)
    file_format = Column(String(10), nullable=False)  # "blend", "fbx", "glb"
    version = Column(String(50), default="1.0", nullable=False)
    licensing_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Asset {self.name}>"


class UsageLog(Base):
    """Cost tracking: GPT tokens, TTS chars, render minutes per project."""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    gpt_tokens = Column(Integer, default=0, nullable=False)
    tts_characters = Column(Integer, default=0, nullable=False)
    render_minutes = Column(Integer, default=0, nullable=False)
    cost = Column(Float, nullable=False)  # Total cost in USD
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="usage_logs")

    def __repr__(self):
        return f"<UsageLog project={self.project_id} cost=${self.cost:.2f}>"


class NotificationHook(Base):
    """Notification webhook stub (will be wired in Phase 9)."""

    __tablename__ = "notification_hooks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # None = global
    event_type = Column(String(50), nullable=False)  # "render_complete", "render_failed"
    hook_type = Column(String(50), nullable=False)  # "webhook", "email"
    destination = Column(String(512), nullable=False)  # URL or email
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<NotificationHook {self.event_type}>"
