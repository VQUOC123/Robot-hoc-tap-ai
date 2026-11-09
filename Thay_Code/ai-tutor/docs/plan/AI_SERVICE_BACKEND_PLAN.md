# Tutor Backend Service — Go + Fiber

**Stack:** Go 1.23 · Fiber v3 · PostgreSQL 16 · Redis 7 · Docker
**Repo:** `tutor-backend/` (project độc lập, không liên quan ai-tutor RPi5)
**Domain:** `https://api.tutor.your-domain.com`

---

## 1. Kiến trúc tổng quan

Áp dụng **Clean Architecture** (Uncle Bob) — dependency chỉ hướng vào trong:

```
Interfaces (HTTP)
    ↓ depends on
Application (Use Cases)
    ↓ depends on
Domain (Entities + Interfaces)
    ↑ implemented by
Infrastructure (DB, Redis, AI, Image)
```

- **Domain** không import gì ngoài stdlib
- **Application** chỉ import domain interfaces — không biết Fiber, Postgres, Redis tồn tại
- **Infrastructure** implement domain interfaces, không biết HTTP tồn tại
- **Interfaces/HTTP** chuyển HTTP request → use case → HTTP response

**Design Patterns sử dụng:**
| Pattern | Áp dụng tại |
|---|---|
| Repository | Data access abstraction (domain/repository) |
| Use Case / Interactor | Business logic đóng gói (application/) |
| Strategy | AIClient — mỗi provider là 1 strategy |
| Factory | Tạo AIClient từ Provider config (infrastructure/ai) |
| Middleware Chain | Auth, rate limit, CORS, logger (interfaces/http/middleware) |
| Constructor Injection | Toàn bộ dependencies truyền qua constructor |
| Option Pattern | Server config, AI client config |
| Cursor Pagination | Hiệu năng query lịch sử lớn |

---

## 2. Cấu trúc thư mục

