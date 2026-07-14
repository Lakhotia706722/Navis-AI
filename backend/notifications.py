"""Notification system for render completion, failures, and cost alerts."""
import logging
import os
import json
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Notification event types."""
    RENDER_STARTED = "render_started"
    RENDER_COMPLETED = "render_completed"
    RENDER_FAILED = "render_failed"
    COST_THRESHOLD_EXCEEDED = "cost_threshold_exceeded"
    WORKSPACE_INVITE = "workspace_invite"  # Phase 11


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"


class NotificationManager:
    """Manages sending notifications via various channels."""

    def __init__(self):
        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

    async def send_notification(
        self,
        notification_type: NotificationType,
        render_job_id: int,
        project_id: int,
        data: Dict[str, Any],
        channels: Optional[list[NotificationChannel]] = None,
    ) -> bool:
        """
        Send notification via specified channels.

        Args:
            notification_type: Type of notification
            render_job_id: Render job ID
            project_id: Project ID
            data: Additional data to include
            channels: List of channels to send to (default: all enabled)

        Returns:
            True if at least one channel succeeded
        """
        if channels is None:
            channels = self._get_enabled_channels()

        success = False

        try:
            for channel in channels:
                if channel == NotificationChannel.WEBHOOK:
                    if await self._send_webhook(notification_type, render_job_id, project_id, data):
                        success = True
                elif channel == NotificationChannel.EMAIL:
                    if await self._send_email(notification_type, render_job_id, project_id, data):
                        success = True
                elif channel == NotificationChannel.SLACK:
                    if await self._send_slack(notification_type, render_job_id, project_id, data):
                        success = True
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")

        return success

    async def _send_webhook(
        self,
        notification_type: NotificationType,
        render_job_id: int,
        project_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Send webhook notification."""
        if not self.webhook_url:
            return False

        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": notification_type.value,
            "render_job_id": render_job_id,
            "project_id": project_id,
            "data": data,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Webhook notification sent for render {render_job_id}")
                    return True
                else:
                    logger.warning(f"Webhook failed with status {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False

    async def _send_email(
        self,
        notification_type: NotificationType,
        render_job_id: int,
        project_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Send email notification."""
        if not self.email_enabled:
            return False

        # Email sending would be implemented with a service like SendGrid, AWS SES, etc.
        # For MVP, we'll just log it
        logger.info(f"Email notification queued for render {render_job_id}: {notification_type.value}")
        return True

    async def _send_slack(
        self,
        notification_type: NotificationType,
        render_job_id: int,
        project_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Send Slack notification."""
        if not self.slack_webhook:
            return False

        # Format message based on notification type
        if notification_type == NotificationType.RENDER_COMPLETED:
            title = "✅ Render Complete"
            color = "good"
        elif notification_type == NotificationType.RENDER_FAILED:
            title = "❌ Render Failed"
            color = "danger"
        elif notification_type == NotificationType.COST_THRESHOLD_EXCEEDED:
            title = "⚠️ Cost Threshold Exceeded"
            color = "warning"
        else:
            title = notification_type.value
            color = "#439FE0"

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "fields": [
                        {"title": "Render Job", "value": str(render_job_id), "short": True},
                        {"title": "Project", "value": str(project_id), "short": True},
                        {"title": "Details", "value": json.dumps(data, indent=2), "short": False},
                    ],
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.slack_webhook, json=payload)
                if response.status_code == 200:
                    logger.info(f"Slack notification sent for render {render_job_id}")
                    return True
                else:
                    logger.warning(f"Slack notification failed with status {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    def _get_enabled_channels(self) -> list[NotificationChannel]:
        """Get list of enabled notification channels."""
        channels = []
        if self.webhook_url:
            channels.append(NotificationChannel.WEBHOOK)
        if self.email_enabled:
            channels.append(NotificationChannel.EMAIL)
        if self.slack_webhook:
            channels.append(NotificationChannel.SLACK)
        return channels if channels else [NotificationChannel.WEBHOOK]


# Global notification manager
notification_manager = NotificationManager()


async def notify_render_completion(render_job_id: int, project_id: int, output_path: str):
    """Notify on render completion."""
    data = {
        "status": "completed",
        "output_path": output_path,
        "completed_at": datetime.utcnow().isoformat(),
    }
    await notification_manager.send_notification(
        NotificationType.RENDER_COMPLETED,
        render_job_id,
        project_id,
        data,
    )


async def notify_render_failure(render_job_id: int, project_id: int, error_message: str):
    """Notify on render failure."""
    data = {
        "status": "failed",
        "error_message": error_message,
        "failed_at": datetime.utcnow().isoformat(),
    }
    await notification_manager.send_notification(
        NotificationType.RENDER_FAILED,
        render_job_id,
        project_id,
        data,
    )


async def notify_cost_threshold_exceeded(project_id: int, current_cost: float, threshold: float):
    """Notify when project exceeds cost threshold."""
    data = {
        "current_cost": current_cost,
        "threshold": threshold,
        "exceeded_by": current_cost - threshold,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await notification_manager.send_notification(
        NotificationType.COST_THRESHOLD_EXCEEDED,
        0,  # No specific render job
        project_id,
        data,
    )
