# Scene JSON Specification

## Overview

Scene JSON is the complete definition of a single 3D scene in a maritime training video. It defines:
- 3D objects and their positions
- Camera path and movement
- Lighting setup
- Rendering parameters
- Timing and duration

This document formally specifies the Scene JSON schema.

## Schema

### Root: `SceneDefinition`

```typescript
{
  scene_number: number,           // Order in video (1, 2, 3, ...)
  name: string,                   // Scene title (e.g., "Anchor Deployment")
  duration_seconds: number,       // Length in seconds (e.g., 5.0)
  description: string,            // What happens in this scene
  objects: Object3D[],            // 3D objects in scene
  camera_path: CameraPath,        // Camera motion
  lighting: Lighting,             // Light setup
  background_color: string,       // Hex color (e.g., "#87CEEB")
  render_samples: number,         // 16 (preview) or 128 (full)
  render_quality: string,         // "preview", "medium", "high"
  notes: string?                  // Optional notes for animator
}
```

### Object3D

A 3D model placed in the scene.

```typescript
{
  id: string,                     // Unique ID within scene (e.g., "vessel_main")
  asset_name: string,             // Asset library reference (e.g., "cargo-vessel-01")
  position: Vector3,              // World position (x, y, z)
  rotation: Vector3,              // Euler rotation in degrees (x, y, z)
  scale: Vector3,                 // Scale multiplier (1.0 = normal size)
  material_override?: {           // Optional material overrides
    color?: string,               // Hex color
    metallic?: number,            // 0.0-1.0
    roughness?: number            // 0.0-1.0
  },
  animation?: {                   // Optional animation keyframes
    keyframes: [{
      time: number,               // Time in seconds
      position?: Vector3,
      rotation?: Vector3,
      scale?: Vector3
    }],
    interpolation: "linear" | "bezier"
  }
}
```

### Vector3

3D coordinate or rotation.

```typescript
{
  x: number,
  y: number,
  z: number
}
```

### CameraPath

Camera motion through the scene.

```typescript
{
  keyframes: CameraKeyframe[],    // Camera positions over time
  interpolation: "linear" | "bezier" | "constant"
}
```

### CameraKeyframe

Camera position and orientation at a specific time.

```typescript
{
  time_seconds: number,           // Time in scene (0 to duration_seconds)
  position: Vector3,              // Camera world position
  look_at: Vector3,               // Point camera is looking at
  fov: number                     // Field of view in degrees (45-65 typical)
}
```

### Lighting

Scene lighting setup.

```typescript
{
  ambient_strength: number,       // 0.0-1.0 (global illumination)
  key_light_angle: Vector3,       // Direction of main light (x, y, z degrees)
  key_light_strength: number,     // 0.0-2.0 (main light intensity)
  fill_light_strength: number,    // 0.0-1.0 (fill light for shadows)
  shadows_enabled: boolean        // Ray-traced shadows
}
```

## Examples

### Example 1: Simple Anchor on Deck

```json
{
  "scene_number": 1,
  "name": "Anchor on Deck",
  "duration_seconds": 5.0,
  "description": "Close-up of anchor on ship deck with rope",
  "objects": [
    {
      "id": "deck_main",
      "asset_name": "deck",
      "position": {"x": 0, "y": 0, "z": 0},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    },
    {
      "id": "anchor_main",
      "asset_name": "anchor-01",
      "position": {"x": 2, "y": 0.5, "z": 0},
      "rotation": {"x": 0, "y": 45, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    },
    {
      "id": "rope_attached",
      "asset_name": "rope-coil",
      "position": {"x": 0, "y": 0.8, "z": -1},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 1.5, "y": 1.5, "z": 1.5}
    }
  ],
  "camera_path": {
    "keyframes": [
      {
        "time_seconds": 0,
        "position": {"x": 5, "y": 2, "z": 5},
        "look_at": {"x": 0, "y": 0.5, "z": 0},
        "fov": 50
      },
      {
        "time_seconds": 5,
        "position": {"x": 3, "y": 1.5, "z": 2},
        "look_at": {"x": 1.5, "y": 0.5, "z": 0},
        "fov": 50
      }
    ],
    "interpolation": "linear"
  },
  "lighting": {
    "ambient_strength": 0.6,
    "key_light_angle": {"x": 45, "y": 60, "z": 0},
    "key_light_strength": 1.2,
    "fill_light_strength": 0.4,
    "shadows_enabled": true
  },
  "background_color": "#87CEEB",
  "render_samples": 128,
  "render_quality": "high"
}
```