```
tutor-backend/
│
├── cmd/
│   └── server/
│       └── main.go                  # Entry: load config → wire DI → start server
│
├── internal/                        # Private — không thể import từ ngoài
│   │
│   ├── domain/                      # Layer 1: Core — zero external dependencies
│   │   ├── entity/
│   │   │   ├── provider.go          # Provider{}, Status enum, Validate()
│   │   │   ├── prompt.go            # Prompt{}, Stage enum (Stage1/Stage2)
│   │   │   ├── analysis.go          # Analysis{}, SubjectType, HWType enums
│   │   │   ├── device.go            # Device{} (RPi5 token), TokenHash
│   │   │   └── admin.go             # AdminUser{}, Role enum
│   │   ├── repository/              # Pure interfaces — no implementation
│   │   │   ├── provider.go          # ProviderRepository interface
│   │   │   ├── prompt.go            # PromptRepository interface
│   │   │   ├── analysis.go          # AnalysisRepository interface
│   │   │   ├── device.go            # DeviceRepository interface
│   │   │   └── admin.go             # AdminRepository interface
│   │   ├── service/                 # External service interfaces
│   │   │   ├── ai_client.go         # AIClient interface (Strategy)
│   │   │   ├── image_processor.go   # ImageProcessor interface
│   │   │   └── cache.go             # Cache interface (rate limit, stats)
│   │   └── apperror/
│   │       └── errors.go            # Sentinel errors: ErrNotFound, ErrUnauthorized...
│   │
│   ├── application/                 # Layer 2: Use Cases — only imports domain
│   │   ├── analysis/
│   │   │   ├── analyze.go           # AnalyzeUseCase: stage1 → stage2 → save
│   │   │   ├── list.go              # ListAnalysesUseCase: cursor pagination + filter
│   │   │   └── dto.go               # Input/Output structs for this use case
│   │   ├── provider/
│   │   │   ├── create.go
│   │   │   ├── update.go
│   │   │   ├── delete.go
│   │   │   ├── list.go
│   │   │   ├── get.go
│   │   │   ├── test_connection.go   # Ping provider, measure latency
│   │   │   └── dto.go
│   │   ├── prompt/
│   │   │   ├── create.go
│   │   │   ├── update.go
│   │   │   ├── delete.go
│   │   │   ├── list.go
│   │   │   └── dto.go
│   │   ├── device/
│   │   │   ├── create.go            # Generate token, hash, store
│   │   │   ├── revoke.go
│   │   │   ├── list.go
│   │   │   └── dto.go
│   │   └── auth/
│   │       ├── login.go             # ValidateCredentials → issue JWT pair
│   │       ├── refresh.go           # Validate refresh token → new access token
│   │       ├── logout.go            # Blacklist access token in Redis
│   │       └── dto.go
│   │
│   ├── infrastructure/              # Layer 3: Implementations
│   │   ├── postgres/
│   │   │   ├── client.go            # pgxpool setup, health check
│   │   │   ├── tx.go                # Transaction helper wrapper
│   │   │   ├── query/               # sqlc generated — DO NOT EDIT
│   │   │   │   ├── db.go
│   │   │   │   ├── provider.sql.go
│   │   │   │   ├── prompt.sql.go
│   │   │   │   ├── analysis.sql.go
│   │   │   │   ├── device.sql.go
│   │   │   │   └── admin.sql.go
│   │   │   └── repo/                # implements domain/repository interfaces
│   │   │       ├── provider.go
│   │   │       ├── prompt.go
│   │   │       ├── analysis.go
│   │   │       ├── device.go
│   │   │       └── admin.go
│   │   ├── redis/
│   │   │   ├── client.go            # go-redis v9 setup, health check
│   │   │   ├── rate_limiter.go      # Sliding window rate limiting
│   │   │   ├── jwt_blacklist.go     # Token blacklist (logout)
│   │   │   └── stats.go             # INCR counters, EXPIRE daily keys
│   │   ├── ai/
│   │   │   ├── factory.go           # NewAIClient(provider) → AIClient
│   │   │   └── openai_compat/
│   │   │       └── client.go        # OpenAI-compatible HTTP client
│   │   │                            # (LiteLLM, OpenRouter, OpenAI đều dùng được)
│   │   ├── image/
│   │   │   └── processor.go         # implements ImageProcessor: resize, validate
│   │   └── crypto/
│   │       └── aes.go               # AES-256-GCM: Encrypt/Decrypt API keys
│   │
│   └── interfaces/
│       └── http/
│           ├── server.go            # Fiber app setup, graceful shutdown
│           ├── router.go            # Route groups: /api/v1/device, /api/v1/admin
│           ├── middleware/
│           │   ├── device_auth.go   # Validate Bearer token (RPi5)
│           │   ├── admin_auth.go    # Validate JWT (admin UI)
│           │   ├── rate_limit.go    # Per-device sliding window via Redis
│           │   ├── cors.go          # Whitelist admin domain
│           │   ├── logger.go        # zerolog structured request log
│           │   └── recover.go       # Panic → 500, log stack trace
│           ├── handler/
│           │   ├── analysis.go
│           │   ├── provider.go
│           │   ├── prompt.go
│           │   ├── history.go
│           │   ├── device.go
│           │   ├── auth.go
│           │   ├── stats.go
│           │   └── health.go
│           └── dto/
│               ├── request/         # Fiber body parsing + validation tags
│               └── response/        # Consistent JSON envelope
│
├── pkg/                             # Public reusable packages (có thể dùng ngoài)
│   ├── logger/
│   │   └── logger.go               # zerolog singleton, log level from env
│   ├── validator/
│   │   └── validator.go            # go-playground/validator wrapper, custom rules
│   ├── pagination/
│   │   └── cursor.go               # Cursor pagination helper (encode/decode cursor)
│   ├── timeutil/
│   │   └── timeutil.go             # UTC helpers, format strings
│   └── httputil/
│       └── response.go             # JSON envelope: {data, error, meta}
│
├── configs/
│   └── config.go                   # Env → Config struct (envconfig / godotenv)
│
├── migrations/                      # Goose SQL migrations
│   ├── 20240101000001_create_providers.sql
│   ├── 20240101000002_create_prompts.sql
│   ├── 20240101000003_create_devices.sql
│   ├── 20240101000004_create_admin_users.sql
│   ├── 20240101000005_create_analyses.sql
│   └── 20240101000006_create_settings.sql
│
├── sql/                             # sqlc input SQL queries
│   ├── schema.sql                   # Full schema (reference)
│   └── queries/
│       ├── provider.sql
│       ├── prompt.sql
│       ├── analysis.sql
│       ├── device.sql
│       └── admin.sql
│
├── scripts/
│   ├── dev.sh                       # docker-compose up + air (hot reload)
│   ├── migrate.sh                   # goose up
│   ├── migrate_down.sh              # goose down
│   ├── generate.sh                  # sqlc generate
│   └── seed.sh                      # Insert default admin + demo data
│
├── docker-compose.yml               # Local: postgres + redis
├── Dockerfile                       # Multi-stage: builder → minimal runtime
├── .air.toml                        # Air hot reload config
├── sqlc.yaml                        # sqlc config
├── Makefile                         # Shortcuts
└── go.mod
```

