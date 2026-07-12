"""Script generation from prompt using GPT."""
import logging
from typing import Optional

from ai.gpt_client import gpt_client
from ai.schemas import Script, ScriptLine

logger = logging.getLogger(__name__)


def generate_script(prompt: str, max_duration: float = 300.0) -> tuple[Script, dict]:
    """
    Generate a script from a user prompt using GPT.

    Args:
        prompt: User's video request (e.g., "Create a video on anchor handling")
        max_duration: Maximum video length in seconds (default 5 minutes)

    Returns:
        (Script object, usage_stats dict with token counts)
    """
    system_prompt = """You are an expert maritime training video scriptwriter.
Create clear, professional scripts for maritime training videos.
Output ONLY valid JSON in this format:
{
  "title": "Video title",
  "total_duration_seconds": <number>,
  "lines": [
    {
      "line_number": <int>,
      "type": "narration|dialogue|action",
      "speaker": <null or string>,
      "text": "<line of narration/dialogue>",
      "duration_seconds": <float>,
      "notes": <null or string>
    }
  ],
  "summary": "Brief summary"
}

Guidelines:
- Keep lines concise (2-10 seconds each)
- Use "narration" for voiceover, "dialogue" for character speech, "action" for scene descriptions
- Total duration should NOT exceed the requested maximum
- Include detailed notes for complex scenes
"""

    user_prompt = f"""Create a maritime training video script based on this request:
"{prompt}"

Target duration: {max_duration} seconds
Output ONLY JSON (no markdown, no code blocks)."""

    result = gpt_client.call_gpt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format="json_object",
        temperature=0.7,
    )

    try:
        script_dict = gpt_client.parse_json_response(result["text"])
        script = Script(**script_dict)

        logger.info(
            f"Generated script: '{script.title}' ({script.total_duration_seconds}s, {len(script.lines)} lines)"
        )

        return script, result["tokens"]

    except Exception as e:
        logger.error(f"Failed to parse script: {e}")
        raise ValueError(f"Script generation failed: {e}")
