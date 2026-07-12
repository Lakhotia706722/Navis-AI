"""Pydantic schemas for AI planning pipeline (Scene JSON, script, storyboard)."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ Script ============


class ScriptLine(BaseModel):
    """A single line of narration or dialogue."""

    line_number: int
    type: str  # "narration", "dialogue", "action"
    speaker: Optional[str] = None  # For dialogue
    text: str
    duration_seconds: float  # How long this line takes to speak/act
    notes: Optional[str] = None


class Script(BaseModel):
    """AI-generated script."""

    title: str
    total_duration_seconds: float
    lines: List[ScriptLine]
    summary: str = Field(description="Brief summary of the script")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Anchor Handling Best Practices",
                "total_duration_seconds": 120.0,
                "lines": [
                    {
                        "line_number": 1,
                        "type": "narration",
                        "text": "Welcome to anchor handling best practices.",
                        "duration_seconds": 3.0,
                    }
                ],
                "summary": "A guide to proper anchor handling",
            }
        }


# ============ Storyboard ============


class Shot(BaseModel):
    """A single shot in the storyboard."""

    shot_number: int
    scene_name: str
    camera_angle: str  # "wide", "medium", "close-up", "overhead"
    action_description: str
    duration_seconds: float
    narrative_lines: List[int] = Field(description="Script line numbers for this shot")
    key_objects: List[str] = Field(default_factory=list, description="Objects to show")
    lighting_notes: Optional[str] = None
    camera_movement: Optional[str] = None  # "static", "pan", "zoom", "tracking"


class Storyboard(BaseModel):
    """AI-generated storyboard (shot list)."""

    title: str
    shots: List[Shot]
    total_duration_seconds: float

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Anchor Handling Best Practices",
                "shots": [
                    {
                        "shot_number": 1,
                        "scene_name": "Vessel at sea",
                        "camera_angle": "wide",
                        "action_description": "Establishing shot of vessel",
                        "duration_seconds": 3.0,
                        "narrative_lines": [1],
                        "key_objects": ["vessel", "sea"],
                        "camera_movement": "static",
                    }
                ],
                "total_duration_seconds": 120.0,
            }
        }


# ============ Scene JSON (Scene Definition) ============


class Vector3(BaseModel):
    """3D vector (x, y, z)."""

    x: float
    y: float
    z: float


class Object3D(BaseModel):
    """3D object in a scene."""

    id: str
    asset_name: str  # Reference to asset library
    position: Vector3
    rotation: Vector3
    scale: Vector3
    material_override: Optional[Dict[str, Any]] = None
    animation: Optional[Dict[str, Any]] = None  # Keyframes, etc.


class CameraKeyframe(BaseModel):
    """Camera position/rotation at a specific time."""

    time_seconds: float
    position: Vector3
    look_at: Vector3
    fov: float = 50.0  # Field of view


class CameraPath(BaseModel):
    """Camera motion through a scene."""

    keyframes: List[CameraKeyframe]
    interpolation: str = "linear"  # "linear", "bezier", "constant"


class Lighting(BaseModel):
    """Lighting setup."""

    ambient_strength: float = 0.5
    key_light_angle: Vector3 = Field(default_factory=lambda: Vector3(x=45, y=45, z=0))
    key_light_strength: float = 1.0
    fill_light_strength: float = 0.3
    shadows_enabled: bool = True


class SceneDefinition(BaseModel):
    """Complete Scene JSON: objects, camera, timing, rendering params."""

    scene_number: int
    name: str
    duration_seconds: float
    description: str
    objects: List[Object3D] = Field(default_factory=list)
    camera_path: CameraPath
    lighting: Lighting = Field(default_factory=Lighting)
    background_color: str = "#87CEEB"  # Sky blue default
    render_samples: int = 128
    render_quality: str = "high"  # "preview", "medium", "high"
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "scene_number": 1,
                "name": "Establishing Shot",
                "duration_seconds": 3.0,
                "description": "Wide shot of vessel at sea",
                "objects": [
                    {
                        "id": "vessel_main",
                        "asset_name": "cargo-vessel-01",
                        "position": {"x": 0, "y": 0, "z": 0},
                        "rotation": {"x": 0, "y": 0, "z": 0},
                        "scale": {"x": 1, "y": 1, "z": 1},
                    }
                ],
                "camera_path": {
                    "keyframes": [
                        {
                            "time_seconds": 0,
                            "position": {"x": 50, "y": 30, "z": 50},
                            "look_at": {"x": 0, "y": 0, "z": 0},
                            "fov": 50,
                        }
                    ],
                    "interpolation": "linear",
                },
                "lighting": {
                    "ambient_strength": 0.5,
                    "key_light_angle": {"x": 45, "y": 45, "z": 0},
                    "key_light_strength": 1.0,
                },
                "render_samples": 128,
                "render_quality": "high",
            }
        }


class ScenePlan(BaseModel):
    """Complete plan for a video: all scenes."""

    title: str
    total_duration_seconds: float
    scenes: List[SceneDefinition]
    metadata: Optional[Dict[str, Any]] = None


# ============ AI Planning Output ============


class AIPlanningOutput(BaseModel):
    """Output of the entire AI planning pipeline."""

    script: Script
    storyboard: Storyboard
    scene_plan: ScenePlan
    planning_notes: Optional[str] = None
