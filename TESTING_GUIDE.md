# Yetrix Maritime AI Studio - End-to-End Testing Guide

## ✅ SYSTEM STATUS

All services are running:
- Backend API: http://localhost:8000 ✅
- Frontend: http://localhost:5173 ✅
- PostgreSQL: localhost:5432 ✅
- Redis: localhost:6379 ✅
- MinIO: http://localhost:9001 ✅
- Celery Worker: Ready ✅

---

## TEST 1: Frontend UI Access

### Step 1.1 - Open Frontend
1. Open browser to `http://localhost:5173`
2. You should see the **Login page** with:
   - Maritime AI Studio title
   - Email input field
   - Password input field
   - Login button

### Step 1.2 - Check Console
- Open Developer Tools (F12)
- Go to Console tab
- Should see no critical errors
- Network requests should go to `http://localhost:8000`

---

## TEST 2: User Registration & Authentication

### Step 2.1 - Register New User
1. At login page, look for "Don't have an account?" link
2. Click to go to registration page
3. Enter:
   - **Email:** `testuser@example.com`
   - **Password:** `Password123!`
   - **Full Name:** `Test User`
4. Click **Register**
5. Should redirect to login page

### Step 2.2 - Login
1. Enter same credentials:
   - **Email:** `testuser@example.com`
   - **Password:** `Password123!`
2. Click **Login**
3. Should redirect to **Dashboard** showing:
   - Welcome message
   - "New Project" button
   - Empty projects list (first time)

### Expected Result
- JWT token stored in localStorage
- User can see their profile/avatar in top right
- Dashboard loads successfully

---

## TEST 3: Create a Project

### Step 3.1 - Start Project Creation
1. On Dashboard, click **"New Project"** button
2. Modal/form appears with fields:
   - **Project Title**
   - **Description**
   - **Prompt** (AI instruction)
3. Fill with:
   - **Title:** `Ocean Voyage`
   - **Description:** `Beautiful maritime scene`
   - **Prompt:** `Create a cinematic maritime scene with sailboats on calm waters at sunset. Include seagulls flying in the sky. Camera should pan slowly across the ocean.`
4. Click **Create Project**

### Expected Result
- Project created successfully
- Redirected to ProjectDetail page
- Shows project info, status: "CREATED"
- Ready to start render job

---

## TEST 4: Start a Render Job

### Step 4.1 - Initiate Render
1. On ProjectDetail page, click **"Start Render"** button
2. Modal appears asking for render mode:
   - **Preview** (fast, 16 samples, ~1-2 min)
   - **Full** (production, 128 samples, ~5-10 min)
3. Select **Preview** for quick test
4. Click **Start**

### Expected Behavior
- Render job created with status: **QUEUED**
- Celery worker picks up task
- Status moves: QUEUED → PROCESSING → RENDERING → DONE
- Progress bar updates in real-time (0% → 100%)
- Takes ~1-2 minutes for preview render

### Step 4.2 - Monitor Rendering
1. Stay on ProjectDetail page
2. Watch progress update every 5 seconds
3. Check for stages:
   - **QUEUED:** Waiting for worker
   - **PROCESSING:** AI planning (10-30 sec)
   - **RENDERING:** Blender render (30-90 sec for preview)
   - **DONE:** Complete with video output

### Expected Result
- Progress reaches 100%
- Status changes to "DONE"
- Output video path appears (stored in MinIO)
- Option to download or re-render

---

## TEST 5: API Testing (curl commands)

### Setup - Get Authentication Token

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "curl-test@example.com",
    "password": "TestPassword123",
    "full_name": "Curl Test User"
  }'

# 2. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "curl-test@example.com",
    "password": "TestPassword123"
  }'

# Copy the "access_token" from response
export TOKEN="<paste_token_here>"
```

### Test Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

#### Get Current User
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
# Expected: User info (id, email, full_name, etc.)
```

