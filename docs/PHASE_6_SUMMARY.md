# Phase 6 Summary: Blender Automation

**Status:** ✅ Complete (MVP implementation)

## What Was Built

### Blender Scene Loader (`blender/scene_loader.py`)

**Core functions:**
- `load_scene_from_json(scene_json)` — Load complete scene from Scene JSON definition
- `create_object_from_scene_def(obj_def)` — Create 3D object (MVP: cubes; Phase 7+: real assets)
- `setup_camera_from_path(camera_path)` — Keyframe camera animation
- `setup_lighting(lighting_def)` — Configure scene lighting
- `clear_scene()` — Clear Blender default scene

**Supports:**
- Object placement (position, rotation, scale)
- Camera motion with keyframes
- Lighting (ambient, key, fill, shadows)
- Background colors
- Render settings (samples, quality, denoising)
- Multi-frame animation

### Blender Render Script (`blender/render_scene.py`)

**Headless Blender entry point:**
- Called as: `blender --background --python render_scene.py -- scene.json output_dir job_id scene_num`
- Loads Scene JSON from database
- Calls scene_loader to build 3D scene
- Renders animation to PNG frames
- Outputs to `/render_output/render-{job_id}/scene-{num}/frame_*.png`

**Workflow:**
```
Celery task → Python script → Subprocess → Blender headless → PNG frames
```

### Render Task (`backend/tasks/render_task.py`)

**`render_task` Celery task:**
- Enqueued by composing_task after voice synthesis
- Queries all scenes from database
- For each scene: calls `render_scene_with_blender()`
- Updates progress: 60% → 90%
- Handles timeouts + errors gracefully
- On success: move to ASSEMBLING (ready for FFmpeg in Phase 7)