---

## 3. Database Schema

```sql
-- ── providers ────────────────────────────────────────────────
CREATE TABLE providers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    base_url        TEXT NOT NULL,
    api_key_enc     BYTEA NOT NULL,         -- AES-256-GCM encrypted
    model           VARCHAR(100) NOT NULL,
    timeout_sec     INTEGER NOT NULL DEFAULT 30,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_tested_at  TIMESTAMPTZ,
    last_latency_ms INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT providers_name_key UNIQUE (name)
);

-- ── prompts ──────────────────────────────────────────────────
CREATE TABLE prompts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    stage           SMALLINT NOT NULL,          -- 1 = detect homework, 2 = detail analysis
    content         TEXT NOT NULL,
    subject_filter  VARCHAR(50),                -- null = all subjects
    grade_filter    VARCHAR(10),                -- null = all grades
    is_active       BOOLEAN NOT NULL DEFAULT true,
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_prompts_stage_active ON prompts (stage, is_active);

-- ── devices (RPi5 tokens) ─────────────────────────────────────
CREATE TABLE devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    token_hash      CHAR(64) NOT NULL UNIQUE,   -- SHA-256 hex của raw token
    last_used_at    TIMESTAMPTZ,
    last_ip         INET,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── admin_users ───────────────────────────────────────────────
CREATE TABLE admin_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,              -- bcrypt cost=12
    role            VARCHAR(20) NOT NULL DEFAULT 'viewer', -- viewer | editor | admin
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── analyses ─────────────────────────────────────────────────
CREATE TABLE analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID NOT NULL REFERENCES devices(id),
    student_id      VARCHAR(100),               -- RPi5 gửi kèm
    -- context snapshot
    activity        VARCHAR(50),
    focus_score     SMALLINT,
    hw_visible      BOOLEAN,
    -- stage 1 result
    s1_doing_hw     BOOLEAN,
    s1_confidence   NUMERIC(4,3),
    s1_latency_ms   INTEGER,
    -- stage 2 result (null nếu s1_doing_hw = false)
    s2_subject      VARCHAR(50),
    s2_grade        VARCHAR(10),
    s2_hw_type      VARCHAR(50),
    s2_progress     SMALLINT,
    s2_hints        TEXT,
    s2_latency_ms   INTEGER,
    -- provider used
    provider_id     UUID REFERENCES providers(id),
    -- image
    image_path      TEXT,                       -- optional, nếu lưu ảnh
    image_width     SMALLINT,
    image_height    SMALLINT,
    image_size_kb   SMALLINT,
    -- timing
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Cursor pagination: thường query WHERE created_at < ? ORDER BY created_at DESC
CREATE INDEX idx_analyses_created_at  ON analyses (created_at DESC);
CREATE INDEX idx_analyses_device_id   ON analyses (device_id, created_at DESC);
CREATE INDEX idx_analyses_s2_subject  ON analyses (s2_subject) WHERE s2_subject IS NOT NULL;

-- ── settings ─────────────────────────────────────────────────
CREATE TABLE settings (
    key             VARCHAR(100) PRIMARY KEY,
    value           JSONB NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Ví dụ rows: capture_interval=10, image_quality=82, cooldown_hw=30
```

