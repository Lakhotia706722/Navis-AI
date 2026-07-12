"""Tests for monitoring and logging."""
import pytest
from backend.monitoring import StructuredLogger, app_logger


def test_structured_logger_creation():
    """Test logger initialization."""
    logger = StructuredLogger("test_logger")
    assert logger.logger is not None


def test_structured_logger_log_event(caplog):
    """Test structured event logging."""
    logger = StructuredLogger("test_event")
    
    logger.log_event(
        "test_event_type",
        "Test message",
        {"key": "value"}
    )
    
    # Check that event was logged
    assert len(caplog.records) >= 1


def test_structured_logger_log_error(caplog):
    """Test error logging."""
    logger = StructuredLogger("test_error")
    
    try:
        raise ValueError("Test error")
    except ValueError as e:
        logger.log_error("test_error_type", "Error occurred", e)
    
    # Check that error was logged
    assert len(caplog.records) >= 1


def test_structured_logger_log_metric(caplog):
    """Test metric logging."""
    logger = StructuredLogger("test_metric")
    
    logger.log_metric(
        "render_duration_seconds",
        120.5,
        {"render_mode": "preview"}
    )
    
    # Check that metric was logged
    assert len(caplog.records) >= 1


def test_app_logger_exists():
    """Test global app logger is initialized."""
    assert app_logger is not None
    assert app_logger.logger is not None
