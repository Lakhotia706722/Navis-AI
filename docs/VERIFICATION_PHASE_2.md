# Phase 2 Verification Checklist

Use this to verify that Phase 2 is working correctly.

## Pre-Flight Checks

### Docker Services Running

```bash
docker-compose ps
```

**Expected:** All services show "healthy" or "running"
- postgres: healthy
- redis: healthy
- minio: healthy
- api: running
- worker: running

### Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"ok"}
```

### Redis Connection

```bash
docker-compose exec redis redis-cli ping
```

**Expected Response:** `PONG`

---

## Unit Tests (40 tests)

### Run Full Suite

```bash
docker-compose exec api pytest -v
```

**Expected:** 40 tests PASSED

### Run by Category

```bash
# Auth tests (16)
docker-compose exec api pytest backend/tests/test_auth.py -v
docker-compose exec api pytest backend/tests/test_security.py -v

# Project tests (10)
docker-compose exec api pytest backend/tests/test_projects.py -v

# Render tests (10)
docker-compose exec api pytest backend/tests/test_renders.py -v

# Storage tests (4)
docker-compose exec api pytest backend/tests/test_storage.py -v
```

---

## Manual Integration Test

### 1. Register & Login

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "secure123",
    "full_name": "Test User"
  }'

# Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "secure123"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

### 2. Create Project

```bash
PROJECT=$(curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Anchor Handling",
    "description": "Learn proper anchor techniques",
    "prompt": "Create a 2-minute video on anchor handling best practices in maritime operations"
  }')

PROJECT_ID=$(echo $PROJECT | jq -r '.id')
echo "Created project: $PROJECT_ID"
```

**Expected Response:**
- `id`: number
- `title`: "Anchor Handling"
- `status`: "queued"
- `user_id`: 1

### 3. List Projects

```bash
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:** Array with at least one project

### 4. Get Project Details

```bash
curl http://localhost:8000/api/projects/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.render_jobs'
```

**Expected:** `render_jobs` array (empty at first)

### 5. Start Render Job

```bash
RENDER=$(curl -X POST http://localhost:8000/api/renders/$PROJECT_ID/start?render_mode=preview \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

RENDER_ID=$(echo $RENDER | jq -r '.id')
echo "Started render: $RENDER_ID"
echo $RENDER | jq '.status, .progress_percent'
```

**Expected Response:**
- `id`: number
- `project_id`: matches $PROJECT_ID
- `status`: "queued"
- `progress_percent`: 0
- `render_mode`: "preview"
- `celery_task_id`: UUID string

### 6. Monitor Render Progress

```bash
# Watch status change from queued → planning → composing → rendering → assembling → done

for i in {1..30}; do
  RENDER_STATUS=$(curl -s http://localhost:8000/api/renders/$RENDER_ID \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status, .progress_percent')
  echo "[$i/30] $RENDER_STATUS"
  
  if [[ "$RENDER_STATUS" == *"done"* ]] || [[ "$RENDER_STATUS" == *"failed"* ]]; then
    echo "Render complete!"
    break
  fi
  
  sleep 1
done
```

**Expected Progression:**
- Status: queued (0%)
- Status: planning (10%)
- Status: composing (30%)
- Status: rendering (60%)
- Status: assembling (90%)
- Status: done (100%)

### 7. Check Final Render Job

```bash
curl http://localhost:8000/api/renders/$RENDER_ID \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected (if done):**
- `status`: "done"
- `progress_percent`: 100
- `output_video_path`: starts with "s3://maritime-studio/renders/"
- `started_at`: timestamp
- `completed_at`: timestamp

### 8. List Render Jobs for Project

```bash
curl http://localhost:8000/api/projects/$PROJECT_ID/renders \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:** Array with one render job

### 9. Cancel Render (Optional)

Start another render, then cancel it:

```bash
RENDER2=$(curl -X POST http://localhost:8000/api/renders/$PROJECT_ID/start?render_mode=full \
  -H "Authorization: Bearer $TOKEN")

RENDER2_ID=$(echo $RENDER2 | jq -r '.id')

# Cancel it
curl -X POST http://localhost:8000/api/renders/$RENDER2_ID/cancel \
  -H "Authorization: Bearer $TOKEN" | jq '.status, .error_message'
```

**Expected:**
- `status`: "failed"
- `error_message`: "Cancelled by user"

### 10. Update Project

```bash
curl -X PUT http://localhost:8000/api/projects/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated: Anchor Handling"
  }' | jq '.title'
```

**Expected:** "Updated: Anchor Handling"

### 11. Delete Project

```bash
curl -X DELETE http://localhost:8000/api/projects/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN"

# Should return 204 No Content (no response body)
```

Verify deletion:

```bash
curl http://localhost:8000/api/projects/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.detail'
```

**Expected:** "Project not found"

---

## Authorization Tests

### Test: Cannot Access Another User's Project

```bash
# Register user 1
USER1_TOKEN=$(curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user1@example.com", "password": "pass"}' \
  | jq -r '.id')

USER1_TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user1@example.com", "password": "pass"}' \
  | jq -r '.access_token')

# User 1 creates project
PROJECT=$(curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer $USER1_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "User1 Project", "prompt": "prompt"}' \
  | jq -r '.id')

# Register user 2
USER2_TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user2@example.com", "password": "pass"}' \
  | jq -r '.access_token')

# User 2 tries to access user 1's project
curl http://localhost:8000/api/projects/$PROJECT \
  -H "Authorization: Bearer $USER2_TOKEN" | jq '.detail'
```

**Expected:** "You do not have access to this project" or similar 403 error

---

## Worker Logs

```bash
docker-compose logs worker --tail 50
```

**Expected to see:**
```
Starting dummy planning task for render_job X
Render job X moved to PLANNING (10%)
Render job X moved to COMPOSING (30%)
Render job X moved to RENDERING (60%)
Render job X moved to ASSEMBLING (90%)
Render job X DONE (100%)
```

---

## Database Inspection

### Check Users Table

```bash
docker-compose exec postgres psql -U maritime_user -d maritime_studio -c "SELECT id, email FROM users LIMIT 5;"
```

### Check Projects

```bash
docker-compose exec postgres psql -U maritime_user -d maritime_studio -c "SELECT id, user_id, title, status FROM projects LIMIT 5;"
```

### Check Render Jobs

```bash
docker-compose exec postgres psql -U maritime_user -d maritime_studio -c "SELECT id, project_id, status, progress_percent, celery_task_id FROM render_jobs LIMIT 5;"
```

---

## Troubleshooting

### Tests Failing

```bash
# Run with verbose output
docker-compose exec api pytest -vvv backend/tests/test_projects.py::TestProjectRoutes::test_create_project_success

# Check for db issues
docker-compose logs -f postgres
```

### Worker Not Processing Tasks

```bash
# Check Celery connection
docker-compose logs -f worker | grep -i redis

# Verify Redis is running
docker-compose exec redis redis-cli PING

# Check for stuck tasks
docker-compose exec redis redis-cli KEYS "celery*"
```

### Projects Not Appearing

```bash
# Verify token is valid
TOKEN_PAYLOAD=$(echo $TOKEN | cut -d'.' -f2 | base64 -d)
echo $TOKEN_PAYLOAD | jq

# Check user_id matches
docker-compose exec postgres psql -U maritime_user -d maritime_studio -c "SELECT id, email FROM users WHERE email='test@example.com';"
```

---

## Summary

✅ Phase 2 is complete when:
- All 40 tests pass
- Manual integration test runs end-to-end (project created, render started, status updated to done)
- Worker logs show task progression through state machine
- Database contains projects and render_jobs with correct ownership
- Authorization prevents cross-user access