---

## 4. API Endpoints

### Device API (RPi5) — Bearer token auth
```
POST   /api/v1/device/analyze           # Gửi ảnh, nhận kết quả phân tích
GET    /api/v1/device/health            # Check service alive
```

### Admin API — JWT auth
```
# Auth
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

# Providers
GET    /api/v1/providers                # Danh sách (có pagination)
POST   /api/v1/providers                # Tạo mới
GET    /api/v1/providers/:id            # Chi tiết
PUT    /api/v1/providers/:id            # Cập nhật
DELETE /api/v1/providers/:id            # Xóa
POST   /api/v1/providers/:id/test       # Test connection, đo latency
POST   /api/v1/providers/:id/default    # Đặt làm provider mặc định

# Prompts
GET    /api/v1/prompts                  # Lọc theo stage, subject
POST   /api/v1/prompts
GET    /api/v1/prompts/:id
PUT    /api/v1/prompts/:id
DELETE /api/v1/prompts/:id

# Devices (RPi5 tokens)
GET    /api/v1/devices
POST   /api/v1/devices                  # Tạo token mới, trả raw token 1 lần
DELETE /api/v1/devices/:id              # Revoke

# Analysis History
GET    /api/v1/analyses                 # cursor pagination, filter: device, subject, date range
GET    /api/v1/analyses/:id             # Chi tiết 1 record

# Stats
GET    /api/v1/stats/overview           # Calls today, homework rate, top subjects
GET    /api/v1/stats/latency            # P50/P95/P99 latency per provider

# Settings
GET    /api/v1/settings
PUT    /api/v1/settings                 # Batch upsert key-value

# Health
GET    /health                          # {status, db, redis, version}
```

### Response Envelope (tất cả endpoints)
```json
// Success
{ "data": {...}, "meta": {"cursor": "...", "total": 42} }

// Error
{ "error": { "code": "UNAUTHORIZED", "message": "..." } }
```

---

## 5. Domain Interfaces chính

```go
// domain/service/ai_client.go
type Stage1Result struct {
    DoingHW    bool
    Confidence float64
    LatencyMs  int
}

type Stage2Result struct {
    Subject   string
    Grade     string
    HWType    string
    Progress  int
    Hints     string
    LatencyMs int
}

type AIClient interface {
    DetectHomework(ctx context.Context, imageJPEG []byte) (Stage1Result, error)
    AnalyzeHomework(ctx context.Context, imageJPEG []byte) (Stage2Result, error)
}

// domain/service/image_processor.go
type ProcessedImage struct {
    Data      []byte  // JPEG bytes
    Width     int
    Height    int
    SizeKB    int
}

type ImageProcessor interface {
    // Validate MIME, max size, resize nếu cần, encode JPEG
    Process(ctx context.Context, raw []byte, maxWidth, maxHeight, quality int) (ProcessedImage, error)
}

// domain/service/cache.go
type Cache interface {
    // Rate limiting
    IncrAndExpire(ctx context.Context, key string, ttl time.Duration) (int64, error)
    // JWT blacklist
    SetBlacklist(ctx context.Context, jti string, ttl time.Duration) error
    IsBlacklisted(ctx context.Context, jti string) (bool, error)
    // Stats
    IncrCounter(ctx context.Context, key string) error
    GetCounter(ctx context.Context, key string) (int64, error)
}

// domain/repository/analysis.go
type AnalysisFilter struct {
    DeviceID  *uuid.UUID
    Subject   *string
    DoingHW   *bool
    FromTime  *time.Time
    ToTime    *time.Time
    Cursor    *time.Time  // created_at cursor
    Limit     int
}

type AnalysisRepository interface {
    Create(ctx context.Context, a *entity.Analysis) error
    GetByID(ctx context.Context, id uuid.UUID) (*entity.Analysis, error)
    List(ctx context.Context, filter AnalysisFilter) ([]*entity.Analysis, error)
    CountBySubject(ctx context.Context, from, to time.Time) (map[string]int64, error)
}
```

