# tutor-airobot-be

Backend API cho hệ thống **Tutor AI Robot** — nhận ảnh từ thiết bị Raspberry Pi, phân tích qua AI, lưu lịch sử và cung cấp dashboard quản trị.

## Kiến trúc tổng quan

```
Raspberry Pi (ai-tutor)
        │  POST /api/v1/device/analyze
        │  Bearer: <device-token>
        ▼
tutor-airobot-be  ─── PostgreSQL
        │         ─── Redis
        │
        ▼
Admin Frontend (tutor-airobot-fe)
```

**Stack:** Go + Fiber v3 · PostgreSQL · Redis · Docker

---

## Yêu cầu

| Công cụ | Phiên bản |
|---------|-----------|
| Go | ≥ 1.22 |
| Docker + Docker Compose | bất kỳ |
| make | bất kỳ (tuỳ chọn) |

---

## Cài đặt lần đầu

### 1. Tạo file `.env`

```bash
cp .env.example .env
```

Mở `.env` và điền 2 giá trị bắt buộc:

```bash
# Tạo JWT_SECRET (tối thiểu 32 ký tự)
openssl rand -base64 48

# Tạo AES_MASTER_KEY (đúng 32 bytes = 64 ký tự hex)
openssl rand -hex 32
```

Dán kết quả vào `.env`:

```env
JWT_SECRET=<kết quả lệnh đầu>
AES_MASTER_KEY=<kết quả lệnh thứ hai>
```

Kiểm tra các biến còn lại — mặc định phù hợp cho môi trường local:

```env
DATABASE_URL=postgres://tutor:tutor_dev_password@localhost:5432/tutor?sslmode=disable
REDIS_URL=redis://localhost:6379/0
ADMIN_FRONTEND_URL=http://localhost:5173
APP_ENV=development
```

### 2. Khởi động Postgres + Redis

```bash
docker-compose up -d
```

Kiểm tra:

```bash
docker-compose ps
# Cả 2 service phải ở trạng thái (healthy)
```

### 3. Build và chạy backend

```bash
go build -o bin/server ./cmd/server
./bin/server
```

Khi thấy dòng `HTTP server starting :8080` là backend sẵn sàng.
Migrations tự động chạy khi khởi động.

### 4. Seed dữ liệu ban đầu (chỉ 1 lần)

```bash
go run scripts/seed/main.go
```

Lệnh này tạo:
- **Admin user:** `admin@tutor.local` / `admin123`
- Demo AI provider (placeholder, cần cập nhật API key thật qua UI)
- 2 system prompt mặc định (Stage 1 + Stage 2)

---

## Chạy hàng ngày

```bash
# Khởi động infrastructure (nếu chưa chạy)
docker-compose up -d

# Chạy backend
./bin/server
```

Hoặc dùng Makefile:

```bash
make infra-up   # docker postgres + redis
make build-local
./bin/server
```

---

## Makefile commands

| Command | Tác dụng |
|---------|----------|
| `make build-local` | Build binary cho OS hiện tại |
| `make build` | Build binary Linux (production) |
| `make dev` | Chạy infra + hot reload (cần `air`) |
| `make infra-up` | Chỉ khởi động postgres + redis |
| `make infra-down` | Dừng postgres + redis |
| `make seed` | Seed admin user + demo data |
| `make test` | Chạy unit tests |
| `make migrate` | Apply migrations (goose) |
| `make migrate-status` | Xem trạng thái migrations |
| `make lint` | Chạy golangci-lint |

---

## Cấu trúc project

