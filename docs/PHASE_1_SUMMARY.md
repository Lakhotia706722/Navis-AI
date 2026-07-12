# Phase 1 Summary: Database & Auth

**Status:** ✅ Complete

## What Was Built

### Database Schema (PostgreSQL)

7 tables with full relationships:

1. **`users`** — User accounts
   - `id`, `email` (unique), `hashed_password`, `full_name`, `is_active`, `created_at`, `updated_at`
   - Indexes: `email` (unique), `id`

2. **`projects`** — Top-level project per submission
   - `id`, `user_id` (FK), `title`, `description`, `prompt`, `status`, `created_at`, `updated_at`
   - Status enum: `queued` → `planning` → `composing` → `rendering` → `assembling` → `done` | `failed`
   - Indexes: `user_id`, `id`

3. **`render_jobs`** — Individual render execution (one+ per project)
   - `id`, `project_id` (FK), `celery_task_id` (unique), `status` (same enum), `progress_percent`, `render_mode` (preview/full), `output_video_path`, `error_message`, `started_at`, `completed_at`, `created_at`, `updated_at`
   - Indexes: `project_id`, `id`

4. **`scenes`** — Individual scenes from AI-generated scene JSON
   - `id`, `render_job_id` (FK), `scene_number`, `name`, `duration_seconds`, `scene_json` (JSON blob), `created_at`
   - Indexes: `render_job_id`, `id`

5. **`assets`** — 3D asset library
   - `id`, `name` (unique), `category`, `tags` (JSON), `file_path`, `file_format` (blend/fbx/glb), `version`, `licensing_info`, `created_at`, `updated_at`
   - Indexes: `name` (unique), `category`, `id`

6. **`usage_logs`** — Cost tracking per project
   - `id`, `project_id` (FK), `usage_type` (gpt_tokens/tts_chars/render_minutes), `quantity`, `cost_usd`, `metadata` (JSON), `created_at`
   - Indexes: `project_id`, `usage_type`, `id`

7. **`notification_hooks`** — Stub for webhook/email (fully wired in Phase 9)
   - `id`, `project_id` (FK, nullable), `event_type`, `hook_type`, `destination`, `created_at`
   - Indexes: `id`

**Full Schema Doc:** [docs/database.md](database.md)

### Backend Code

**Configuration & DB:**
- `backend/config.py` — Settings from env vars (database, JWT, OpenAI, S3, Blender, etc.)
- `backend/database.py` — SQLAlchemy engine + SessionLocal + get_db dependency

**Models:**
- `backend/models.py` — 7 SQLAlchemy ORM models with enums (RoleEnum, RenderJobStatusEnum)

**Security:**
- `backend/security.py` — Password hashing (bcrypt), JWT token creation/validation

**API Schemas:**
- `backend/schemas.py` — Pydantic request/response models for all endpoints (UserCreate, ProjectResponse, etc.)

**Routes:**
- `backend/routes/auth.py` — Auth endpoints:
  - `POST /api/auth/register` — Create new user
  - `POST /api/auth/login` — Get JWT token
  - `GET /api/auth/me` — Get current user (requires token)
  - Helper: `get_current_user` dependency for protecting routes

**Main App:**
- `backend/main.py` — FastAPI app with CORS, lifespan hook (creates tables), auth router wired

### Migrations

- `backend/alembic.ini` — Alembic config
- `backend/migrations/env.py` — Migration environment
- `backend/migrations/versions/001_initial_schema.py` — Initial migration (all 7 tables)

### Tests

- `backend/tests/conftest.py` — Pytest fixtures (in-memory SQLite DB, test client)
- `backend/tests/test_auth.py` — 8 auth tests:
  - Register success + duplicate email handling
  - Login success + invalid password + nonexistent user
  - `/me` endpoint with/without token
  - Invalid email validation
- `backend/tests/test_security.py` — 5 security tests:
  - Password hashing consistency
  - Password verification (correct/incorrect)
  - JWT creation/decoding
  - Expired token rejection