---

## 6. Use Case mẫu: AnalyzeUseCase

```go
// application/analysis/analyze.go
type AnalyzeInput struct {
    DeviceID    uuid.UUID
    StudentID   string
    ImageRaw    []byte   // raw multipart bytes từ RPi5
    Activity    string
    FocusScore  int
    HWVisible   bool
}

type AnalyzeOutput struct {
    DoingHW   bool
    Subject   string
    Grade     string
    Hints     string
    Progress  int
}

type AnalyzeUseCase struct {
    imageProc   domain.ImageProcessor
    aiFactory   AIClientFactory    // interface, không phải concrete
    providerRepo domain.ProviderRepository
    promptRepo   domain.PromptRepository
    analysisRepo domain.AnalysisRepository
    stats        domain.Cache
}

func (uc *AnalyzeUseCase) Execute(ctx context.Context, in AnalyzeInput) (AnalyzeOutput, error) {
    // 1. Process image (resize, validate)
    img, err := uc.imageProc.Process(ctx, in.ImageRaw, 1024, 768, 82)

    // 2. Load default provider + prompts
    provider, _ := uc.providerRepo.GetDefault(ctx)
    client := uc.aiFactory.Create(provider)

    // 3. Stage 1: detect homework
    s1, err := client.DetectHomework(ctx, img.Data)
    if err != nil || !s1.DoingHW {
        uc.savePartialResult(ctx, in, img, provider, s1, nil)
        return AnalyzeOutput{DoingHW: false}, nil
    }

    // 4. Stage 2: analyze detail (chỉ khi stage 1 = true)
    s2, err := client.AnalyzeHomework(ctx, img.Data)

    // 5. Save full result
    uc.saveResult(ctx, in, img, provider, s1, &s2)

    // 6. Increment stats counter
    uc.stats.IncrCounter(ctx, "calls:today")

    return AnalyzeOutput{
        DoingHW: true,
        Subject: s2.Subject,
        Grade:   s2.Grade,
        Hints:   s2.Hints,
        Progress: s2.Progress,
    }, nil
}
```

---

## 7. Performance & Scalability

### Database
- **pgxpool** với `MaxConns=20`, `MinConns=5` — không new connection mỗi request
- **sqlc** — compile-time type-safe queries, không ORM runtime overhead
- **Index chiến lược:** cursor pagination dùng `created_at DESC` index, không dùng OFFSET
- **Partial index:** `WHERE s2_subject IS NOT NULL` cho stats queries
- **Connection timeout:** `AcquireTimeout=5s` để fail fast thay vì queue

### Redis
- **Sliding window rate limit:** `ZADD + ZREMRANGEBYSCORE + ZCARD` — O(log N), không race condition
- **Pipeline** cho multi-key operations (stats counters)
- Key pattern: `rate:{device_id}:{window}`, `blacklist:{jti}`, `stats:calls:{date}`

### HTTP (Fiber)
- Fiber dùng **fasthttp** — zero-allocation HTTP, 10x faster than net/http cho throughput cao
- **Worker pool** cho image processing: goroutine pool size = `GOMAXPROCS * 2`
- **Timeout middleware:** context timeout 35s (margin trên AI call 30s timeout)
- **Body limit:** 10MB max multipart để tránh memory abuse
- **Gzip** response cho large JSON (history list)

### AI calls
- **Context propagation:** cancel nếu client disconnect giữa chừng
- **Timeout:** 30s per AI call (cấu hình qua provider.timeout_sec)
- Stage 2 chỉ gọi khi Stage 1 → `doing_hw=true` — tránh double cost
- **Retry:** không retry mặc định (AI calls idempotent nhưng tốn $), để client retry