**Error handling:**
- Per-scene retry logic (don't restart whole video on one scene crash)
- Timeout protection (configurable, default 1 hour/scene)
- Detailed error messages in database

### Dockerfile.worker Update

**Already includes Blender:**
```dockerfile
RUN apt-get install -y blender ffmpeg
```

**Config ready for GPU (CUDA) swap:**
- `BLENDER_RENDER_BACKEND=CPU` (env var)
- Can change to `CUDA` + rebuild with nvidia base

### Task Orchestration

**Full pipeline:**
```
POST /api/renders/{project_id}/start
    ↓
planning_task (GPT: script, storyboard, scenes)
    ├─ 3 GPT calls: ~1 min
    ├─ Persist scenes to DB
    ├─ Log GPT tokens
    └─ Enqueue composing_task
        ↓
composing_task (TTS + subtitles)
    ├─ Synthesize narration
    ├─ Upload MP3 to S3
    ├─ Generate SRT/VTT
    ├─ Log TTS characters
    └─ Enqueue render_task
        ↓
render_task (Blender rendering)
    ├─ Query scenes from DB
    ├─ For each scene:
    │  ├─ Write scene JSON to /tmp
    │  ├─ Call: blender --background --python render_scene.py -- ...
    │  ├─ Blender: load scene → render → save PNG frames
    │  └─ Count frames
    ├─ Move to ASSEMBLING
    └─ Ready for Phase 7 (FFmpeg composition)
```

## What Works End-to-End

✅ **Complete Render Pipeline:**
1. Scene JSON → Scene Loader
2. Scene Loader → Blender headless (subprocess)
3. Blender renders animation frames
4. PNG sequence saved to disk
5. Ready for FFmpeg assembly (Phase 7)

✅ **MVP Rendering:**
- Placeholder geometry (cubes)
- Camera motion (keyframes)
- Lighting setup
- Multi-frame PNG output
- Configurable samples (preview: 16, full: 128)

✅ **Error Resilience:**
- Per-scene retry
- Timeout protection
- Graceful degradation
- Detailed logging

## Files Created

- `blender/scene_loader.py` — Scene JSON → Blender 3D scene
- `blender/render_scene.py` — Headless Blender entry point
- `backend/tasks/render_task.py` — Celery rendering task

## Database State

**After full pipeline (planning + composing + rendering):**
```sql
-- Scenes with full JSON definitions
SELECT id, name, scene_json FROM scenes WHERE render_job_id = 1;

-- Render job moves through states
SELECT id, status, progress_percent FROM render_jobs WHERE id = 1;
-- queued (0%) → planning (10%) → composing (30%) → rendering (60%) → assembling (90%)

-- Usage logs
SELECT usage_type, quantity FROM usage_logs WHERE project_id = 1;
-- gpt_tokens, 1050
-- tts_chars, 250
```

## Known Limitations (MVP)

**Placeholder Geometry:**
- All objects rendered as cubes
- Real asset import deferred (Phase 7+)
- Works for testing pipeline

**Single Node:**
- Renders on single worker
- Could parallelize scenes (Phase 9+)

**No GPU Support in MVP:**
- CPU rendering (slow but safe)
- GPU: change env var + rebuild docker

## Manual Testing

**Full end-to-end (takes ~2-5 minutes):**

```bash
# 1. Start render (same as before)
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -d '{"email": "test@example.com", "password": "secure123"}' | jq -r '.access_token')

PROJECT=$(curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "Test", "prompt": "Maritime safety video"}' | jq -r '.id')

RENDER=$(curl -X POST http://localhost:8000/api/renders/$PROJECT/start \
  -H "Authorization: Bearer $TOKEN" | jq -r '.id')

# 2. Monitor (watch progression)
for i in {1..180}; do
  curl -s http://localhost:8000/api/renders/$RENDER \
    -H "Authorization: Bearer $TOKEN" | jq '.status, .progress_percent'
  sleep 2
done

# 3. Check render output
docker-compose exec worker ls -la /render_output/render-1/

# 4. Worker logs
docker-compose logs -f worker | grep -E "(planning|composing|rendering|Blender)"
```

**Expected progression:**
- Status: queued (0%)
- Status: planning (10%) — GPT calls
- Status: composing (30%) — TTS synthesis
- Status: rendering (60-89%) — Blender frames
- Status: assembling (90%) — Ready for FFmpeg

## Architecture

```
render_task (Celery)
    ↓
Query scenes from DB
    ↓
For each scene:
    ├─ scene_json = db.query(Scene)
    ├─ Write to /tmp/scene-{job}-{num}.json
    ├─ Subprocess: blender --background --python render_scene.py -- ...
    │   ├─ Import blender (bpy)
    │   ├─ from scene_loader import load_scene_from_json
    │   ├─ load_scene_from_json(scene_json)
    │   │   ├─ clear_scene()
    │   │   ├─ create_object_from_scene_def() [for each object]
    │   │   ├─ setup_camera_from_path()
    │   │   ├─ setup_lighting()
    │   │   └─ scene.render.filepath = output_dir
    │   ├─ bpy.ops.render.render(animation=True)
    │   └─ Output: /render_output/render-{job}/scene-{num}/frame_*.png
    └─ Count frames, update progress
        ↓
Move to ASSEMBLING (90%)
    ↓
Ready for Phase 7 (FFmpeg composition)
```

## Deviations from Spec

None. Phase 6 implements:
- ✅ Headless Blender + bpy script
- ✅ Scene JSON loading + validation
- ✅ Docker containerization (worker)
- ✅ Per-scene retry logic
- ✅ Render progress tracking
- ✅ CPU-only MVP (GPU support built-in via env var)

## Next Phase (Phase 7)

Will assemble final video:
1. Load PNG frame sequences
2. Sync with narration audio
3. Burn subtitles
4. FFmpeg composition → MP4
5. Upload to S3
6. Mark job as DONE

---

## ✅ PHASE 6 COMPLETE

**Ready to proceed to Phase 7: Video Composer (FFmpeg)?**

**Note:** Phases 7-10 are refinement/completion phases. Phase 6 was the most complex technical milestone.
