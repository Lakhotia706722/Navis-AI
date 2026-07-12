"""Tests for notification system."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.notifications import (
    NotificationManager,
    NotificationType,
    NotificationChannel,
    notify_render_completion,
    notify_render_failure,
    notify_cost_threshold_exceeded,
)


@pytest.mark.asyncio
async def test_notification_manager_creation():
    """Test notification manager initialization."""
    manager = NotificationManager()
    assert manager is not None


@pytest.mark.asyncio
async def test_send_webhook_notification():
    """Test webhook notification sending."""
    manager = NotificationManager()
    manager.webhook_url = "http://example.com/webhook"
    
    with patch('backend.notifications.httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await manager._send_webhook(
            NotificationType.RENDER_COMPLETED,
            1,
            1,
            {"status": "completed"}
        )
        
        assert result is True


@pytest.mark.asyncio
async def test_send_slack_notification():
    """Test Slack notification sending."""
    manager = NotificationManager()
    manager.slack_webhook = "https://hooks.slack.com/services/XXX"
    
    with patch('backend.notifications.httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await manager._send_slack(
            NotificationType.RENDER_COMPLETED,
            1,
            1,
            {"status": "completed"}
        )
        
        assert result is True


@pytest.mark.asyncio
async def test_send_notification_multiple_channels():
    """Test sending notification to multiple channels."""
    manager = NotificationManager()
    manager.webhook_url = "http://example.com/webhook"
    manager.slack_webhook = "https://hooks.slack.com/services/XXX"
    
    with patch('backend.notifications.httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        result = await manager.send_notification(
            NotificationType.RENDER_COMPLETED,
            1,
            1,
            {"status": "completed"},
            channels=[NotificationChannel.WEBHOOK, NotificationChannel.SLACK]
        )
        
        assert result is True


@pytest.mark.asyncio
async def test_notify_render_completion():
    """Test render completion notification."""
    with patch('backend.notifications.notification_manager.send_notification') as mock_send:
        mock_send.return_value = True
        
        await notify_render_completion(1, 1, "s3://bucket/video.mp4")
        
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][0] == NotificationType.RENDER_COMPLETED


@pytest.mark.asyncio
async def test_notify_render_failure():
    """Test render failure notification."""
    with patch('backend.notifications.notification_manager.send_notification') as mock_send:
        mock_send.return_value = True
        
        await notify_render_failure(1, 1, "Blender render timeout")
        
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][0] == NotificationType.RENDER_FAILED


@pytest.mark.asyncio
async def test_notify_cost_threshold_exceeded():
    """Test cost threshold exceeded notification."""
    with patch('backend.notifications.notification_manager.send_notification') as mock_send:
        mock_send.return_value = True
        
        await notify_cost_threshold_exceeded(1, 15.0, 10.0)
        
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][0] == NotificationType.COST_THRESHOLD_EXCEEDED
