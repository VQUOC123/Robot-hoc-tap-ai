# tutor-airobot-fe

Giao diện quản trị cho hệ thống **Tutor AI Robot** — quản lý AI providers, thiết bị Raspberry Pi, xem lịch sử phân tích và dashboard thống kê.

## Kiến trúc tổng quan

```
tutor-airobot-fe (Vue 3)
        │  REST API
        ▼
tutor-airobot-be (Go, port 8080)
```

**Stack:** Vue 3.5 · TypeScript · Vite 6 · Tailwind CSS v4 · shadcn-vue · TanStack Query v5

---

## Yêu cầu

| Công cụ | Phiên bản |
|---------|-----------|
| Node.js | ≥ 18 |
| npm | ≥ 9 |

---

## Cài đặt lần đầu

### 1. Cài dependencies

```bash
cd tutor-airobot-fe
npm install
```

### 2. Tạo file `.env.development`

```bash
cp .env.development.example .env.development
```

Nội dung mặc định đã đúng cho môi trường local — không cần sửa nếu backend chạy tại `localhost:8080`:

```env
VITE_API_URL=http://localhost:8080
VITE_APP_TITLE=Tutor Admin (Dev)
```

Nếu backend chạy ở IP khác (ví dụ deploy trên server):

```env
VITE_API_URL=http://192.168.1.100:8080
```

---

## Chạy

### Development (hot reload)

```bash
npm run dev
```

Mở trình duyệt: **http://localhost:5173**

### Production build

```bash
npm run build
```

File tĩnh xuất ra thư mục `dist/`. Có thể serve bằng nginx, Caddy hoặc:

```bash
npm run preview   # preview local tại port 4173
```

---

## Đăng nhập lần đầu

> Backend phải đang chạy và đã seed dữ liệu (`go run scripts/seed/main.go` trong `tutor-airobot-be`)

| Trường | Giá trị |
|--------|---------|
| Email | `admin@tutor.local` |
| Mật khẩu | `admin123` |

**Sau khi đăng nhập, làm ngay:**
1. Vào **Providers** → cập nhật API key thật cho AI provider
2. Vào **Devices** → tạo thiết bị → copy token → cấu hình vào Raspberry Pi

---

## Tính năng

| Trang | Tính năng |
|-------|-----------|
| **Dashboard** | KPI cards (tổng phân tích, tỉ lệ làm bài, latency, thiết bị), biểu đồ latency theo giờ, biểu đồ phân bố môn học, bảng phân tích gần đây |
| **Providers** | Thêm/sửa/xóa AI provider (OpenAI, Claude, Gemini, LiteLLM...), set default, test kết nối |
| **Prompts** | Quản lý system prompt Stage 1 (phát hiện bài tập) và Stage 2 (phân tích chi tiết) |
| **Devices** | Đăng ký thiết bị RPi, xem trạng thái kết nối, thu hồi token |
| **Analyses** | Lịch sử phân tích với infinite scroll, filter theo ngày/môn/thiết bị/trạng thái bài tập, xem chi tiết từng record |
| **Settings** | Cấu hình hệ thống |

---

## Cấu trúc project

```
src/
├── main.ts                         # Entry point
├── router/                         # Vue Router (routes + auth guard)
├── shared/
│   ├── api/
│   │   ├── client.ts               # Axios instance + JWT interceptor + refresh
│   │   └── types.ts                # CursorResponse, ApiError
│   ├── components/
│   │   ├── ui/                     # shadcn-vue components
│   │   ├── data-table/             # TanStack Table wrapper
│   │   └── layout/                 # AppLayout, PageContainer, NavBar
│   ├── composables/                # useConfirm, useCopyToClipboard, ...
│   └── utils/                      # format helpers (formatMs, formatDate, ...)
└── features/
    ├── auth/                       # Login page, useAuth, token storage
    ├── providers/                  # Provider list, form, detail
    ├── prompts/                    # Prompt list, editor
    ├── devices/                    # Device table, create dialog
    └── analyses/                   # Analysis table, filters, detail dialog, charts
```

---

## Biến môi trường

| Biến | Mô tả |
|------|-------|
| `VITE_API_URL` | URL của backend (không có dấu `/` cuối) |
| `VITE_APP_TITLE` | Tiêu đề hiển thị trên trình duyệt |

File `.env.development` dùng khi `npm run dev`.
File `.env.production` dùng khi `npm run build` (copy từ `.env.production.example`).

---

## Scripts

| Script | Tác dụng |
|--------|----------|
| `npm run dev` | Dev server với hot reload (port 5173) |
| `npm run build` | Build production vào `dist/` |
| `npm run preview` | Preview bản build tại port 4173 |
| `npm run lint` | ESLint kiểm tra toàn bộ code |
| `npm run type-check` | TypeScript type checking |
