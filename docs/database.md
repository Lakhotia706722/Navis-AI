# Database Schema

## Overview

The PostgreSQL database tracks projects, renders, assets, and usage (for cost control). All data is scoped to a user's projects; there is no multi-tenant isolation needed for MVP.

## Tables

### `users`

User accounts. Each user owns projects.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `email` | VARCHAR(255) UNIQUE NOT NULL | Login email |
| `hashed_password` | VARCHAR(255) NOT NULL | bcrypt hash |
| `full_name` | VARCHAR(255) | Optional display name |
| `is_active` | BOOLEAN DEFAULT TRUE | Soft delete flag |
| `created_at` | DATETIME NOT NULL | Creation timestamp |
| `updated_at` | DATETIME NOT NULL | Last update timestamp |

**Indexes:** `email` (unique), `id`

### `projects`

Top-level project (one per user submission). Owns all downstream data.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `user_id` | INTEGER FK → users.id | Project owner |
| `title` | VARCHAR(255) NOT NULL | Display name |
| `description` | TEXT | Optional project notes |
| `prompt` | TEXT | Original user prompt (input for AI planning) |
| `status` | ENUM NOT NULL | One of: `queued`, `planning`, `composing`, `rendering`, `assembling`, `done`, `failed` |
| `created_at` | DATETIME NOT NULL | Creation timestamp |
| `updated_at` | DATETIME NOT NULL | Last update timestamp |

**Indexes:** `user_id`, `id`

**Status Machine:**
- User submits prompt → `queued`
- Celery job starts AI planning → `planning`
- Scenes + voice plan ready → `composing`
- Blender rendering scenes → `rendering`
- FFmpeg assembling final video → `assembling`
- Output ready → `done`
- Any step fails → `failed`

### `render_jobs`

Tracks a single render execution for a project. Can have multiple (for retries/rerenders).

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `project_id` | INTEGER FK → projects.id | Parent project |
| `celery_task_id` | VARCHAR(255) UNIQUE | Celery task UUID (for job tracking) |
| `status` | ENUM NOT NULL | Same as projects (state machine) |
| `progress_percent` | INTEGER DEFAULT 0 | 0–100, updated as job progresses |
| `render_mode` | VARCHAR(50) DEFAULT 'full' | `preview` (16 samples) or `full` (128 samples) |
| `output_video_path` | VARCHAR(512) | S3 path to final MP4 (null until done) |
| `error_message` | TEXT | Failure reason (if status = `failed`) |
| `estimated_duration_seconds` | INTEGER | Estimated total runtime |
| `started_at` | DATETIME | When job was picked up by worker |
| `completed_at` | DATETIME | When job finished (success or failure) |
| `created_at` | DATETIME NOT NULL | Creation timestamp |
| `updated_at` | DATETIME NOT NULL | Last update timestamp |

**Indexes:** `project_id`, `id`

**State Flow:**
1. Job created, status = `queued`, progress = 0
2. Worker picks up → status = `planning`, starts AI pipeline
3. Script + storyboard ready → status = `composing`, starts asset selection + voice synthesis
4. Voice + assets ready → status = `rendering`, starts Blender
5. Blender frames ready → status = `assembling`, starts FFmpeg
6. MP4 written to S3 → status = `done`, progress = 100
7. On error at any step → status = `failed`, error_message set, completed_at set

### `scenes`

Individual scene within a render job (from AI-generated scene JSON).

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `render_job_id` | INTEGER FK → render_jobs.id | Parent render job |
| `scene_number` | INTEGER NOT NULL | Order in project (1, 2, 3, ...) |
| `name` | VARCHAR(255) NOT NULL | Scene title (e.g., "Anchor deployment") |
| `duration_seconds` | FLOAT NOT NULL | Scene length in seconds |
| `scene_json` | JSON NOT NULL | Full scene definition (objects, camera path, timing) — see docs/scene-json.md |
| `created_at` | DATETIME NOT NULL | Creation timestamp |

**Indexes:** `render_job_id`, `id`

### `assets`

