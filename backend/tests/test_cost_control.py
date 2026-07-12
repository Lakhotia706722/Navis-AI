"""Tests for cost tracking and control."""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session

from backend.cost_control import CostController
from backend.models import Project, User, UsageLog
from backend.database import SessionLocal


@pytest.fixture
def db():
    """Database session for tests."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def user(db: Session):
    """Create test user."""
    user = User(
        email="cost_test@example.com",
        hashed_password="hashed_password",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def project(db: Session, user: User):
    """Create test project."""
    project = Project(
        user_id=user.id,
        title="Cost Test Project",
        prompt="Test prompt",
        cost_threshold=10.0,
    )
    db.add(project)
    db.commit()
    return project


def test_cost_controller_creation(db: Session):
    """Test cost controller initialization."""
    controller = CostController(db)
    assert controller is not None
    assert controller.db is not None


@pytest.mark.asyncio
async def test_log_gpt_usage(db: Session, project: Project):
    """Test GPT usage logging."""
    controller = CostController(db)
    
    with patch('backend.cost_control.notify_cost_threshold_exceeded'):
        cost = await controller.log_gpt_usage(project.id, 1000)
    
    # Cost should be (1000 / 1000) * 0.015 = 0.015
    assert cost == pytest.approx(0.015, rel=1e-3)
    
    # Check that usage was logged
    logs = db.query(UsageLog).filter(UsageLog.project_id == project.id).all()
    assert len(logs) == 1
    assert logs[0].gpt_tokens == 1000


@pytest.mark.asyncio
async def test_log_tts_usage(db: Session, project: Project):
    """Test TTS usage logging."""
    controller = CostController(db)
    
    with patch('backend.cost_control.notify_cost_threshold_exceeded'):
        cost = await controller.log_tts_usage(project.id, 1000)
    
    # Cost should be (1000 / 1000) * 0.015 = 0.015
    assert cost == pytest.approx(0.015, rel=1e-3)
    
    # Check that usage was logged
    logs = db.query(UsageLog).filter(UsageLog.project_id == project.id).all()
    assert len(logs) == 1
    assert logs[0].tts_characters == 1000


@pytest.mark.asyncio
async def test_log_render_usage(db: Session, project: Project):
    """Test render time logging."""
    controller = CostController(db)
    
    with patch('backend.cost_control.notify_cost_threshold_exceeded'):
        cost = await controller.log_render_usage(project.id, 5.0)
    
    # Cost should be 0 for local rendering
    assert cost == 0.0
    
    # Check that usage was logged
    logs = db.query(UsageLog).filter(UsageLog.project_id == project.id).all()
    assert len(logs) == 1
    assert logs[0].render_minutes == 5


def test_get_project_cost(db: Session, project: Project):
    """Test getting project cost breakdown."""
    controller = CostController(db)
    
    # Log some usage
    log1 = UsageLog(
        project_id=project.id,
        gpt_tokens=1000,
        tts_characters=0,
        render_minutes=0,
        cost=0.015,
    )
    log2 = UsageLog(
        project_id=project.id,
        gpt_tokens=0,
        tts_characters=500,
        render_minutes=0,
        cost=0.0075,
    )
    db.add(log1)
    db.add(log2)
    db.commit()
    
    total_cost, breakdown = controller.get_project_cost(project.id)
    
    assert total_cost == pytest.approx(0.0225, rel=1e-3)
    assert breakdown["gpt_tokens"] == 1000
    assert breakdown["tts_characters"] == 500
    assert breakdown["total_cost"] == pytest.approx(0.0225, rel=1e-3)


@pytest.mark.asyncio
async def test_cost_threshold_alert(db: Session, project: Project):
    """Test cost threshold alert."""
    controller = CostController(db)
    project.cost_threshold = 0.01  # Low threshold for testing
    db.commit()
    
    # Log usage that exceeds threshold
    with patch('backend.cost_control.notify_cost_threshold_exceeded') as mock_notify:
        await controller.log_gpt_usage(project.id, 2000)  # Should exceed 0.01
        
        # Notification should be called
        mock_notify.assert_called()


def test_cost_constants():
    """Test cost constant values."""
    controller = CostController(SessionLocal())
    
    assert controller.GPT_COST_PER_1K_TOKENS == 0.015
    assert controller.TTS_COST_PER_1K_CHARS == 0.015
    assert controller.RENDER_COST_PER_MINUTE == 0.0
    assert controller.DEFAULT_COST_THRESHOLD == 10.0
