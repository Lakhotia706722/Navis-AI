"""Storyboard generation from script using GPT."""
import logging

from ai.gpt_client import gpt_client
from ai.schemas import Script, Storyboard, Shot

logger = logging.getLogger(__name__)


def generate_storyboard(script: Script) -> tuple[Storyboard, dict]:
    """
    Generate a storyboard (shot list) from a script using GPT.

    Args:
        script: Script object from script engine

    Returns:
        (Storyboard object, usage_stats dict)
    """
    # Format script for GPT
    script_text = "\n".join(
        [f"Line {line.line_number} ({line.duration_seconds}s): {line.text}" for line in script.lines]
    )

    system_prompt = """You are an expert maritime video director and cinematographer.
Create detailed shot lists (storyboards) for maritime training videos.
Output ONLY valid JSON in this format:
{
  "title": "Same as script title",
  "shots": [
    {
      "shot_number": <int>,
      "scene_name": "<location name>",
      "camera_angle": "wide|medium|close-up|overhead|aerial",
      "action_description": "<what happens in this shot>",
      "duration_seconds": <float>,
      "narrative_lines": [<line numbers from script>],
      "key_objects": ["<object>", "<object>"],
      "lighting_notes": "<lighting setup>",
      "camera_movement": "static|pan|zoom|tracking|dolly"
    }
  ],
  "total_duration_seconds": <number>
}

Guidelines:
- Create 1-3 shots per minute of video
- Vary camera angles for visual interest
- Clearly link shots to script lines using narrative_lines array
- List all 3D objects that should appear
- Include specific camera movements
- Keep total_duration_seconds matching script duration
"""

    user_prompt = f"""Create a detailed storyboard for this maritime training script:

SCRIPT TITLE: {script.title}
DURATION: {script.total_duration_seconds}s

SCRIPT LINES:
{script_text}

Output ONLY JSON (no markdown, no code blocks)."""

    result = gpt_client.call_gpt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format="json_object",
        temperature=0.7,
    )

    try:
        storyboard_dict = gpt_client.parse_json_response(result["text"])
        storyboard = Storyboard(**storyboard_dict)

        logger.info(f"Generated storyboard: {len(storyboard.shots)} shots, {storyboard.total_duration_seconds}s")

        return storyboard, result["tokens"]

    except Exception as e:
        logger.error(f"Failed to parse storyboard: {e}")
        raise ValueError(f"Storyboard generation failed: {e}")
