# API Contracts - Phase 1: Auth Endpoints

## Overview

Phase 1 implements user authentication with JWT tokens. All endpoints are unauthenticated except `/api/auth/me`.

**Base URL:** `http://localhost:8000`

**Content-Type:** `application/json`

## Endpoints

### POST /api/auth/register

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123",
  "full_name": "John Doe"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2026-07-12T16:30:00"
}
```

**Errors:**
- `409 Conflict` — Email already registered
- `422 Unprocessable Entity` — Invalid email or missing required fields

---

### POST /api/auth/login

Login and receive JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized` — Invalid email or password
- `403 Forbidden` — User account is inactive
- `422 Unprocessable Entity` — Missing required fields

---

### GET /api/auth/me

Get current authenticated user.

**Request Header:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2026-07-12T16:30:00"
}
```

**Errors:**
- `401 Unauthorized` — Missing or invalid token
- `404 Not Found` — User deleted after token issued (edge case)

---

## Common Headers

**For authenticated requests:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Token Details

**JWT Structure:**
- **Algorithm:** HS256
- **Secret:** From `JWT_SECRET_KEY` env var
- **Expiration:** Configurable via `JWT_EXPIRATION_HOURS` (default 24 hours)

**Payload:**
```json
{
  "sub": "1",           // user_id as string
  "email": "user@example.com",
  "exp": 1689188000    // Unix timestamp
}
```

## Error Response Format

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

Some endpoints may include `error_code`:

```json
{
  "detail": "Invalid credentials",
  "error_code": "auth_001"
}
```

## Examples

### Complete Registration + Login Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "MySecurePass123!",
    "full_name": "New User"
  }'

# Response:
# {
#   "id": 2,
#   "email": "newuser@example.com",
#   "full_name": "New User",
#   "is_active": true,
#   "created_at": "2026-07-12T17:00:00"
# }

# 2. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "MySecurePass123!"
  }'

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiZW1haWwiOiJuZXd1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjg5MzA5NDAwfQ.abcdef...",
#   "token_type": "bearer"
# }

# 3. Get current user (using token from step 2)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiZW1haWwiOiJuZXd1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjg5MzA5NDAwfQ.abcdef..."

# Response:
# {
#   "id": 2,
#   "email": "newuser@example.com",
#   "full_name": "New User",
#   "is_active": true,
#   "created_at": "2026-07-12T17:00:00"
# }
```

## Future Phases

Phases 2+ will add:
- `POST /api/projects` — Create project (requires auth)
- `GET /api/projects` — List projects (requires auth)
- `GET /api/projects/{id}` — Get project details (requires auth + ownership check)
- `POST /api/renders/{id}/start` — Start render job (requires auth + ownership)
- `GET /api/assets?category=...&tags=...` — Search assets (public or requires auth)
- And more...

Token will be required for all project/render operations to enforce ownership and rate limiting.

## Security Notes

- Passwords are hashed with bcrypt (never stored in plain text)
- Tokens are JWT HS256-signed
- All credentials should be sent over HTTPS in production
- Tokens expire after 24 hours (configurable)
- Failed login attempts are not rate-limited in MVP (Phase 9 TODO)
