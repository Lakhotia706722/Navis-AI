"""Scene planner: generates Scene JSON from storyboard using GPT."""
import logging

from ai.gpt_client import gpt_client
from ai.schemas import Storyboard, ScenePlan, SceneDefinition

logger = logging.getLogger(__name__)


def generate_scene_plan(storyboard: Storyboard, max_scenes: int = 10) -> tuple[ScenePlan, dict]:
    """
    Generate detailed Scene JSON from storyboard using GPT.

    Each shot from storyboard becomes a scene with 3D objects, camera path, timing.

    Args:
        storyboard: Storyboard object from storyboard engine
        max_scenes: Maximum number of scenes to generate

    Returns:
        (ScenePlan object, usage_stats dict)
    """
    # Format storyboard for GPT
    shots_text = "\n".join(
        [
            f"Shot {shot.shot_number}: {shot.scene_name}\n"
            f"  Camera: {shot.camera_angle}, Duration: {shot.duration_seconds}s\n"
            f"  Action: {shot.action_description}\n"
            f"  Objects: {', '.join(shot.key_objects)}\n"
            f"  Movement: {shot.camera_movement or 'static'}"
            for shot in storyboard.shots[:max_scenes]
        ]
    )

    system_prompt = """You are an expert 3D scene designer for maritime animations.
Generate detailed 3D scene definitions (Scene JSON) for maritime training videos.
Output ONLY valid JSON in this format:
{
  "title": "Video title",
  "total_duration_seconds": <number>,
  "scenes": [
    {
      "scene_number": <int>,
      "name": "<scene name>",
      "duration_seconds": <float>,
      "description": "<what happens>",
      "objects": [
        {
          "id": "unique_id",
          "asset_name": "<asset name from library>",
          "position": {"x": <float>, "y": <float>, "z": <float>},
          "rotation": {"x": <float>, "y": <float>, "z": <float>},
          "scale": {"x": <float>, "y": <float>, "z": <float>},
          "animation": null
        }
      ],
      "camera_path": {
        "keyframes": [
          {
            "time_seconds": 0,
            "position": {"x": <float>, "y": <float>, "z": <float>},
            "look_at": {"x": <float>, "y": <float>, "z": <float>},
            "fov": 50
          }
        ],
        "interpolation": "linear"
      },
      "lighting": {
        "ambient_strength": 0.5,
        "key_light_angle": {"x": 45, "y": 45, "z": 0},
        "key_light_strength": 1.0,
        "fill_light_strength": 0.3,
        "shadows_enabled": true
      },
      "background_color": "#87CEEB",
      "render_samples": 128,
      "render_quality": "high",
      "notes": null
    }
  ]
}

Guidelines:
- Each scene represents one shot from the storyboard
- Use realistic maritime object positions (vessels at origin, camera at safe distance)
- Camera FOV typically 45-65 degrees
- Camera keyframes for movement (first at t=0, last at duration)
- Use asset names from maritime library: anchor, cargo-vessel, deck, rope, sea, sky, etc.
- Position camera to show action clearly (match camera_angle from storyboard)
- Lighting: key light typically 45-90° angle, ambient for fill
"""

    user_prompt = f"""Create detailed 3D scene definitions for this storyboard:

STORYBOARD TITLE: {storyboard.title}
TOTAL DURATION: {storyboard.total_duration_seconds}s

SHOTS:
{shots_text}

Generate {len(storyboard.shots[:max_scenes])} scenes (one per shot).
Use realistic maritime asset names and positions.
Output ONLY JSON (no markdown, no code blocks)."""

    result = gpt_client.call_gpt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format="json_object",
        temperature=0.7,
    )

    try:
        plan_dict = gpt_client.parse_json_response(result["text"])
        scene_plan = ScenePlan(**plan_dict)

        logger.info(
            f"Generated scene plan: {len(scene_plan.scenes)} scenes, {scene_plan.total_duration_seconds}s"
        )

        return scene_plan, result["tokens"]

    except Exception as e:
        logger.error(f"Failed to parse scene plan: {e}")
        raise ValueError(f"Scene plan generation failed: {e}")
