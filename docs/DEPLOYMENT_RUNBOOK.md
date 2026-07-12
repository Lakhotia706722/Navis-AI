# Deployment Runbook: Yetrix Maritime AI Studio

**Version:** 1.0  
**Last Updated:** July 12, 2026  
**Status:** Production-Ready MVP

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment (Kubernetes)](#production-deployment-kubernetes)
5. [Database Management](#database-management)
6. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
7. [Scaling & Performance](#scaling--performance)
8. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

- Docker & Docker Compose (v20.10+)
- kubectl (v1.24+) for Kubernetes deployments
- Git (v2.30+)
- Python 3.11+ (for CLI scripts)
- PostgreSQL client tools (psql)
- Redis CLI (optional, for queue inspection)

### Required Credentials

- OpenAI API key
- AWS S3 or MinIO credentials
- GitHub/GitLab deploy token (if using private registries)
- SSL certificate (for HTTPS)

### Network & Infrastructure

- Kubernetes cluster (EKS, AKS, GKE, or self-hosted)
- RDS PostgreSQL instance (or self-managed Postgres)
- ElastiCache Redis instance (or self-managed Redis)
- AWS S3 bucket (or MinIO deployment)
- Internet access to OpenAI API

---

## Local Development

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/maritime-studio.git
cd maritime-studio

# 2. Copy configuration
cp .env.example .env

# 3. Add secrets (do NOT commit)
# Edit .env with your OpenAI key, etc.

# 4. Start services
docker-compose up -d

# 5. Wait for services to be ready (30 seconds)
sleep 30

# 6. Verify health
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 7. Run tests
docker-compose exec api pytest backend/tests/ -v

# 8. Start frontend (new terminal)
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
```

### Development Workflow

```bash
# Backend changes (auto-reload via Docker)
docker-compose restart api

# Frontend changes (auto-reload via Vite)
# Just save files, browser refreshes automatically

# Run specific tests
docker-compose exec api pytest backend/tests/test_auth.py -v

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Database access
docker-compose exec postgres psql -U maritime_user -d maritime_studio

# Cleanup (stop all services)
docker-compose down
# Or with volumes
docker-compose down -v
```

---

## Staging Deployment

### Staging Environment Setup

**Use the same docker-compose.yml but with production env vars:**

```bash
# 1. Deploy to staging machine/VM

# 2. Copy staging env file
cp .env.staging .env

# 3. Edit .env with staging-specific values:
# - DATABASE_URL=postgresql://user:pass@staging-rds:5432/maritime_staging
# - REDIS_URL=redis://staging-redis:6379/0
# - MINIO_ENDPOINT=s3.staging.amazonaws.com
# - OPENAI_API_KEY=sk-... (staging key)

# 4. Build images (if needed)
docker-compose build

# 5. Start services
docker-compose up -d

# 6. Verify all services
docker-compose ps

# 7. Run migrations
docker-compose exec api alembic upgrade head

# 8. Create admin user
docker-compose exec api python -c "
from backend.database import SessionLocal
from backend.models import User
from backend.security import hash_password

db = SessionLocal()
admin = User(
    email='admin@staging.example.com',
    hashed_password=hash_password('CHANGE_ME'),
    is_active=True
)
db.add(admin)
db.commit()
print('Admin user created')
"

# 9. Test end-to-end
curl -X POST http://staging-domain:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@staging.example.com","password":"CHANGE_ME"}'
```

---

## Production Deployment (Kubernetes)

### 1. Cluster Preparation

```bash
# 1. Create cluster (AWS EKS example)
eksctl create cluster \
  --name maritime-studio \
  --version 1.28 \
  --region us-east-1 \
  --nodes 3 \
  --node-type t3.xlarge

# 2. Get kubeconfig
aws eks update-kubeconfig \
  --name maritime-studio \
  --region us-east-1

# 3. Verify connectivity
kubectl get nodes
# Expected: 3 nodes in Ready state

# 4. Install Ingress Controller (if needed)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

### 2. Database & Cache Setup

```bash
# 1. Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier maritime-studio-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --master-username maritime_user \
  --master-user-password "CHANGE_ME_STRONG_PASSWORD" \
  --allocated-storage 100 \
  --multi-az

# 2. Create ElastiCache Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id maritime-studio-redis \
  --cache-node-type cache.t3.small \
  --engine redis \
  --num-cache-nodes 1 \
  --engine-version 7.0

# 3. Get endpoints
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier maritime-studio-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id maritime-studio-redis \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text)

echo "RDS: $RDS_ENDPOINT:5432"
echo "Redis: $REDIS_ENDPOINT:6379"
```

### 3. Container Registry

```bash
# 1. Create ECR repository
aws ecr create-repository \
  --repository-name maritime-studio/backend \
  --region us-east-1

aws ecr create-repository \
  --repository-name maritime-studio/worker \
  --region us-east-1

# 2. Build and push images
REGISTRY="YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com"

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $REGISTRY

# Build backend
docker build -f Dockerfile.backend \
  -t $REGISTRY/maritime-studio/backend:latest \
  -t $REGISTRY/maritime-studio/backend:v1.0 .

docker push $REGISTRY/maritime-studio/backend:latest

# Build worker
docker build -f Dockerfile.worker \
  -t $REGISTRY/maritime-studio/worker:latest \
  -t $REGISTRY/maritime-studio/worker:v1.0 .

docker push $REGISTRY/maritime-studio/worker:latest
```

### 4. Kubernetes Deployment

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create secrets (IMPORTANT: Use secure secrets management)
# Option A: kubectl (for testing only, not production!)
kubectl create secret generic maritime-studio-secrets \
  --from-literal=DATABASE_URL="postgresql://..." \
  --from-literal=REDIS_URL="redis://..." \
  --from-literal=OPENAI_API_KEY="sk-..." \
  -n maritime-studio

# Option B: AWS Secrets Manager (recommended for production)
aws secretsmanager create-secret \
  --name maritime-studio/db \
  --secret-string "postgresql://user:pass@rds:5432/maritime"

# 3. Deploy ConfigMap & Secrets
kubectl apply -f k8s/secrets.yaml

# 4. Deploy API
kubectl apply -f k8s/api-deployment.yaml

# 5. Deploy Worker
kubectl apply -f k8s/worker-deployment.yaml

# 6. Verify rollout
kubectl rollout status deployment/maritime-api -n maritime-studio
kubectl rollout status deployment/maritime-worker -n maritime-studio

# 7. Check pod status
kubectl get pods -n maritime-studio

# 8. View API logs
kubectl logs -f -l app=maritime-studio,component=api -n maritime-studio
```

### 5. Database Migration

```bash
# 1. Port-forward to API pod
kubectl port-forward -n maritime-studio \
  svc/maritime-api 8000:80 &

# 2. Run migrations
curl -X POST http://localhost:8000/api/admin/migrate \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Or directly on container:
kubectl exec -it -n maritime-studio \
  deployment/maritime-api -- \
  alembic upgrade head
```

### 6. Ingress (HTTPS)

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: maritime-studio
  namespace: maritime-studio
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.your-domain.com
    secretName: maritime-tls-cert
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: maritime-api
            port:
              number: 80
```

```bash
# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Get HTTPS URL
kubectl get ingress -n maritime-studio
```

---

## Database Management

### Backups

```bash
# 1. RDS automatic backups (enable in AWS Console)
# - Retention: 30 days
# - Backup window: 03:00-04:00 UTC

# 2. Manual backup
aws rds create-db-snapshot \
  --db-instance-identifier maritime-studio-db \
  --db-snapshot-identifier maritime-studio-backup-$(date +%Y%m%d)

# 3. Verify backup
aws rds describe-db-snapshots \
  --db-snapshot-identifier maritime-studio-backup-20260712
```

### Restoration

```bash
# 1. Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier maritime-studio-db-restored \
  --db-snapshot-identifier maritime-studio-backup-20260712

# 2. Update app to point to new DB
# (Update DATABASE_URL env var and redeploy)
```

### Schema Migrations

```bash
# 1. In development
alembic upgrade head

# 2. In Kubernetes
kubectl exec -n maritime-studio \
  deployment/maritime-api -- \
  alembic upgrade head

# 3. Verify
alembic current
```

---

## Monitoring & Troubleshooting

### Health Checks

```bash
# 1. API health
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 2. Database connectivity
kubectl exec -n maritime-studio deployment/maritime-api -- \
  python -c "from backend.database import engine; engine.execute('SELECT 1')"

# 3. Redis connectivity
kubectl exec -n maritime-studio deployment/maritime-api -- \
  redis-cli -h redis ping
# Expected: PONG

# 4. S3/MinIO connectivity
kubectl exec -n maritime-studio deployment/maritime-api -- \
  python -c "from backend.storage import s3_client; s3_client.head_bucket(Bucket='maritime-studio')"
```

### Viewing Logs

```bash
# API logs
kubectl logs -f deployment/maritime-api -n maritime-studio

# Worker logs
kubectl logs -f deployment/maritime-worker -n maritime-studio

# All logs with label
kubectl logs -f -l app=maritime-studio -n maritime-studio --all-containers=true

# Logs from specific container
kubectl logs -f deployment/maritime-api -n maritime-studio -c api
```

### Debugging

```bash
# 1. Describe pod (events, conditions)
kubectl describe pod -n maritime-studio POD_NAME

# 2. Shell into pod
kubectl exec -it -n maritime-studio deployment/maritime-api -- /bin/bash

# 3. Check resource usage
kubectl top pods -n maritime-studio

# 4. Check events
kubectl get events -n maritime-studio --sort-by='.lastTimestamp'

# 5. Check persistent volumes (if applicable)
kubectl get pvc -n maritime-studio
```

---

## Scaling & Performance

### Horizontal Scaling

```bash
# 1. Scale API replicas
kubectl scale deployment maritime-api \
  --replicas 5 \
  -n maritime-studio

# 2. Scale worker replicas
kubectl scale deployment maritime-worker \
  --replicas 3 \
  -n maritime-studio

# 3. Verify
kubectl get deployment -n maritime-studio
```

### Resource Limits

```yaml
# In k8s/api-deployment.yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### HorizontalPodAutoscaler (Optional)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: maritime-api-hpa
  namespace: maritime-studio
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: maritime-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Rollback Procedures

### Rollback to Previous Version

```bash
# 1. Check rollout history
kubectl rollout history deployment/maritime-api -n maritime-studio

# 2. Rollback to previous revision
kubectl rollout undo deployment/maritime-api -n maritime-studio

# 3. Rollback to specific revision
kubectl rollout undo deployment/maritime-api \
  --to-revision=2 \
  -n maritime-studio

# 4. Verify rollback
kubectl rollout status deployment/maritime-api -n maritime-studio
```

### Rollback Database Schema

```bash
# 1. Check Alembic history
alembic history

# 2. Downgrade to previous migration
alembic downgrade -1

# 3. Or downgrade to specific revision
alembic downgrade 001_initial_schema
```

---

## Disaster Recovery

### Complete Cluster Recovery

```bash
# 1. Backup everything
kubectl get all -n maritime-studio -o yaml > backup-all.yaml

# 2. If cluster is lost, restore from backup
kubectl apply -f backup-all.yaml

# 3. Restore database from RDS snapshot
# (See Database Management section)
```

---

## Security Checklist

- [ ] All secrets stored in AWS Secrets Manager (not in config)
- [ ] HTTPS enabled (cert from Let's Encrypt via cert-manager)
- [ ] Network policies restrict pod-to-pod communication
- [ ] RBAC configured (service accounts with minimal permissions)
- [ ] Container images scanned for vulnerabilities
- [ ] Regular database backups enabled (30-day retention)
- [ ] Logs centralized to CloudWatch/ELK
- [ ] Rate limiting enabled on API
- [ ] WAF enabled on Ingress
- [ ] VPC security groups configured properly

---

## Post-Deployment Verification

```bash
# 1. Health check API
curl https://api.your-domain.com/health

# 2. Test authentication
curl -X POST https://api.your-domain.com/api/auth/login \
  -d '{"email":"test@example.com","password":"test"}'

# 3. Test render endpoint
curl -X POST https://api.your-domain.com/api/projects \
  -H "Authorization: Bearer $TOKEN"

# 4. Monitor metrics
kubectl top pods -n maritime-studio

# 5. Check logs for errors
kubectl logs -f deployment/maritime-api -n maritime-studio | grep ERROR
```

---

## Support & Escalation

**For issues:**
1. Check logs: `kubectl logs -f deployment/maritime-api`
2. Check events: `kubectl get events -n maritime-studio`
3. Check resources: `kubectl top pods -n maritime-studio`
4. Check RDS: AWS Console → RDS → maritime-studio-db
5. Contact DevOps team with pod names and timestamps

---

**This runbook is maintained by the DevOps team. Last reviewed: 2026-07-12**

