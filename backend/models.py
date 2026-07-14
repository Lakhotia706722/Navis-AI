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
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class WorkspaceRoleEnum(str, Enum):
    """Roles within a workspace. See docs/rbac.md for permission matrix."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

    # Numeric rank — higher = more permissions (used in middleware comparisons)
    @property
    def rank(self) -> int:
        return {"owner": 4, "admin": 3, "member": 2, "viewer": 1}[self.value]

    def __ge__(self, other: "WorkspaceRoleEnum") -> bool:
        return self.rank >= other.rank

    def __gt__(self, other: "WorkspaceRoleEnum") -> bool:
        return self.rank > other.rank


class InviteStatusEnum(str, Enum):
    """Lifecycle of a workspace invite."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class RoleEnum(str, Enum):
    """Legacy single-user role — kept for backward compat; superseded by WorkspaceRoleEnum."""

    OWNER = "owner"


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
    workspace_memberships = relationship("WorkspaceMember", foreign_keys="WorkspaceMember.user_id", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


class Workspace(Base):
    """A team workspace that owns a collection of projects."""

    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    plan_tier = Column(String(50), nullable=False, default="free",
                       comment="Billing tier stub — enforced in Phase 12")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    invites = relationship("WorkspaceInvite", back_populates="workspace", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="workspace")

    def __repr__(self):
        return f"<Workspace {self.id} — {self.name}>"


class WorkspaceMember(Base):
    """Membership of a user in a workspace with an assigned role."""

    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(WorkspaceRoleEnum), nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="workspace_memberships")
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<WorkspaceMember workspace={self.workspace_id} user={self.user_id} role={self.role}>"


class WorkspaceInvite(Base):
    """Pending invite to join a workspace."""

    __tablename__ = "workspace_invites"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(WorkspaceRoleEnum), nullable=False)
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    status = Column(SQLEnum(InviteStatusEnum), nullable=False, default=InviteStatusEnum.PENDING)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="invites")
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<WorkspaceInvite {self.email} → workspace={self.workspace_id} status={self.status}>"


class Project(Base):
    """Project (owns all downstream assets/renders)."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
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
    workspace = relationship("Workspace", back_populates="projects")
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
    """Cost tracking: GPT tokens, TTS chars, render minutes per project/workspace."""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Denormalised workspace FK for fast billing aggregation in Phase 12",
    )
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