### Image processing
```go
// Resize chạy trong goroutine riêng, không block request goroutine
func (p *Processor) Process(ctx context.Context, raw []byte, ...) (ProcessedImage, error) {
    // 1. Validate content-type (JPEG/PNG), max size (5MB)
    // 2. Decode image header để đọc dimensions (không decode full)
    // 3. Nếu cần resize: dùng imaging.Fit() với INTER_AREA
    // 4. imencode JPEG với quality param
    // 5. Return ProcessedImage với metadata
}
```

---

## 8. Security

### API Key Encryption (AES-256-GCM)
```go
// infrastructure/crypto/aes.go
// Master key: AES_MASTER_KEY env var (32 bytes hex)
// Mỗi API key: random nonce (12 bytes) + ciphertext, lưu cùng trong DB

func Encrypt(plaintext, masterKey []byte) ([]byte, error)
func Decrypt(ciphertext, masterKey []byte) ([]byte, error)
// Trả về: nonce || ciphertext (prepend nonce để decrypt tự tách)
```

### Device Token
```go
// Khi tạo token mới:
rawToken := crypto/rand.Read(32 bytes) → hex encode (64 chars)
tokenHash := sha256(rawToken) → lưu DB
// Trả raw token CHỈ 1 LẦN cho admin — không thể recover sau đó

// Khi verify:
hash := sha256(bearerToken)
db.FindDeviceByHash(hash) → so sánh constant-time
```

### Admin JWT
```go
// Access token: 15 phút, contains: {sub: admin_id, jti: uuid, role}
// Refresh token: 7 ngày, HttpOnly cookie
// Logout: jti → Redis blacklist với TTL = remaining access token lifetime
// Middleware check: verify signature → check blacklist → extract claims
```

### Rate Limiting
```
Device API: 20 req/phút per device (sliding window 60s)
Auth endpoints: 5 req/phút per IP
Admin API: 300 req/phút per admin user
```

### CORS
```go
// Chỉ whitelist ADMIN_FRONTEND_URL từ env
// Credentials: false (JWT in Authorization header, không cookie cross-origin)
// Methods: GET, POST, PUT, DELETE, OPTIONS
```

---

## 9. Dev Scripts & Makefile

```makefile
# Makefile

.PHONY: dev build test migrate generate seed lint

dev:           ## Khởi động local dev (postgres + redis + hot reload)
	docker-compose up -d postgres redis
	air -c .air.toml

build:         ## Build binary production
	CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o bin/server ./cmd/server

test:          ## Chạy unit tests
	go test ./... -race -cover

test-int:      ## Integration tests (cần DB + Redis đang chạy)
	go test ./... -tags=integration -race

migrate:       ## Chạy migration lên mới nhất
	goose -dir migrations postgres "$(DATABASE_URL)" up

migrate-down:  ## Rollback 1 migration
	goose -dir migrations postgres "$(DATABASE_URL)" down

generate:      ## Tạo lại sqlc type-safe queries
	sqlc generate

seed:          ## Insert dữ liệu mẫu (admin user + demo provider)
	go run scripts/seed/main.go

lint:          ## Golangci-lint
	golangci-lint run ./...

docker-build:  ## Build Docker image
	docker build -t tutor-backend:latest .

docker-push:   ## Push lên registry
	docker push tutor-backend:latest
```

### `scripts/dev.sh`
```bash
#!/usr/bin/env bash
set -e

echo "🐳 Starting PostgreSQL + Redis..."
docker-compose up -d postgres redis

echo "⏳ Waiting for postgres to be ready..."
until docker-compose exec postgres pg_isready -U tutor; do sleep 1; done

echo "📦 Running migrations..."
make migrate

echo "🌱 Seeding default data..."
make seed

echo "🚀 Starting server with hot reload..."
make dev
```

