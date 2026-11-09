# Tutor AI Robot — Backend Feature Documentation

## Overview

This backend powers a Raspberry Pi camera monitoring system that analyzes student focus and homework activity using AI vision models. It provides a REST API consumed by:

1. **Raspberry Pi devices** — submit camera frames for AI analysis
2. **Admin frontend** — manage devices, AI providers, prompts, and view analytics

---

## Architecture

```
cmd/server/main.go          — entry point, wires dependencies
internal/
  domain/                   — interfaces (repository contracts, entities)
  application/              — use cases (business logic)
  infrastructure/           — postgres, redis, AI client implementations
  interfaces/http/          — Fiber v3 HTTP handlers, middleware, router
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| HTTP server | Go + Fiber v3 |
| Database | PostgreSQL (pgxpool) |
| Cache / Auth | Redis (JWT blacklist, rate limiting) |
| Auth | JWT (access + refresh tokens) |
| AI providers | OpenAI-compatible REST (OpenAI, Claude, Gemini, etc.) |
| Migrations | golang-migrate |
| Deployment | Docker + docker-compose |

---

## Authentication

### Admin Authentication (JWT)

Admins authenticate via username/password. The system issues short-lived access tokens and long-lived refresh tokens.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/login` | POST | None (IP rate-limited) | Returns `access_token` + `refresh_token` |
| `/api/v1/auth/refresh` | POST | None | Exchange refresh token for new access token |
| `/api/v1/auth/logout` | POST | AdminAuth | Blacklists current access token in Redis |

**Login request:**
```json
{ "username": "admin", "password": "secret" }
```

**Login response:**
```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 900
  }
}
```

### Device Authentication (Bearer token)

Each Raspberry Pi device is issued a unique bearer token by the admin. The token is sent in the `Authorization: Bearer <token>` header on every analysis request.

- Tokens are hashed (bcrypt) before storage; raw value is shown once at creation
- Tokens can be revoked by the admin (device cannot submit until a new token is issued)

---

## AI Provider Management

