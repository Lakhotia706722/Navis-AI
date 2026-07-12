"""Tests for AI planning pipeline (mock GPT calls)."""
import pytest
from unittest.mock import patch, MagicMock

from ai.schemas import Script, ScriptLine, Storyboard, Shot, ScenePlan, SceneDefinition, CameraPath, CameraKeyframe, Vector3
from ai.script_engine import generate_script
from ai.storyboard_engine import generate_storyboard
from ai.scene_planner import generate_scene_plan
from ai.asset_selector import find_asset, resolve_scene_assets


class TestScriptEngine:
    """Script generation tests."""

    @patch("ai.script_engine.gpt_client.call_gpt")
    def test_generate_script_success(self, mock_gpt):
        """Test successful script generation."""
        mock_gpt.return_value = {
            "text": """{
                "title": "Anchor Handling",
                "total_duration_seconds": 60.0,
                "lines": [
                    {
                        "line_number": 1,
                        "type": "narration",
                        "text": "Welcome to anchor handling",
                        "duration_seconds": 3.0,
                        "notes": null
                    }
                ],
                "summary": "A guide to proper anchor handling"
            }""",
            "tokens": {"prompt_tokens": 100, "completion_tokens": 150, "total_tokens": 250},
        }

        script, tokens = generate_script("Create anchor handling video")

        assert script.title == "Anchor Handling"
        assert script.total_duration_seconds == 60.0
        assert len(script.lines) == 1
        assert script.lines[0].text == "Welcome to anchor handling"
        assert tokens["total_tokens"] == 250

    @patch("ai.script_engine.gpt_client.call_gpt")
    def test_generate_script_markdown_block(self, mock_gpt):
        """Test script generation with markdown code block."""
        mock_gpt.return_value = {
            "text": """```json
            {
                "title": "Test",
                "total_duration_seconds": 30.0,
                "lines": [],
                "summary": "test"
            }
            ```""",
            "tokens": {"total_tokens": 100},
        }

        script, tokens = generate_script("Test")
        assert script.title == "Test"


class TestStoryboardEngine:
    """Storyboard generation tests."""

    @patch("ai.storyboard_engine.gpt_client.call_gpt")
    def test_generate_storyboard_success(self, mock_gpt):
        """Test successful storyboard generation."""
        script = Script(
            title="Anchor Handling",
            total_duration_seconds=60.0,
            lines=[
                ScriptLine(
                    line_number=1,
                    type="narration",
                    text="Welcome",
                    duration_seconds=3.0,
                )
            ],
            summary="Test",
        )

        mock_gpt.return_value = {
            "text": """{
                "title": "Anchor Handling",
                "shots": [
                    {
                        "shot_number": 1,
                        "scene_name": "Vessel at sea",
                        "camera_angle": "wide",
                        "action_description": "Establishing shot",
                        "duration_seconds": 3.0,
                        "narrative_lines": [1],
                        "key_objects": ["vessel"],
                        "lighting_notes": "Natural sunlight",
                        "camera_movement": "static"
                    }
                ],
                "total_duration_seconds": 60.0
            }""",
            "tokens": {"total_tokens": 300},
        }

        storyboard, tokens = generate_storyboard(script)

        assert storyboard.title == "Anchor Handling"
        assert len(storyboard.shots) == 1
        assert storyboard.shots[0].scene_name == "Vessel at sea"
        assert tokens["total_tokens"] == 300


class TestScenePlanner:
    """Scene plan generation tests."""

    @patch("ai.scene_planner.gpt_client.call_gpt")
    def test_generate_scene_plan_success(self, mock_gpt):
        """Test successful scene plan generation."""
        storyboard = Storyboard(
            title="Anchor Handling",
            shots=[
                Shot(
                    shot_number=1,
                    scene_name="Vessel at sea",
                    camera_angle="wide",
                    action_description="Establishing",
                    duration_seconds=3.0,
                    narrative_lines=[1],
                    key_objects=["vessel", "sea"],
                    camera_movement="static",
                )
            ],
            total_duration_seconds=60.0,
        )

        mock_gpt.return_value = {
            "text": """{
                "title": "Anchor Handling",
                "total_duration_seconds": 60.0,
                "scenes": [
                    {
                        "scene_number": 1,
                        "name": "Vessel at sea",
                        "duration_seconds": 3.0,
                        "description": "Establishing shot",
                        "objects": [
                            {
                                "id": "vessel_main",
                                "asset_name": "cargo-vessel-01",
                                "position": {"x": 0, "y": 0, "z": 0},
                                "rotation": {"x": 0, "y": 0, "z": 0},
                                "scale": {"x": 1, "y": 1, "z": 1}
                            }
                        ],
                        "camera_path": {
                            "keyframes": [
                                {
                                    "time_seconds": 0,
                                    "position": {"x": 50, "y": 30, "z": 50},
                                    "look_at": {"x": 0, "y": 0, "z": 0},
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
                        "render_quality": "high"
                    }
                ]
            }""",
            "tokens": {"total_tokens": 500},
        }

        scene_plan, tokens = generate_scene_plan(storyboard)

        assert scene_plan.title == "Anchor Handling"
        assert len(scene_plan.scenes) == 1
        assert scene_plan.scenes[0].name == "Vessel at sea"
        assert len(scene_plan.scenes[0].objects) == 1
        assert scene_plan.scenes[0].objects[0].asset_name == "cargo-vessel-01"


class TestAssetSelector:
    """Asset selector tests."""

    def test_find_asset_stub_library(self):
        """Test finding asset in stub library."""
        asset = find_asset("cargo-vessel-01")
        assert asset is not None
        assert asset.name == "cargo-vessel-01"
        assert asset.category == "vessel"
        assert "maritime" in asset.tags

    def test_find_asset_not_found(self):
        """Test asset not found returns None."""
        asset = find_asset("nonexistent-asset")
        assert asset is None

    def test_find_asset_by_category(self):
        """Test finding asset with category filter."""
        asset = find_asset("cargo-vessel-01", category="vessel")
        assert asset is not None

        asset = find_asset("cargo-vessel-01", category="anchor")
        assert asset is None

    def test_resolve_scene_assets(self):
        """Test resolving multiple scene assets."""
        objects = ["cargo-vessel-01", "anchor-01", "sea", "nonexistent"]
        resolved = resolve_scene_assets(objects)

        assert resolved["cargo-vessel-01"] is not None
        assert resolved["anchor-01"] is not None
        assert resolved["sea"] is not None
        assert resolved["nonexistent"] is None

    def test_stub_asset_library_completeness(self):
        """Test that stub library has expected maritime assets."""
        assets_to_check = ["cargo-vessel-01", "anchor-01", "rope-coil", "deck", "sea", "sky"]
        for asset_name in assets_to_check:
            asset = find_asset(asset_name)
            assert asset is not None, f"Expected asset {asset_name} not in stub library"