### `docker-compose.yml` (local only)
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tutor
      POSTGRES_USER: tutor
      POSTGRES_PASSWORD: tutor_dev_password
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    ports: ["6379:6379"]

volumes:
  postgres_data:
```

### `.env.example`
```bash
# Server
APP_PORT=8080
APP_ENV=development           # development | production

# Database
DATABASE_URL=postgres://tutor:tutor_dev_password@localhost:5432/tutor?sslmode=disable
DB_MAX_CONNS=20
DB_MIN_CONNS=5

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=your-256-bit-secret-here
AES_MASTER_KEY=your-32-byte-hex-master-key-here

# CORS
ADMIN_FRONTEND_URL=http://localhost:5173   # dev | https://admin.tutor.com prod

# Logging
LOG_LEVEL=debug                # debug | info | warn | error

# AI (defaults, có thể override từ DB providers table)
DEFAULT_AI_TIMEOUT_SEC=30
MAX_IMAGE_SIZE_MB=5
```

---

## 10. Dockerfile (multi-stage)

```dockerfile
# Stage 1: Build
FROM golang:1.23-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server ./cmd/server

# Stage 2: Minimal runtime (~20MB image)
FROM alpine:3.20
RUN apk --no-cache add ca-certificates tzdata
WORKDIR /app
COPY --from=builder /app/server .
COPY --from=builder /app/migrations ./migrations
EXPOSE 8080
ENTRYPOINT ["./server"]
```

---

## 11. Dependencies (go.mod chính)

```
github.com/gofiber/fiber/v3            # HTTP framework
github.com/gofiber/contrib/jwt         # JWT middleware
github.com/jackc/pgx/v5               # PostgreSQL driver (pgxpool)
github.com/redis/go-redis/v9           # Redis client
github.com/sqlc-dev/sqlc              # SQL code generation (dev tool)
github.com/pressly/goose/v3           # DB migrations (dev tool)
github.com/rs/zerolog                  # Zero-allocation structured logging
github.com/go-playground/validator/v10 # Input validation
github.com/golang-jwt/jwt/v5          # JWT sign/verify
github.com/disintegration/imaging      # Image resize
github.com/google/uuid                 # UUID generation
github.com/joho/godotenv              # Load .env
golang.org/x/crypto                    # bcrypt password hash
github.com/air-verse/air              # Hot reload (dev tool)
```

---

## 12. Thứ tự implement

```
Phase 1 — Foundation
[ ] go mod init + Dockerfile + docker-compose.yml
[ ] configs/config.go (env loading)
[ ] pkg/logger, pkg/httputil, pkg/pagination
[ ] migrations: tất cả tables
[ ] infrastructure/postgres/client.go + redis/client.go

Phase 2 — Domain + Infrastructure
[ ] domain/entity/* + domain/repository/* interfaces
[ ] domain/service/* interfaces
[ ] infrastructure/crypto/aes.go
[ ] infrastructure/postgres/repo/* (implement interfaces)
[ ] infrastructure/redis/* (rate limiter, blacklist, stats)
[ ] infrastructure/image/processor.go
[ ] infrastructure/ai/openai_compat/client.go + factory.go

Phase 3 — Use Cases
[ ] application/auth/* (login, refresh, logout)
[ ] application/provider/* (CRUD + test)
[ ] application/prompt/* (CRUD)
[ ] application/device/* (create token, revoke)
[ ] application/analysis/analyze.go ← core use case
[ ] application/analysis/list.go

Phase 4 — HTTP Layer
[ ] interfaces/http/middleware/* (auth, rate limit, cors, logger)
[ ] interfaces/http/handler/* (tất cả handlers)
[ ] interfaces/http/dto/* (request/response structs)
[ ] interfaces/http/router.go + server.go

Phase 5 — Scripts + Seed
[ ] scripts/seed (default admin user, demo provider với LiteLLM, default prompts)
[ ] Makefile + scripts/dev.sh
[ ] Integration test cơ bản cho analyze endpoint
```
