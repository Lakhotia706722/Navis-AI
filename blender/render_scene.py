"""Blender script for headless scene rendering.

Usage:
  blender --background --python render_scene.py -- <scene.json> <output_dir> <job_id> <scene_num>
"""
import sys
import json
import os

# Get script arguments (after --)
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

if len(args) < 4:
    print("Usage: blender --background --python render_scene.py -- <scene.json> <output_dir> <job_id> <scene_num>")
    sys.exit(1)

scene_json_path = args[0]
output_dir = args[1]
job_id = args[2]
scene_num = args[3]

print(f"[Blender] Loading scene from {scene_json_path}")
print(f"[Blender] Output directory: {output_dir}")
print(f"[Blender] Job {job_id}, Scene {scene_num}")

try:
    # Load scene JSON
    with open(scene_json_path, "r") as f:
        scene_json = json.load(f)

    print(f"[Blender] Scene loaded: {scene_json.get('name')}")

    # Import scene loader
    import sys
    blender_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, blender_dir)

    from scene_loader import load_scene_from_json
    import bpy

    # Load scene into Blender
    load_scene_from_json(scene_json)

    # Set up rendering
    scene = bpy.context.scene
    scene.render.filepath = os.path.join(output_dir, "frame_")
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.compression = 15

    # Render animation
    print(f"[Blender] Starting render: frames {scene.frame_start}-{scene.frame_end}")
    bpy.ops.render.render(animation=True, write_still=False)

    print(f"[Blender] Render complete")
    print(f"[Blender] Frames saved to {output_dir}")

    sys.exit(0)

except Exception as e:
    print(f"[Blender] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