```
tutor-airobot-be/
├── cmd/server/main.go              # Entry point, wiring toàn bộ dependencies
├── configs/config.go               # Đọc .env, validate biến bắt buộc
├── internal/
│   ├── domain/                     # Entities, repository interfaces, errors
│   ├── application/                # Use cases (business logic)
│   │   ├── analysis/               # Analyze, ListAnalyses use cases
│   │   ├── auth/                   # Login, Refresh, Logout
│   │   ├── device/                 # Create, Revoke, List devices
│   │   ├── prompt/                 # CRUD prompts
│   │   └── provider/               # CRUD + test providers
│   ├── infrastructure/
│   │   ├── ai/                     # AI client (OpenAI-compatible)
│   │   ├── crypto/                 # AES encrypt/decrypt API keys
│   │   ├── image/                  # Image validation + resize
│   │   ├── postgres/repo/          # PostgreSQL implementations
│   │   └── redis/                  # JWT blacklist, rate limiter
│   └── interfaces/http/
│       ├── handler/                # HTTP handlers (auth, provider, device, analysis, stats)
│       ├── middleware/             # JWT auth, rate limit, CORS, logger
│       └── router.go               # Route definitions
├── migrations/                     # Goose SQL migrations (6 tables)
├── scripts/seed/main.go            # Seed admin + demo data
├── docs/FEATURES.md                # Tài liệu chi tiết tính năng & API
├── docker-compose.yml              # Postgres + Redis
└── Makefile
```

---

## API endpoints chính

| Endpoint | Auth | Mô tả |
|----------|------|-------|
| `POST /api/v1/auth/login` | — | Đăng nhập admin |
| `POST /api/v1/auth/refresh` | — | Làm mới access token |
| `GET  /api/v1/providers` | Admin | Danh sách AI providers |
| `POST /api/v1/providers` | Admin | Tạo provider mới |
| `PUT  /api/v1/providers/:id` | Admin | Cập nhật provider (kể cả `is_default`) |
| `POST /api/v1/providers/:id/test` | Admin | Test kết nối provider |
| `GET  /api/v1/devices` | Admin | Danh sách thiết bị RPi |
| `POST /api/v1/devices` | Admin | Tạo thiết bị, trả raw token (1 lần duy nhất) |
| `POST /api/v1/devices/:id/revoke` | Admin | Thu hồi token thiết bị |
| `POST /api/v1/device/analyze` | Device | RPi gửi ảnh để phân tích AI |
| `GET  /api/v1/analyses` | Admin | Lịch sử phân tích (cursor pagination) |
| `GET  /api/v1/stats/overview` | Admin | KPI tổng quan |
| `GET  /api/v1/stats/latency` | Admin | Latency theo giờ (24h) |
| `GET  /api/v1/stats/subjects` | Admin | Phân bố môn học (30 ngày) |

Xem chi tiết: [`docs/FEATURES.md`](docs/FEATURES.md)

---

## Kết nối với thiết bị Raspberry Pi

1. Vào admin UI → **Devices** → **Thêm thiết bị**
2. Copy raw token (chỉ hiển thị 1 lần)
3. Cấu hình trên RPi:

```env
# file .env trên Raspberry Pi (ai-tutor)
DEVICE_TOKEN=<raw-token>
BACKEND_URL=http://<ip-backend>:8080
```

---

## Biến môi trường đầy đủ

| Biến | Mặc định | Bắt buộc |
|------|----------|----------|
| `DATABASE_URL` | — | ✅ |
| `JWT_SECRET` | — | ✅ (≥ 32 ký tự) |
| `AES_MASTER_KEY` | — | ✅ (64 ký tự hex) |
| `APP_PORT` | `8080` | |
| `APP_ENV` | `development` | |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `ADMIN_FRONTEND_URL` | `http://localhost:5173` | |
| `JWT_ACCESS_EXPIRY_MIN` | `15` | |
| `JWT_REFRESH_EXPIRY_DAYS` | `7` | |
| `RATE_LIMIT_AUTH_RPM` | `5` | |
| `RATE_LIMIT_ADMIN_RPM` | `300` | |
| `RATE_LIMIT_DEVICE_RPM` | `20` | |
| `MAX_IMAGE_SIZE_MB` | `5` | |
| `DEFAULT_AI_TIMEOUT_SEC` | `30` | |
| `LOG_LEVEL` | `info` | |
