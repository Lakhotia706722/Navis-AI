# API Contracts - Phase 2: Projects & Render Jobs

## Overview

Phase 2 adds CRUD endpoints for projects and render job management. All endpoints require JWT authentication (Bearer token from `/api/auth/login`).

**Base URL:** `http://localhost:8000`

**Content-Type:** `application/json`

**Auth Header:** `Authorization: Bearer <token>`

## Endpoints

### Projects

#### POST /api/projects

Create a new project.

**Request:**
```json
{
  "title": "Marine Safety Training",
  "description": "A video on marine safety protocols",
  "prompt": "Create a 5-minute video on how to properly secure cargo on a vessel"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Marine Safety Training",
  "description": "A video on marine safety protocols",
  "prompt": "Create a 5-minute video on how to properly secure cargo on a vessel",
  "status": "queued",
  "created_at": "2026-07-12T17:30:00",
  "updated_at": "2026-07-12T17:30:00"
}
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `422 Unprocessable Entity` — Missing required fields

---

#### GET /api/projects

List all projects for the authenticated user.

**Request:** (no body)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Marine Safety Training",
    "description": "A video on marine safety protocols",
    "prompt": "Create a 5-minute video...",
    "status": "done",
    "created_at": "2026-07-12T17:30:00",
    "updated_at": "2026-07-12T18:45:00"
  },
  {
    "id": 2,
    "user_id": 1,
    "title": "Anchor Handling Guide",
    "description": null,
    "prompt": "Create a video on anchor handling...",
    "status": "queued",
    "created_at": "2026-07-12T18:00:00",
    "updated_at": "2026-07-12T18:00:00"
  }
]
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token

---

#### GET /api/projects/{project_id}

Get a specific project with render jobs.

**Request:** (no body)

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Marine Safety Training",
  "description": "A video on marine safety protocols",
  "prompt": "Create a 5-minute video...",
  "status": "done",
  "created_at": "2026-07-12T17:30:00",
  "updated_at": "2026-07-12T18:45:00",
  "render_jobs": [
    {
      "id": 1,
      "project_id": 1,
      "status": "done",
      "progress_percent": 100,
      "render_mode": "full",
      "output_video_path": "s3://maritime-studio/renders/render-1.mp4",
      "error_message": null,
      "estimated_duration_seconds": 300,
      "started_at": "2026-07-12T17:31:00",
      "completed_at": "2026-07-12T18:45:00",
      "created_at": "2026-07-12T17:30:00",
      "updated_at": "2026-07-12T18:45:00"
    }
  ]
}
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `403 Forbidden` — Project belongs to another user
- `404 Not Found` — Project doesn't exist

---

#### PUT /api/projects/{project_id}

Update a project.

**Request:**
```json
{
  "title": "Updated Title",
  "description": "New description",
  "prompt": "Updated prompt"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Updated Title",
  "description": "New description",
  "prompt": "Updated prompt",
  "status": "queued",
  "created_at": "2026-07-12T17:30:00",
  "updated_at": "2026-07-12T18:50:00"
}
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `403 Forbidden` — Project belongs to another user
- `404 Not Found` — Project doesn't exist

---

#### DELETE /api/projects/{project_id}

Delete a project (cascades to render jobs, scenes, usage logs).

**Request:** (no body)

**Response (204 No Content)** — Empty

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `403 Forbidden` — Project belongs to another user
- `404 Not Found` — Project doesn't exist

---

### Render Jobs

#### POST /api/renders/{project_id}/start

Start a new render job for a project.

**Query Parameters:**
- `render_mode` (optional): `preview` (fast, 16 samples) or `full` (production, 128 samples). Default: `full`

**Request:** (no body, mode in query params)

