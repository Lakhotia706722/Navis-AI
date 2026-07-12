# Local Development Setup

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local backend testing)
- Node.js 18+ (for frontend)
- Git

## Quick Start

### 1. Clone & Configure

```bash
git clone <repo>
cd maritime-studio
cp .env.example .env
```

Update `.env` with your values:
- `OPENAI_API_KEY` — your OpenAI API key (GPT-4 + TTS)
- Other values can stay as defaults for local dev

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** (port 5432)
- **Redis** (port 6379)
- **MinIO** (port 9000, admin console 9001)
- **FastAPI** (port 8000)
- **Celery Worker** (watches queue)

### 3. Initialize Database

```bash
# Inside the API container, run migrations
docker-compose exec api alembic upgrade head
```

### 4. Start Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` and proxies `/api/*` to the backend.

## Health Checks

**Backend:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

**MinIO Admin Console:**
```
http://localhost:9001
Username: minioadmin
Password: minioadmin
```

**Redis:**
```bash
docker-compose exec redis redis-cli ping
# Expected: PONG
```

## Logs

```bash
# Follow backend logs
docker-compose logs -f api

# Follow worker logs
docker-compose logs -f worker

# Follow all
docker-compose logs -f
```

## Stopping

```bash
docker-compose down
# Remove volumes too (wipes data):
docker-compose down -v
```

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://maritime_user:maritime_pass@postgres:5432/maritime_studio` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker |
| `S3_ENDPOINT_URL` | `http://minio:9000` | Object storage (MinIO) |
| `OPENAI_API_KEY` | Required | GPT-4 API key for planning |
| `OPENAI_TTS_MODEL` | `tts-1-hd` | OpenAI TTS model |
| `BLENDER_RENDER_BACKEND` | `CPU` | Rendering backend (CPU or CUDA) |
| `PREVIEW_RENDER_SAMPLES` | `16` | Fast preview render samples |
| `FULL_RENDER_SAMPLES` | `128` | Production render samples |

## Future: GPU Rendering

When CUDA/GPU is available:

1. Update `.env`: `BLENDER_RENDER_BACKEND=CUDA`
2. Rebuild worker with nvidia/cuda base image:
   ```bash
   # Edit Dockerfile.worker to inherit from nvidia/cuda
   docker-compose build --no-cache worker
   docker-compose up -d
   ```

## Troubleshooting

**Container fails to start:**
```bash
docker-compose logs <service>
# e.g., docker-compose logs api
```

**Port already in use:**
```bash
# Change port in docker-compose.yml or kill the process
# Windows: Get-NetTCPConnection -LocalPort 8000 | Stop-Process
```

**Can't connect to database:**
```bash
# Wait for postgres healthcheck
docker-compose ps
# Status should show "healthy" for postgres
```