#### List Projects
```bash
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN"
# Expected: Array of projects
```

#### Get Project Details
```bash
curl http://localhost:8000/api/projects/1 \
  -H "Authorization: Bearer $TOKEN"
# Expected: Project with status, created_at, render_jobs, etc.
```

#### Create Project
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "API Test Project",
    "description": "Testing via curl",
    "prompt": "Create a 3D rendered scene of a lighthouse on rocky cliffs with ocean waves"
  }'
# Expected: Project created with id
```

#### Start Render
```bash
PROJECT_ID=1
curl -X POST http://localhost:8000/api/renders/$PROJECT_ID/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"render_mode": "preview"}'
# Expected: RenderJob with status QUEUED and task_id
```

#### Get Render Status
```bash
RENDER_ID=1
curl http://localhost:8000/api/renders/$RENDER_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: RenderJob with updated progress and status
```

---

## TEST 6: Celery Worker & Background Tasks

### Step 6.1 - Watch Worker Logs
```bash
docker logs maritime-worker -f
```

### Step 6.2 - Expected Log Pattern
When you start a render, worker logs should show:

```
[2026-07-12 12:23:45,123: INFO/MainProcess] Task planning_task[123e4567-e89b-12d3-a456-426614174000] received
[2026-07-12 12:23:50,456: INFO/PoolWorker-1] Planning started for project ID 1
[2026-07-12 12:24:15,789: INFO/PoolWorker-1] Planning complete: 5 scenes, 2.3 tokens
[2026-07-12 12:24:16,012: INFO/PoolWorker-1] Storyboarding started
[2026-07-12 12:24:45,678: INFO/PoolWorker-1] Task complete: render_job_id=1, status=DONE
```

### Step 6.3 - Monitor Task Queue
```bash
# Connect to Redis and check queue
docker exec maritime-redis redis-cli
> LRANGE celery 0 -1
> HGETALL celery-task-meta-*
```

---

## TEST 7: Database Verification

### Step 7.1 - Connect to PostgreSQL
```bash
# Using psql (if installed)
psql -U maritime_user -h localhost -d maritime_studio

# Inside psql, run:
\dt                              # List tables
SELECT * FROM users;             # Check users
SELECT * FROM projects;          # Check projects
SELECT * FROM render_jobs;       # Check render jobs
SELECT * FROM scenes;            # Check scenes
SELECT COUNT(*) FROM usage_logs; # Check usage tracking
```

### Step 7.2 - Expected Tables
- ✅ `users` - User accounts
- ✅ `projects` - Project metadata
- ✅ `render_jobs` - Render task status
- ✅ `scenes` - Individual scenes per render
- ✅ `assets` - Asset library
- ✅ `usage_logs` - Cost tracking
- ✅ `notification_hooks` - Webhook destinations
- ✅ `subscriptions` - User subscriptions (MVP: unused)

---

## TEST 8: Object Storage (MinIO)

### Step 8.1 - Access MinIO UI
1. Open browser to `http://localhost:9001`
2. Login with:
   - **Username:** `minioadmin`
   - **Password:** `minioadmin`

### Step 8.2 - Verify Buckets
- Should see `maritime-studio` bucket
- After render completes, check for:
  - `/renders/{render_job_id}/` folder
  - `output.mp4` - Final video
  - `audio.wav` - Generated audio
  - Scene images and metadata

---

## TEST 9: Cost Control & Monitoring

### Step 9.1 - Check Cost Tracking
```bash
# After completing a render, check usage logs:
curl http://localhost:8000/api/projects/1/usage \
  -H "Authorization: Bearer $TOKEN"

# Expected response:
{
  "project_id": 1,
  "total_gpt_tokens": 1500,
  "total_tts_chars": 2400,
  "total_render_minutes": 2,
  "estimated_cost_usd": 0.15,
  "usage_logs": [
    {
      "usage_type": "gpt_tokens",
      "quantity": 1500,
      "cost_usd": 0.075
    },
    {
      "usage_type": "tts_chars",
      "quantity": 2400,
      "cost_usd": 0.06
    },
    {
      "usage_type": "render_minutes",
      "quantity": 2,
      "cost_usd": 0.015
    }
  ]
}
```