**Response (200 OK):**
```json
{
  "id": 1,
  "project_id": 1,
  "status": "queued",
  "progress_percent": 0,
  "render_mode": "full",
  "output_video_path": null,
  "error_message": null,
  "estimated_duration_seconds": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2026-07-12T18:00:00",
  "updated_at": "2026-07-12T18:00:00"
}
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `403 Forbidden` — Project belongs to another user
- `404 Not Found` — Project doesn't exist
- `422 Unprocessable Entity` — Invalid render_mode

---

#### GET /api/renders/{render_job_id}

Get render job status and details.

**Request:** (no body)

**Response (200 OK):**
```json
{
  "id": 1,
  "project_id": 1,
  "status": "rendering",
  "progress_percent": 65,
  "render_mode": "full",
  "output_video_path": null,
  "error_message": null,
  "estimated_duration_seconds": 300,
  "started_at": "2026-07-12T18:00:30",
  "completed_at": null,
  "created_at": "2026-07-12T18:00:00",
  "updated_at": "2026-07-12T18:05:30",
  "scenes": []
}
```

**Status Values:**
- `queued` — Waiting for worker to pick up
- `planning` — AI planning phase (script, storyboard, scene plan)
- `composing` — Asset selection and voice synthesis
- `rendering` — Blender rendering scenes
- `assembling` — FFmpeg composing final video
- `done` — Complete
- `failed` — Error occurred

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `403 Forbidden` — Render job's project belongs to another user
- `404 Not Found` — Render job doesn't exist

---

#### POST /api/renders/{render_job_id}/cancel

Cancel a running render job.

**Request:** (no body)

**Response (200 OK):**
```json
{
  "id": 1,
  "project_id": 1,
  "status": "failed",
  "progress_percent": 65,
  "render_mode": "full",
  "output_video_path": null,
  "error_message": "Cancelled by user",
  "estimated_duration_seconds": 300,
  "started_at": "2026-07-12T18:00:30",
  "completed_at": "2026-07-12T18:06:00",
  "created_at": "2026-07-12T18:00:00",
  "updated_at": "2026-07-12T18:06:00"
}
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `403 Forbidden` — Render job's project belongs to another user
- `404 Not Found` — Render job doesn't exist
- `409 Conflict` — Cannot cancel job that's already done or failed

---

#### GET /api/projects/{project_id}/renders

List all render jobs for a project.

**Request:** (no body)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "project_id": 1,
    "status": "done",
    "progress_percent": 100,
    "render_mode": "full",
    "output_video_path": "s3://maritime-studio/renders/render-1.mp4",
    "error_message": null,
    "estimated_duration_seconds": 300,
    "started_at": "2026-07-12T17:31:00",
    "completed_at": "2026-07-12T18:45:00",
    "created_at": "2026-07-12T17:30:00",
    "updated_at": "2026-07-12T18:45:00"
  },
  {
    "id": 2,
    "project_id": 1,
    "status": "rendering",
    "progress_percent": 50,
    "render_mode": "preview",
    "output_video_path": null,
    "error_message": null,
    "estimated_duration_seconds": 120,
    "started_at": "2026-07-12T18:50:00",
    "completed_at": null,
    "created_at": "2026-07-12T18:50:00",
    "updated_at": "2026-07-12T18:55:00"
  }
]
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `403 Forbidden` — Project belongs to another user
- `404 Not Found` — Project doesn't exist

---

## Examples

### Complete Workflow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure123",
    "full_name": "User Name"
  }'

# 2. Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure123"
  }' | jq -r '.access_token')

# 3. Create project
PROJECT=$(curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Anchor Training",
    "description": "Learn how to properly handle anchors",
    "prompt": "Create a 2-minute video on anchor handling best practices"
  }')

PROJECT_ID=$(echo $PROJECT | jq -r '.id')
echo "Created project: $PROJECT_ID"

# 4. List projects
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" | jq

# 5. Get specific project
curl http://localhost:8000/api/projects/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN" | jq

# 6. Start render job
RENDER=$(curl -X POST http://localhost:8000/api/renders/$PROJECT_ID/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"render_mode": "preview"}')

RENDER_ID=$(echo $RENDER | jq -r '.id')
echo "Started render: $RENDER_ID"

# 7. Poll render status (keep checking until done)
curl http://localhost:8000/api/renders/$RENDER_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.status, .progress_percent'

# 8. Cancel render (if needed)
curl -X POST http://localhost:8000/api/renders/$RENDER_ID/cancel \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## State Machine

Projects and render jobs follow this status flow:

```
Create Project → status: "queued"
  ↓
Start Render → RenderJob status: "queued"
  ↓
Worker picks up → status: "planning" (10% progress)
  ↓
Scenes planned → status: "composing" (30% progress)
  ↓
Voice/assets ready → status: "rendering" (60% progress)
  ↓
Blender done → status: "assembling" (90% progress)
  ↓
FFmpeg done → status: "done" (100% progress, output_video_path set)
  ↓
ERROR at any step → status: "failed", error_message set
```

---

## Storage Integration

Output files are stored in S3/MinIO:
- Rendered video: `s3://maritime-studio/renders/render-{render_job_id}.mp4`
- Assets: `s3://maritime-studio/assets/{asset_name}.{format}`
- Audio: `s3://maritime-studio/audio/render-{render_job_id}.mp3`
- Subtitles: `s3://maritime-studio/subtitles/render-{render_job_id}.srt`

---

## Job Queue (Celery)

- Jobs are enqueued to Redis when `POST /api/renders/{project_id}/start` is called
- Worker picks up and processes, updating `render_jobs.status` and `progress_percent`
- In Phase 2, a dummy task just moves through the state machine
- Phase 3+ will replace with real AI planning, Blender rendering, and FFmpeg assembly