### Example 2: Wide Establishing Shot of Vessel

```json
{
  "scene_number": 1,
  "name": "Vessel at Sea",
  "duration_seconds": 3.0,
  "description": "Establishing shot of cargo vessel at sea",
  "objects": [
    {
      "id": "vessel_main",
      "asset_name": "cargo-vessel-01",
      "position": {"x": 0, "y": 0, "z": 0},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1}
    },
    {
      "id": "sea_plane",
      "asset_name": "sea",
      "position": {"x": 0, "y": -10, "z": 0},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 10, "y": 1, "z": 10}
    },
    {
      "id": "sky_dome",
      "asset_name": "sky",
      "position": {"x": 0, "y": 50, "z": 0},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 100, "y": 100, "z": 100}
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
    "ambient_strength": 0.7,
    "key_light_angle": {"x": 30, "y": 45, "z": 0},
    "key_light_strength": 1.0,
    "fill_light_strength": 0.3,
    "shadows_enabled": true
  },
  "background_color": "#87CEEB",
  "render_samples": 128,
  "render_quality": "high"
}
```

## Coordinate System

**Blender convention (used throughout):**
- **X-axis:** Left/Right (positive = right)
- **Y-axis:** Up/Down (positive = up)
- **Z-axis:** Forward/Backward (positive = forward/away)

**Rotations (Euler angles):**
- Degrees (0-360 or -180 to 180)
- Order: XYZ (applied in order)
- Positive rotation = counterclockwise when looking from positive axis toward origin

## Position Guidelines

**For maritime scenes:**

| Object | Typical Position |
|--------|-----------------|
| Sea plane | y = -10 to -20 (below vessel) |
| Vessel (main) | (0, 0, 0) - origin |
| Anchor (on deck) | (±2-5, 0.5-1.5, ±1-3) |
| Rope coils | (±3-6, 1-2, -5 to -10) |
| Sky dome | (0, 50-100, 0) - far above |
| Camera | 20-100 units away from origin |

## Camera Guidelines

**For maritime training videos:**

| Shot Type | Position | Look At | FOV |
|-----------|----------|---------|-----|
| Wide establishing | (50-100, 30-50, 50-100) | (0, 0, 0) | 45-55° |
| Medium close-up | (10-20, 5-10, 10-20) | (0, 1, 0) | 50-60° |
| Close-up detail | (3-8, 2-5, 3-8) | (0, 0.5, 0) | 55-70° |
| Overhead | (20-50, 50-100, 20-50) | (0, 0, 0) | 45-60° |
| Tracking (moving) | Multiple keyframes | Follows action | 50-65° |

## Lighting Guidelines

**Typical maritime lighting:**
- **Daylight exterior:** ambient 0.5-0.7, key 0.9-1.2, fill 0.3-0.5
- **Overcast:** ambient 0.7-0.9, key 0.7-0.9, fill 0.5-0.7
- **Dramatic/training focus:** ambient 0.4-0.5, key 1.2-1.5, fill 0.2-0.3
- **Always enable shadows** for realistic maritime scenes

## Validation Rules

✅ **Valid Scene JSON must have:**
1. scene_number > 0
2. duration_seconds > 0
3. At least one object OR a clear environment setup
4. At least one camera keyframe
5. camera_path keyframes sorted by time_seconds
6. first keyframe at time_seconds = 0
7. last keyframe at time_seconds ≤ duration_seconds

❌ **Invalid Scene JSON:**
- Missing required fields
- Objects with non-existent asset names (checked against asset library in Phase 5)
- Camera keyframes outside duration
- Negative durations or samples
- render_samples < 1

## Phase 6: Blender Import

Blender automation (Phase 6) will:
1. Read Scene JSON
2. Validate structure
3. Load asset .blend files from S3
4. Position objects per coordinates
5. Set up camera with keyframes
6. Configure lighting
7. Set render settings (samples, quality)
8. Render animation
9. Output frames as PNG sequence

See `blender/scene_loader.py` (Phase 6) for import logic.

## Future Extensions (Post-MVP)

- Material animations (color/texture over time)
- Particle effects (water spray, smoke)
- Dynamic simulations (cloth, rigid body)
- Audio sync markers (mark where narration peaks)
- Depth of field parameters
- Motion blur settings