Admins configure one or more AI providers. The system proxies homework analysis requests through whichever provider is marked as default.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/providers` | GET | List all providers |
| `/api/v1/providers` | POST | Create provider |
| `/api/v1/providers/:id` | GET | Get provider detail |
| `/api/v1/providers/:id` | PUT | Update provider (name, URL, model, API key, timeout, is_default) |
| `/api/v1/providers/:id` | DELETE | Delete provider |
| `/api/v1/providers/:id/test` | POST | Test connectivity + latency |

### Provider fields

```json
{
  "id": "uuid",
  "name": "OpenAI GPT-4o",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "api_key": "sk-••••••",
  "timeout_sec": 30,
  "is_default": true,
  "is_active": true,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

- **`api_key`** is always returned masked (e.g. `sk-...abc`). Submit a new value to update it.
- **`is_default`** — only one provider is default; setting a new default clears the previous one.
- **`base_url`** — any OpenAI-compatible endpoint (Anthropic, Gemini, Ollama, etc.)

### Set default provider

Send `PUT /api/v1/providers/:id` with `{ "is_default": true }`.

### Test connection

`POST /api/v1/providers/:id/test` — sends a minimal probe request and returns:
```json
{ "data": { "success": true, "latency_ms": 342, "error": null } }
```

---

## Prompt Management

System prompts sent to the AI model are managed as versioned records. The admin can create, edit, and delete prompts. The active prompt is selected automatically (most recent active record).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/prompts` | GET | List all prompts |
| `/api/v1/prompts` | POST | Create prompt |
| `/api/v1/prompts/:id` | PUT | Update prompt |
| `/api/v1/prompts/:id` | DELETE | Delete prompt |

### Prompt fields

```json
{
  "id": "uuid",
  "name": "Homework Detector v2",
  "content": "Analyze the image and return JSON: ...",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

## Device Management

Raspberry Pi devices are registered by the admin and identified by bearer tokens.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/devices` | GET | List all devices |
| `/api/v1/devices` | POST | Register new device, returns raw token (shown once) |
| `/api/v1/devices/:id/revoke` | POST | Revoke device token |

### Create device response

```json
{
  "data": {
    "id": "uuid",
    "name": "RPi Camera - Room A101",
    "token": "raw-bearer-token-shown-once",
    "is_active": true,
    "created_at": "2026-01-01T00:00:00Z",
    "note": "Store this token securely — it will not be shown again."
  }
}
```

### Device list item

```json
{
  "id": "uuid",
  "name": "RPi Camera - Room A101",
  "last_used_at": "2026-05-14T10:30:00Z",
  "last_ip": "192.168.1.42",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00Z"
}
```

### Configuring the Raspberry Pi

Set the token in the device's `.env` file:
```
DEVICE_TOKEN=<raw-token>
BACKEND_URL=https://your-backend.example.com
```

---

## Analysis Pipeline (Device → Backend → AI)

### Submit analysis frame

The Pi camera sends a JPEG frame to the backend after local pre-processing detects potential homework activity.

```
POST /api/v1/device/analyze
Authorization: Bearer <device-token>
Content-Type: application/json
```

**Request body:**
```json
{
  "image_b64": "<base64-encoded-JPEG>",
  "student_id": "optional-student-identifier",
  "activity": "writing_notes",
  "focus_score": 82,
  "hw_visible": true,
  "image_width": 1920,
  "image_height": 1080,
  "image_size_kb": 145
}
```

**Two-stage AI pipeline:**

| Stage | Purpose | Latency tracked |
|-------|---------|----------------|
| Stage 1 | Homework detection (doing_hw, subject, grade, hw_type, progress) | `s1_latency_ms` |
| Stage 2 | Extended analysis (confidence, hints) | `s2_latency_ms` |

**Analysis result fields:**
```json
{
  "doing_hw": true,
  "subject": "math",
  "grade": "10",
  "hw_type": "exercises",
  "progress": 65,
  "hints": "Try factoring the quadratic before applying the formula.",
  "confidence": 0.87
}
```

Supported subjects: `math`, `vietnamese`, `english`, `physics`, `chemistry`, `biology`, `history`, `geography`, `other`

Supported hw_type: `exercises`, `theory`, `reading`

---

## Analysis History

Admins can query the full history of AI analyses with filtering and cursor-based pagination.

```
GET /api/v1/analyses?from=2026-05-01&to=2026-05-14&subject=math&doing_hw=true&device_id=uuid&limit=20&cursor=<timestamp>
```

### Query parameters

| Param | Type | Description |
|-------|------|-------------|
| `from` | ISO date | Filter `created_at >= from` |
| `to` | ISO date | Filter `created_at <= to` |
| `subject` | string | Filter by subject |
| `device_id` | UUID | Filter by device |
| `doing_hw` | bool | Filter by homework status |
| `limit` | int | Page size (default 20, max 100) |
| `cursor` | string | Opaque cursor for next page |

### Response

```json
{
  "data": [
    {
      "id": "uuid",
      "device_id": "uuid",
      "device_name": "RPi Camera - Room A101",
      "student_id": "student-42",
      "activity": "writing_notes",
      "focus_score": 82,
      "hw_visible": true,
      "doing_hw": true,
      "subject": "math",
      "grade": "10",
      "hw_type": "exercises",
      "progress": 65,
      "hints": "Try factoring...",
      "confidence": 0.87,
      "provider_id": "uuid",
      "provider_name": "OpenAI GPT-4o",
      "latency_ms": 520,
      "image_width": 1920,
      "image_height": 1080,
      "image_size_kb": 145,
      "created_at": "2026-05-14T10:30:00Z"
    }
  ],
  "meta": {
    "cursor": "2026-05-14T10:29:00Z",
    "has_more": true
  }
}
```

---

## Statistics API

All stats endpoints require AdminAuth.

### Overview stats

```
GET /api/v1/stats/overview
```

```json
{
  "data": {
    "total_analyses": 15420,
    "today_total": 342,
    "today_homework": 187,
    "homework_rate": 0.547,
    "avg_latency_ms": 485,
    "active_providers": 2,
    "active_devices": 5,
    "top_subject": "math"
  }
}
```

### Latency trend (hourly, last 24h)

```
GET /api/v1/stats/latency
```

```json
{
  "data": [
    { "hour": "2026-05-14T09:00:00Z", "avg_ms": 412, "count": 38 },
    { "hour": "2026-05-14T10:00:00Z", "avg_ms": 531, "count": 54 }
  ]
}
```

### Subject distribution (last 30 days)

```
GET /api/v1/stats/subjects
```

```json
{
  "data": [
    { "subject": "math", "count": 1420 },
    { "subject": "vietnamese", "count": 980 }
  ]
}
```

---

## API Response Envelope

All responses use a consistent envelope:

```json
{ "data": <T> }                          // single resource or array
{ "data": <T[]>, "meta": { ... } }       // paginated list
{ "error": "message" }                   // error
```

HTTP status codes:
- `200` — success
- `201` — resource created
- `400` — validation error
- `401` — unauthenticated
- `403` — forbidden (e.g. device token revoked)
- `404` — not found
- `429` — rate limited
- `500` — internal server error

---

## Rate Limiting

Rate limits are enforced per-IP (auth endpoints) and per-device-token (analyze endpoint), backed by Redis sliding window counters.

| Group | Default RPM |
|-------|------------|
| Auth (login) | 10 req/min |
| Admin API | 300 req/min |
| Device analyze | 60 req/min |

Limits are configurable via environment variables:
```
RATE_LIMIT_AUTH_RPM=10
RATE_LIMIT_ADMIN_RPM=300
RATE_LIMIT_DEVICE_RPM=60
```

---

## Environment Configuration

Key environment variables (see `configs/config.go` for full list):

```env
# Server
PORT=8080
ADMIN_FRONTEND_URL=http://localhost:5173

# Database
DATABASE_URL=postgres://user:pass@localhost:5432/tutor_airobot

# Redis
REDIS_URL=redis://localhost:6379

# Auth
JWT_SECRET=change-me-in-production
JWT_ACCESS_TTL=15m
JWT_REFRESH_TTL=7d
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme

# Rate limiting
RATE_LIMIT_AUTH_RPM=10
RATE_LIMIT_ADMIN_RPM=300
RATE_LIMIT_DEVICE_RPM=60
```

---

## Database Schema (key tables)

| Table | Purpose |
|-------|---------|
| `providers` | AI provider config (URL, model, masked API key) |
| `prompts` | System prompt versions |
| `devices` | Registered Raspberry Pi devices (token hash, last IP, last used) |
| `analyses` | Full history of AI analysis results per frame |

Migrations are in `migrations/` and applied automatically on startup.

---

## Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migrations manually
docker-compose exec backend ./server migrate
```

The `docker-compose.yml` starts: PostgreSQL, Redis, and the Go backend.