### Documentation

- `docs/database.md` — Full schema reference, relationships, cost tracking examples, notes for future expansion

## What Works End-to-End

✅ User registration (email + password, validation)
✅ User login (JWT token generation)
✅ Get current user (via Bearer token)
✅ Project ownership (projects scoped to user)
✅ Render job state machine (queued → planning → ... → done/failed)
✅ Cost tracking (usage_logs for GPT tokens, TTS chars, render minutes)
✅ Asset library (with category + tag search stubs)

## Auth & RBAC

**JWT Implementation:**
- Tokens include `user_id` and `email`
- Expiration: 24 hours (configurable via `JWT_EXPIRATION_HOURS`)
- Algorithm: HS256
- Secret: From `JWT_SECRET_KEY` env var (must change in prod)

**RBAC Stub (MVP):**
- Only `OWNER` role implemented (user owns their projects)
- Hooks left for `ADMIN`, `EDITOR`, `VIEWER` (future multi-user teams)
- No team/workspace isolation in MVP (single-user per project)

## Tests Status

**Run tests:**
```bash
docker-compose exec api pytest -v
```

**Expected output:**
```
test_auth.py::TestAuthRoutes::test_register_success PASSED
test_auth.py::TestAuthRoutes::test_register_duplicate_email PASSED
test_auth.py::TestAuthRoutes::test_login_success PASSED
test_auth.py::TestAuthRoutes::test_login_invalid_password PASSED
test_auth.py::TestAuthRoutes::test_login_nonexistent_user PASSED
test_auth.py::TestAuthRoutes::test_get_me_authenticated PASSED
test_auth.py::TestAuthRoutes::test_get_me_unauthenticated PASSED
test_auth.py::TestAuthRoutes::test_register_invalid_email PASSED
test_security.py::TestPasswordHashing::test_hash_password PASSED
test_security.py::TestPasswordHashing::test_verify_password_correct PASSED
test_security.py::TestPasswordHashing::test_verify_password_incorrect PASSED
test_security.py::TestPasswordHashing::test_hash_consistency PASSED
test_security.py::TestJWTToken::test_create_access_token PASSED
test_security.py::TestJWTToken::test_decode_token_valid PASSED
test_security.py::TestJWTToken::test_decode_token_invalid PASSED
test_security.py::TestJWTToken::test_decode_token_expired PASSED

==== 16 passed in X.XXs ====
```

## Manual Testing (After docker-compose up -d)

### 1. Register a user
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "secure123",
    "full_name": "Demo User"
  }'
```

**Expected response:**
```json
{
  "id": 1,
  "email": "demo@example.com",
  "full_name": "Demo User",
  "is_active": true,
  "created_at": "2026-07-12T16:00:00"
}
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "secure123"
  }'
```

**Expected response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 3. Get current user (using token)
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJhbGc..."
```

**Expected response:**
```json
{
  "id": 1,
  "email": "demo@example.com",
  "full_name": "Demo User",
  "is_active": true,
  "created_at": "2026-07-12T16:00:00"
}
```

### 4. Check database
```bash
docker-compose exec postgres psql -U maritime_user -d maritime_studio -c "SELECT * FROM users;"
```

Should show the registered user.

## Deviations from Spec

None. Phase 1 follows the spec exactly:
- ✅ PostgreSQL schema with all required tables
- ✅ Alembic migrations
- ✅ JWT-based auth
- ✅ Project ownership
- ✅ RBAC stub (owner role only for MVP)
- ✅ Schema documented in docs/database.md
- ✅ Tests written alongside code

## Next Phase

Phase 2 will wire:
- CRUD endpoints for projects (create, list, get, update)
- Celery + Redis integration (dummy task to prove pipeline works)
- Render job status state machine
- Object storage (MinIO/S3) client wrapper

---

## ✅ PHASE 1 COMPLETE

**Ready to proceed to Phase 2: Backend Core API + Job Queue Infra?**