### Step 9.2 - Test Cost Threshold
```bash
# Set project cost threshold
curl -X PATCH http://localhost:8000/api/projects/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"cost_threshold": 0.10}'

# If next render would exceed threshold, should receive warning
```

---

## TEST 10: Asset Library

### Step 10.1 - Upload Asset
```bash
# Create a test blend file or use existing
curl -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer $TOKEN" \
  -F "name=Test Sailboat" \
  -F "category=vehicles" \
  -F "tags=maritime,sailboat" \
  -F "file_format=blend" \
  -F "file=@path/to/file.blend"
```

### Step 10.2 - Search Assets
```bash
# Search by category
curl "http://localhost:8000/api/assets?category=vehicles" \
  -H "Authorization: Bearer $TOKEN"

# Search by tags
curl "http://localhost:8000/api/assets?tags=maritime" \
  -H "Authorization: Bearer $TOKEN"
```

---

## TROUBLESHOOTING

### Issue: Frontend can't connect to API
**Solution:**
```bash
# Check if API is running
curl http://localhost:8000/health
# If no response, check logs:
docker logs maritime-api --tail 50
```

### Issue: Render job stuck in QUEUED
**Solution:**
```bash
# Check worker is running
docker ps | grep maritime-worker
# Check worker logs for errors
docker logs maritime-worker --tail 50
# Verify Redis connection
docker logs maritime-worker | grep "Connected to redis"
```

### Issue: Database connection errors
**Solution:**
```bash
# Check PostgreSQL is healthy
docker logs maritime-postgres --tail 20
# Verify database exists
docker exec maritime-postgres psql -U maritime_user -l
# Check database permissions
docker exec maritime-postgres psql -U maritime_user -d maritime_studio -c "SELECT version();"
```

### Issue: GPT-4 not planning (no OpenAI key)
**Solution:**
- This is expected in test environment
- Set `OPENAI_API_KEY` in `.env.production` for production
- Dummy task will return mock data for testing

### Issue: Blender render fails
**Solution:**
```bash
# Check Blender is installed in worker
docker exec maritime-worker which blender
# Check render output
docker exec maritime-worker ls -la /render_output/
```

---

## PERFORMANCE BASELINE

### Expected Timings

| Operation | Duration | Notes |
|-----------|----------|-------|
| User Registration | <100ms | Database write |
| User Login | <200ms | JWT generation |
| Create Project | <50ms | Database write |
| Start Render (Preview) | <500ms | Task queued |
| AI Planning (GPT-4) | 10-30s | Network dependent |
| TTS Generation (2 scenes) | 5-15s | OpenAI API |
| Scene Rendering (Blender) | 30-90s | CPU dependent |
| Video Composition (FFmpeg) | 10-30s | File I/O intensive |
| **Total Preview Render** | **~1-3 min** | End-to-end |
| **Total Full Render** | **~5-10 min** | 128 samples |

---

## SUCCESS CRITERIA

All tests pass when:
- ✅ Frontend loads at localhost:5173
- ✅ Can register and login
- ✅ Can create projects
- ✅ Can start render jobs
- ✅ Render job completes successfully
- ✅ All API endpoints respond correctly
- ✅ Database contains all required tables
- ✅ Celery worker processes tasks
- ✅ MinIO stores output videos
- ✅ Cost tracking is accurate

**System is PRODUCTION READY when all tests pass!**

---

## NEXT STEPS

1. **Run through all 10 tests**
2. **Document any errors encountered**
3. **Verify performance baseline**
4. **Test with production environment variables**
5. **Deploy to Kubernetes (see DEPLOYMENT_RUNBOOK.md)**