3D asset library (models, meshes, animations). Indexed for fast lookup by scene planner.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `name` | VARCHAR(255) UNIQUE NOT NULL | Asset identifier (e.g., "anchor-01") |
| `category` | VARCHAR(100) NOT NULL | Classification (e.g., "anchor", "rope", "vessel") |
| `tags` | JSON DEFAULT '[]' | Keywords for search (e.g., `["maritime", "equipment", "steel"]`) |
| `file_path` | VARCHAR(512) NOT NULL | S3 path to asset file (.blend, .fbx, .glb) |
| `file_format` | VARCHAR(10) NOT NULL | File type: `blend`, `fbx`, or `glb` |
| `version` | VARCHAR(50) DEFAULT '1.0' | Asset version for tracking updates |
| `licensing_info` | TEXT | License/attribution info |
| `created_at` | DATETIME NOT NULL | Upload timestamp |
| `updated_at` | DATETIME NOT NULL | Last update timestamp |

**Indexes:** `name` (unique), `category`, `id`

### `usage_logs`

Track resource usage (GPT tokens, TTS characters, render minutes) per project for cost tracking and limits.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `project_id` | INTEGER FK → projects.id | Project this usage belongs to |
| `usage_type` | VARCHAR(50) NOT NULL | One of: `gpt_tokens`, `tts_chars`, `render_minutes` |
| `quantity` | INTEGER NOT NULL | Amount used (tokens, chars, or minutes) |
| `cost_usd` | FLOAT | Estimated cost (calculated at log time) |
| `metadata` | JSON | Extra context (e.g., `{"model": "gpt-4-turbo", "provider": "openai"}`) |
| `created_at` | DATETIME NOT NULL | Log timestamp |

**Indexes:** `project_id`, `usage_type`, `id`

**Examples:**
- GPT call with 500 input tokens → `usage_type='gpt_tokens'`, `quantity=500`
- TTS narration of 2000 characters → `usage_type='tts_chars'`, `quantity=2000`
- Blender render taking 45 minutes → `usage_type='render_minutes'`, `quantity=45`

### `notification_hooks`

Webhook/email destinations for job completion/failure. Stub in Phase 1, fully wired in Phase 9.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `project_id` | INTEGER FK → projects.id | Project this hook applies to (null = global) |
| `event_type` | VARCHAR(50) NOT NULL | Event: `render_complete`, `render_failed` |
| `hook_type` | VARCHAR(50) NOT NULL | Destination type: `webhook`, `email` |
| `destination` | VARCHAR(512) NOT NULL | URL or email address |
| `created_at` | DATETIME NOT NULL | Creation timestamp |

**Indexes:** `id`

## Relationships

```
User
  ├─ projects (1 → many)
  │   ├─ render_jobs (1 → many)
  │   │   └─ scenes (1 → many)
  │   └─ usage_logs (1 → many)
  └─ notification_hooks (1 → many, optional)

Assets (standalone, indexed for query)
```

## Migrations

Migrations are managed with Alembic.

**Initial migration:** `backend/migrations/versions/001_initial_schema.py`

To apply:
```bash
alembic upgrade head
```

To rollback:
```bash
alembic downgrade -1
```

## Cost Tracking

`usage_logs` enables project-level cost estimation:

```sql
SELECT 
  project_id,
  SUM(CASE WHEN usage_type='gpt_tokens' THEN quantity ELSE 0 END) as total_tokens,
  SUM(CASE WHEN usage_type='tts_chars' THEN quantity ELSE 0 END) as total_chars,
  SUM(CASE WHEN usage_type='render_minutes' THEN quantity ELSE 0 END) as total_minutes,
  SUM(cost_usd) as total_cost
FROM usage_logs
GROUP BY project_id;
```

This allows per-project billing, alerts, and limits (Phase 9).

## Notes for Future Expansion

- **Multi-user teams:** Add `teams` table, `user_team_roles` junction table, scope projects to teams
- **Billing:** Add `invoices`, `payments` tables, link to `projects` and `usage_logs`
- **Custom fields:** Add `metadata` JSON column to `projects` for extensibility
- **Soft deletes:** Use `deleted_at` timestamps instead of `is_active` boolean if audit trail needed
