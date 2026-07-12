"""Cost tracking and control for projects."""
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models import Project, UsageLog
from backend.notifications import notify_cost_threshold_exceeded

logger = logging.getLogger(__name__)


class CostController:
    """Manages cost tracking and threshold alerts."""

    # Cost constants (in USD)
    GPT_COST_PER_1K_TOKENS = 0.015  # GPT-4 pricing
    TTS_COST_PER_1K_CHARS = 0.015  # OpenAI TTS pricing
    RENDER_COST_PER_MINUTE = 0.0  # Local, no cost
    DEFAULT_COST_THRESHOLD = 10.0  # Default $10 per project

    def __init__(self, db: Session):
        self.db = db

    async def log_gpt_usage(self, project_id: int, tokens: int) -> float:
        """
        Log GPT token usage and return cost.

        Args:
            project_id: Project ID
            tokens: Number of tokens used

        Returns:
            Cost in USD
        """
        cost = (tokens / 1000.0) * self.GPT_COST_PER_1K_TOKENS

        usage_log = UsageLog(
            project_id=project_id,
            gpt_tokens=tokens,
            tts_characters=0,
            render_minutes=0,
            cost=cost,
        )
        self.db.add(usage_log)
        self.db.commit()

        await self._check_threshold(project_id)
        return cost

    async def log_tts_usage(self, project_id: int, characters: int) -> float:
        """
        Log TTS character usage and return cost.

        Args:
            project_id: Project ID
            characters: Number of characters synthesized

        Returns:
            Cost in USD
        """
        cost = (characters / 1000.0) * self.TTS_COST_PER_1K_CHARS

        usage_log = UsageLog(
            project_id=project_id,
            gpt_tokens=0,
            tts_characters=characters,
            render_minutes=0,
            cost=cost,
        )
        self.db.add(usage_log)
        self.db.commit()

        await self._check_threshold(project_id)
        return cost

    async def log_render_usage(self, project_id: int, minutes: float) -> float:
        """
        Log render time and return cost.

        Args:
            project_id: Project ID
            minutes: Minutes of render time

        Returns:
            Cost in USD (0 for local rendering)
        """
        cost = minutes * self.RENDER_COST_PER_MINUTE

        usage_log = UsageLog(
            project_id=project_id,
            gpt_tokens=0,
            tts_characters=0,
            render_minutes=int(minutes),
            cost=cost,
        )
        self.db.add(usage_log)
        self.db.commit()

        await self._check_threshold(project_id)
        return cost

    def get_project_cost(self, project_id: int) -> tuple[float, dict]:
        """
        Get total cost for a project.

        Args:
            project_id: Project ID

        Returns:
            Tuple of (total_cost, breakdown)
        """
        logs = self.db.query(UsageLog).filter(UsageLog.project_id == project_id).all()

        total_gpt_tokens = sum(log.gpt_tokens or 0 for log in logs)
        total_tts_chars = sum(log.tts_characters or 0 for log in logs)
        total_render_mins = sum(log.render_minutes or 0 for log in logs)
        total_cost = sum(log.cost or 0 for log in logs)

        gpt_cost = (total_gpt_tokens / 1000.0) * self.GPT_COST_PER_1K_TOKENS
        tts_cost = (total_tts_chars / 1000.0) * self.TTS_COST_PER_1K_CHARS
        render_cost = total_render_mins * self.RENDER_COST_PER_MINUTE

        breakdown = {
            "gpt_tokens": total_gpt_tokens,
            "gpt_cost": round(gpt_cost, 4),
            "tts_characters": total_tts_chars,
            "tts_cost": round(tts_cost, 4),
            "render_minutes": total_render_mins,
            "render_cost": round(render_cost, 4),
            "total_cost": round(total_cost, 4),
        }

        return total_cost, breakdown

    async def _check_threshold(self, project_id: int):
        """Check if project has exceeded cost threshold and notify if so."""
        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return

            threshold = project.cost_threshold or self.DEFAULT_COST_THRESHOLD
            current_cost, _ = self.get_project_cost(project_id)

            if current_cost > threshold:
                logger.warning(f"Project {project_id} exceeded cost threshold: ${current_cost:.2f} > ${threshold:.2f}")
                await notify_cost_threshold_exceeded(project_id, current_cost, threshold)
        except Exception as e:
            logger.error(f"Error checking cost threshold: {e}")


def get_cost_controller(db: Session) -> CostController:
    """Factory for CostController."""
    return CostController(db)
