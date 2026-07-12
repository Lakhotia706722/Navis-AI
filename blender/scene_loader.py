"""Blender scene loader: reads Scene JSON and builds 3D scene."""
import bpy
import json
import os
from typing import Dict, Any, List


def clear_scene():
    """Clear all objects from the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Remove all meshes and materials
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh, do_unlink=True)


def import_asset_blend(asset_path: str, object_name: str) -> str:
    """
    Import a Blender file as a linked object.

    Args:
        asset_path: Path to .blend file (local or S3 path converted to local)
        object_name: Name to give imported object in scene

    Returns:
        Name of imported object in scene
    """
    if not os.path.exists(asset_path):
        raise FileNotFoundError(f"Asset file not found: {asset_path}")

    # Link objects from asset .blend
    with bpy.data.libraries.load(asset_path) as (data_from, data_to):
        data_to.objects = data_from.objects

    # Add linked objects to scene
    scene = bpy.context.scene
    for obj in data_to.objects:
        scene.collection.objects.link(obj)

    return object_name


def create_object_from_scene_def(scene_def: Dict[str, Any], render_cache: Dict) -> str:
    """
    Create a single 3D object in the scene from scene definition.

    For MVP: use primitive shapes (cubes, spheres) as placeholders.
    Phase 7+: import real asset files.

    Args:
        scene_def: Object definition {id, asset_name, position, rotation, scale}
        render_cache: Cache of loaded assets

    Returns:
        Name of created object
    """
    obj_id = scene_def.get("id", "object")
    asset_name = scene_def.get("asset_name", "placeholder")

    # Position
    pos = scene_def.get("position", {})
    position = (pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))

    # Rotation (in degrees, convert to radians)
    import math
    rot = scene_def.get("rotation", {})
    rotation = (
        math.radians(rot.get("x", 0)),
        math.radians(rot.get("y", 0)),
        math.radians(rot.get("z", 0)),
    )

    # Scale
    scale_def = scene_def.get("scale", {})
    scale = (scale_def.get("x", 1), scale_def.get("y", 1), scale_def.get("z", 1))

    # For MVP: create a cube as placeholder
    # Phase 7+: would import from asset_name
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=position)
    obj = bpy.context.active_object
    obj.name = obj_id
    obj.rotation_euler = rotation
    obj.scale = scale

    return obj_id


def setup_camera_from_path(camera_path: Dict[str, Any]) -> None:
    """
    Set up camera and keyframes from camera path definition.

    Args:
        camera_path: {keyframes: [...], interpolation: "linear"}
    """
    scene = bpy.context.scene

    # Create or get camera
    if "Camera" not in bpy.data.objects:
        bpy.ops.object.camera_add()
    camera = bpy.data.objects["Camera"]
    scene.camera = camera

    keyframes = camera_path.get("keyframes", [])
    if not keyframes:
        return

    # Set up keyframe animation
    scene.frame_start = 0
    total_frames = int(keyframes[-1].get("time_seconds", 1.0) * scene.render.fps)
    scene.frame_end = max(total_frames, 1)

    for kf in keyframes:
        time_sec = kf.get("time_seconds", 0)
        frame_num = int(time_sec * scene.render.fps)

        # Set frame
        scene.frame_set(frame_num)

        # Set position
        pos = kf.get("position", {})
        camera.location = (pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))

        # Set look_at (via rotation)
        look_at = kf.get("look_at", {})
        target = (look_at.get("x", 0), look_at.get("y", 0), look_at.get("z", 0))
        direction = (target[0] - camera.location[0], target[1] - camera.location[1], target[2] - camera.location[2])
        import math
        camera.rotation_euler = (
            math.atan2(direction[2], math.sqrt(direction[0]**2 + direction[1]**2)),
            0,
            math.atan2(direction[0], direction[1]),
        )

        # Insert keyframes
        camera.keyframe_insert(data_path="location", frame=frame_num)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame_num)

        # FOV
        fov = kf.get("fov", 50)
        camera.data.angle = math.radians(fov)
        camera.data.keyframe_insert(data_path="lens", frame=frame_num)


def setup_lighting(lighting_def: Dict[str, Any]) -> None:
    """
    Set up scene lighting from lighting definition.

    Args:
        lighting_def: {ambient_strength, key_light_angle, key_light_strength, ...}
    """
    scene = bpy.context.scene

    # World ambient light
    world = bpy.data.worlds["World"]
    ambient = lighting_def.get("ambient_strength", 0.5)
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = ambient

    # Key light (sun)
    if "KeyLight" not in bpy.data.objects:
        bpy.ops.object.light_add(type='SUN')
    key_light = bpy.data.objects.get("KeyLight") or bpy.context.active_object
    key_light.name = "KeyLight"

    angle = lighting_def.get("key_light_angle", {})
    key_light.location = (angle.get("x", 45), angle.get("y", 45), angle.get("z", 0))
    key_light.data.energy = lighting_def.get("key_light_strength", 1.0)

    # Fill light (optional)
    if "FillLight" not in bpy.data.objects:
        bpy.ops.object.light_add(type='SUN', location=(-5, -5, 5))
    fill_light = bpy.data.objects.get("FillLight")
    if fill_light:
        fill_light.data.energy = lighting_def.get("fill_light_strength", 0.3)

    # Shadows
    if lighting_def.get("shadows_enabled", True):
        world.cycles.use_caustics = True


def load_scene_from_json(scene_json: Dict[str, Any], render_cache: Dict = None) -> None:
    """
    Load a complete scene from Scene JSON definition.

    Args:
        scene_json: Complete SceneDefinition (from database)
        render_cache: Optional cache for loaded assets
    """
    if render_cache is None:
        render_cache = {}

    # Clear scene
    clear_scene()

    # Set background color
    bg_color = scene_json.get("background_color", "#87CEEB")
    # Parse hex color
    if bg_color.startswith("#"):
        r = int(bg_color[1:3], 16) / 255.0
        g = int(bg_color[3:5], 16) / 255.0
        b = int(bg_color[5:7], 16) / 255.0
    else:
        r, g, b = 0.5, 0.5, 0.5

    world = bpy.data.worlds["World"]
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (r, g, b, 1.0)

    # Create objects
    for obj_def in scene_json.get("objects", []):
        try:
            create_object_from_scene_def(obj_def, render_cache)
        except Exception as e:
            print(f"Warning: Failed to create object {obj_def.get('id')}: {e}")

    # Set up camera
    camera_path = scene_json.get("camera_path", {})
    setup_camera_from_path(camera_path)

    # Set up lighting
    lighting = scene_json.get("lighting", {})
    setup_lighting(lighting)

    # Set render settings
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'

    render_quality = scene_json.get("render_quality", "high")
    samples = scene_json.get("render_samples", 128)

    if render_quality == "preview":
        samples = 16
    elif render_quality == "medium":
        samples = 64
    elif render_quality == "high":
        samples = 128

    scene.cycles.samples = samples
    scene.cycles.use_denoising = True

    # Set output format
    duration = scene_json.get("duration_seconds", 5.0)
    scene.frame_start = 0
    scene.frame_end = int(duration * scene.render.fps)

    print(f"Scene loaded: {len(scene_json.get('objects', []))} objects, {samples} samples, {duration}s duration")
