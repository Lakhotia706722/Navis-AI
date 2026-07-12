"""AI planning orchestrator: coordinates script → storyboard → scene plan."""
import logging
import hashlib
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from ai.script_engine import generate_script
from ai.storyboard_engine import generate_storyboard
from ai.scene_planner import generate_scene_plan
from ai.schemas import AIPlanningOutput, ScenePlan
from backend.models import Scene, RenderJob, RenderJobStatusEnum, UsageLog
from backend.config import settings

logger = logging.getLogger(__name__)


def get_prompt_hash(prompt: str) -> str:
    """Generate a hash of the prompt for caching."""
    return hashlib.md5(prompt.encode()).hexdigest()


def run_planning_pipeline(
    render_job: RenderJob,
    prompt: str,
    db: Session,
    max_retries: int = 2,
) -> tuple[AIPlanningOutput, dict]:
    """
    Run the full AI planning pipeline: script → storyboard → scene plan.

    Args:
        render_job: RenderJob being processed
        prompt: User's video request
        db: Database session
        max_retries: Times to retry on validation failure

    Returns:
        (AIPlanningOutput with script/storyboard/scenes, cost_stats)
    """
    cost_stats = {
        "gpt_tokens": 0,
        "steps": {
            "script": {"tokens": 0, "attempts": 0},
            "storyboard": {"tokens": 0, "attempts": 0},
            "scene_plan": {"tokens": 0, "attempts": 0},
        },
    }

    logger.info(f"Starting planning pipeline for render_job {render_job.id}")
    logger.info(f"Prompt: {prompt[:100]}...")

    # Step 1: Generate Script
    logger.info("Step 1: Generating script...")
    script = None
    for attempt in range(max_retries):
        try:
            script, tokens = generate_script(prompt, max_duration=300)
            cost_stats["steps"]["script"]["tokens"] += tokens["total_tokens"]
            cost_stats["steps"]["script"]["attempts"] = attempt + 1
            cost_stats["gpt_tokens"] += tokens["total_tokens"]
            logger.info(f"✓ Script generated ({tokens['total_tokens']} tokens, attempt {attempt + 1})")
            break
        except Exception as e:
            logger.error(f"Script generation failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise

    if not script:
        raise ValueError("Failed to generate script after retries")

    # Step 2: Generate Storyboard
    logger.info("Step 2: Generating storyboard...")
    storyboard = None
    for attempt in range(max_retries):
        try:
            storyboard, tokens = generate_storyboard(script)
            cost_stats["steps"]["storyboard"]["tokens"] += tokens["total_tokens"]
            cost_stats["steps"]["storyboard"]["attempts"] = attempt + 1
            cost_stats["gpt_tokens"] += tokens["total_tokens"]
            logger.info(f"✓ Storyboard generated ({tokens['total_tokens']} tokens, attempt {attempt + 1})")
            break
        except Exception as e:
            logger.error(f"Storyboard generation failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise

    if not storyboard:
        raise ValueError("Failed to generate storyboard after retries")

    # Step 3: Generate Scene Plan
    logger.info("Step 3: Generating scene plan...")
    scene_plan = None
    for attempt in range(max_retries):
        try:
            scene_plan, tokens = generate_scene_plan(storyboard)
            cost_stats["steps"]["scene_plan"]["tokens"] += tokens["total_tokens"]
            cost_stats["steps"]["scene_plan"]["attempts"] = attempt + 1
            cost_stats["gpt_tokens"] += tokens["total_tokens"]
            logger.info(f"✓ Scene plan generated ({tokens['total_tokens']} tokens, attempt {attempt + 1})")
            break
        except Exception as e:
            logger.error(f"Scene plan generation failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise

    if not scene_plan:
        raise ValueError("Failed to generate scene plan after retries")

    # Step 4: Persist scenes to database
    logger.info("Step 4: Persisting scenes to database...")
    try:
        for scene_def in scene_plan.scenes:
            scene = Scene(
                render_job_id=render_job.id,
                scene_number=scene_def.scene_number,
                name=scene_def.name,
                duration_seconds=scene_def.duration_seconds,
                scene_json=scene_def.dict(),
            )
            db.add(scene)
        db.commit()
        logger.info(f"✓ Persisted {len(scene_plan.scenes)} scenes to database")
    except Exception as e:
        logger.error(f"Failed to persist scenes: {e}")
        db.rollback()
        raise

    # Step 5: Log GPT usage
    logger.info("Step 5: Logging token usage...")
    try:
        usage_log = UsageLog(
            project_id=render_job.project_id,
            usage_type="gpt_tokens",
            quantity=cost_stats["gpt_tokens"],
            cost_usd=calculate_gpt_cost(cost_stats["gpt_tokens"]),
            metadata={
                "model": settings.openai_model,
                "pipeline": "script+storyboard+scene_plan",
                "prompt_hash": get_prompt_hash(prompt),
            },
        )
        db.add(usage_log)
        db.commit()
        logger.info(f"✓ Logged {cost_stats['gpt_tokens']} GPT tokens")
    except Exception as e:
        logger.error(f"Failed to log usage: {e}")
        db.rollback()
        raise

    output = AIPlanningOutput(
        script=script,
        storyboard=storyboard,
        scene_plan=scene_plan,
        planning_notes=f"Generated with {cost_stats['gpt_tokens']} tokens ({max_retries} max retries)",
    )

    logger.info(f"✓ Planning pipeline complete: {len(scene_plan.scenes)} scenes")
    return output, cost_stats


def calculate_gpt_cost(tokens: int) -> float:
    """
    Calculate estimated cost for GPT tokens.

    Using gpt-4-turbo pricing (as of July 2024):
    - Input: $0.01 / 1K tokens
    - Output: $0.03 / 1K tokens

    Rough estimate: average ~$0.01-0.015 per token
    """
    return round(tokens * 0.015 / 1000, 4)
