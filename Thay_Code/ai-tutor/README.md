# AI Tutor Monitor

Hệ thống giám sát tập trung học sinh / nhân viên qua camera — chạy trên **Raspberry Pi 5**.

Phát hiện realtime 15 trạng thái hoạt động, điểm tập trung (Focus Score 0–100), theo dõi bài tập học sinh và gửi ảnh lên AI cloud để phân tích chi tiết.

## Kiến trúc tổng quan

```
Raspberry Pi 5
├── Camera Module v2.1 (CSI)
│       │ dual-stream: lores (detection) + main (snapshot 5MP)
│       ▼
├── ai-tutor (Python)
│   ├── Detectors
│   │   ├── FaceDetector   — MediaPipe Face Landmarker + Pose (52 blendshapes)
│   │   ├── HandDetector   — MediaPipe Hands + pen grip + phone score
│   │   └── YoloDetector   — 3 models: COCO + Object365 + OIV7
│   ├── Analyzers
│   │   ├── SignalBundle        — tổng hợp tất cả tín hiệu (frozen dataclass)
│   │   ├── ConfidenceScorer   — 10 ActivityClassifiers, chọn winner
│   │   ├── DrowsinessTracker  — 6 tín hiệu, 4 mức độ ngủ gật
│   │   ├── ActivityAnalyzer   — pipeline chính → activity + focus score
│   │   └── HomeworkMonitor    — state machine: IDLE→REQUESTING→CAPTURED→COOLDOWN
│   └── Web dashboard (Flask, port 5000)
│       │
│       │ Khi HomeworkMonitor đủ điều kiện → chụp ảnh 5MP
│       │ POST /api/v1/device/analyze + Bearer token
│       ▼
└── tutor-airobot-be (Go backend)        ← server riêng hoặc cùng mạng
    ├── Pipeline AI 2 giai đoạn (Stage 1: phát hiện bài → Stage 2: phân tích)
    ├── Lưu lịch sử PostgreSQL
    └── Admin dashboard (tutor-airobot-fe)
```

**Luồng chính:**
1. Camera → MediaPipe + YOLO phát hiện hoạt động theo frame
2. `ActivityAnalyzer` tổng hợp → `activity` + `focus_score` + `homework_visible`
3. `HomeworkMonitor` tích lũy khi học sinh làm bài → sau ~20-30s tự động chụp ảnh
4. Ảnh gửi lên backend → AI phân tích môn học, tiến độ, gợi ý → lưu lịch sử
5. Admin xem toàn bộ trên dashboard web

---

## Yêu cầu phần cứng

| Thiết bị | Model |
|---|---|
| Board | Raspberry Pi 5 (4GB hoặc 8GB RAM) |
| Camera | Raspberry Pi Camera Module v2.1 (IMX219, 8MP) |
| Kết nối | Cable CSI ribbon 15-pin chính hãng |
| Nguồn | Official RPi 5 Power Supply (5V/5A USB-C) |
| Storage | microSD 32GB+ Class 10 / A1 |

---

## Cài đặt nhanh

```bash
git clone git@github.com:nhanntv/tutor-airobot-pi.git /home/pi/ai-tutor
cd /home/pi/ai-tutor

chmod +x setup.sh
./setup.sh --with-all-ai
```

Sau đó điền cấu hình vào `.env` rồi chạy:

```bash
./run.sh
```

Mở dashboard: `http://<ip-raspberry-pi>:5000`

---

## Cài đặt chi tiết

### Bước 1 — Clone project

```bash
git clone git@github.com:nhanntv/tutor-airobot-pi.git /home/pi/ai-tutor
cd /home/pi/ai-tutor
```

### Bước 2 — Chạy setup script

```bash
chmod +x setup.sh
./setup.sh [options]
```

**Các flag tuỳ chọn:**

| Flag | Tác dụng |
|---|---|
| `--with-claude` | Cài Anthropic SDK |
| `--with-openai` | Cài OpenAI SDK |
| `--with-gemini` | Cài Google Generative AI |
| `--with-all-ai` | Cài tất cả AI providers |
| `--skip-system` | Bỏ qua `apt install` (nếu đã cài) |

Script tự động:
- Cài system packages (`picamera2`, `libatlas`, `espeak`, `mpg123`...)
- Tạo Python virtual environment (`venv/`)
- `pip install -r requirements.txt`
- Tạo file `.env` mẫu nếu chưa có

### Bước 3 — Cấu hình `.env`

```bash
nano .env
```

**AI Provider (chọn 1):**

```env
# Tự động chọn provider có key (auto/openai/claude/gemini)
AI_PROVIDER=auto

# Claude (Anthropic)
CLAUDE_API_KEY=sk-ant-...
CLAUDE_VISION_MODEL=claude-sonnet-4-6

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_VISION_MODEL=gpt-4o-mini

# Gemini
GEMINI_API_KEY=AIza...
```

**Camera:**

```env
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FPS=30
SNAPSHOT_WIDTH=2560      # Độ phân giải ảnh gửi AI (5MP)
SNAPSHOT_HEIGHT=1920
```

**Hiệu năng:**

```env
DETECTION_FPS=10         # MediaPipe tối đa 10fps (RPi5 max ~12fps)
STREAM_FPS=20            # MJPEG stream về browser
```

**Kết nối backend** (xem mục [Kết nối với backend](#kết-nối-với-backend-tutor-airobot-be)):

```env
DEVICE_TOKEN=<token từ admin UI>
BACKEND_URL=http://<ip-backend>:8080
```

### Bước 4 — Chạy

```bash
./run.sh
```

Hoặc thủ công:

```bash
source venv/bin/activate
python3 main.py
```

---

## Tính năng

### 15 trạng thái hoạt động

| Trạng thái | Điều kiện phát hiện |
|---|---|
| `sleeping` | DrowsinessTracker SEVERE — gục đầu + nhắm mắt > 5s |
| `using_phone` | Phone score cao + duy trì ≥ 4s (temporal filter) |
| `distracted` | Nhìn sang nơi khác > ngưỡng thời gian |
| `drowsy` | DrowsinessTracker MODERATE+ (ngáp, mắt lim dim, gật đầu) |
| `eating_drinking` | YOLO phát hiện chai/cốc + tay vùng trên |
| `working_computer` | Nhìn màn hình + gõ phím |
| `writing_notes` | Tay viết + nhìn xuống (YOLO sách/bút/pose cổ tay boost) |
| `reading` | 3 cases: sách+nhìn xuống, cầm sách lên, không màn hình+nhìn xuống |
| `focused_studying` | Nhìn màn hình + tương tác (không gõ phím liên tục) |
| `watching_screen` | Nhìn màn hình không gõ phím |
| `talking` | Miệng mở liên tục + nhìn sang |
| `playing` | Cười + tay chuyển động nhanh + gaze mất tập trung |
| `present` | Có mặt, chưa xác định rõ hoạt động |
| `briefly_away` | Vắng mặt ngắn (< 5 phút) |
| `absent` | Vắng mặt chính thức (≥ 5 phút) |

### Phát hiện ngủ gật (DrowsinessTracker)

6 tín hiệu kết hợp, 4 cấp độ:

| Cấp độ | Điều kiện |
|---|---|
| ALERT | Bình thường |
| MILD | 1-2 tín hiệu yếu (mắt nặng / hơi gật) |
| MODERATE | 3+ tín hiệu (ngáp + mắt lim dim + gật đầu) |
| SEVERE | Gục đầu hoàn toàn + nhắm mắt > 5s → `sleeping` |

### HomeworkMonitor

State machine tự động theo dõi khi học sinh làm bài:
- **IDLE** → tích lũy khi `is_homework` hoặc `homework_visible=True`
- **REQUESTING** → hỏi học sinh "Đang làm môn gì?" + auto-capture sau ~3s `homework_visible` liên tiếp
- **CAPTURED** → nút "Phân tích AI" trên dashboard
- **COOLDOWN** → chờ trước khi chu kỳ mới

### Triple YOLO Pipeline

3 model chạy tuần tự mỗi N frame:

| Model | Dataset | Classes quan trọng |
|---|---|---|
| yolo26n-objv1 | Object365 | person, book, pen, laptop, keyboard, mouse, notepaper, pencil_case |
| yolov8n | COCO | person, phone, bottle, cup |
| yolov8n-oiv7 | Open Images V7 | Pen (class 376), Book (class 54) |

Benchmark RPi5: ~143ms tổng (với ONNX export), chạy mỗi 3 frame → an toàn ở 9-10fps.

### Pen Grip Detection

MediaPipe hand landmarks phát hiện cách cầm bút (pinch ratio < 0.45):
- Cầm bút → boost `writing_notes`, block false positive phone
- Cầm phone → ratio ~0.7, không bị ảnh hưởng

---

## Cấu trúc thư mục

```
ai-tutor/
├── main.py                          # Entry point, orchestration, camera loop
├── setup.sh                         # Script cài đặt một lần
├── run.sh                           # Script khởi động
├── requirements.txt                 # Python dependencies
├── .env                             # Config (không commit — trong .gitignore)
│
├── core/
│   ├── config.py                    # Đọc .env, fallback về constants
│   ├── constants.py                 # 21 nhóm ngưỡng mặc định
│   └── types.py                     # TypedDicts dùng chung
│
├── camera/
│   ├── camera_module.py             # Picamera2 dual-stream (lores + main)
│   └── stream_module.py             # Flask MJPEG + REST API + homework endpoints
│
├── detectors/
│   ├── face_detector.py             # FaceDetector facade (Strategy Pattern)
│   │                                #   _LandmarkerBackend (frontal ≤70°)
│   │                                #   _PoseBackend (profile 90°, fallback)
│   ├── hand_detector.py             # MediaPipe Hands + pen grip + phone score
│   ├── yolo_detector.py             # Triple YOLO (Object365 + COCO + OIV7)
│   └── multi_person_tracker.py      # Orchestrator nhiều người, PersonSession
│
├── analyzers/
│   ├── signals.py                   # SignalBundle (frozen dataclass)
│   ├── activity_classifier.py       # 10 ActivityClassifiers (Strategy Pattern)
│   ├── confidence_scorer.py         # ConfidenceScorer: score_all() → winner
│   ├── drowsiness_tracker.py        # DrowsinessTracker: 6 signals, 4 levels
│   ├── activity_analyzer.py         # Pipeline chính → activity + focus + homework_visible
│   └── homework_monitor.py          # State machine IDLE→REQUESTING→CAPTURED→COOLDOWN
│
├── ai/
│   └── ai_module.py                 # Multi-provider LLM (OpenAI/Claude/Gemini)
│
├── services/
│   └── alert_service.py             # TTS alerts khi phát hiện bất thường
│
├── audio/
│   ├── tts_module.py                # Text-to-speech (espeak/mpg123)
│   └── stt_module.py                # Speech-to-text (placeholder)
│
├── utils/
│   ├── image_utils.py               # Xử lý ảnh, resize, encode base64
│   └── time_utils.py                # Các tiện ích thời gian
│
├── web/
│   └── templates/index.html         # Dashboard UI (camera + status + homework panel)
│
├── models/
│   └── face_landmarker.task         # MediaPipe Face Landmarker TFLite
│
├── *.pt / *.onnx                    # YOLO model weights (3 models)
│
├── docs/
│   ├── business/                    # Tài liệu nghiệp vụ
│   └── plan/                        # Kế hoạch phát triển
│
└── logs/                            # Log files (trong .gitignore)
```

---

## API Endpoints (Flask, port 5000)

| Endpoint | Method | Mô tả |
|---|---|---|
| `/` | GET | Dashboard UI |
| `/video_feed` | GET | MJPEG stream |
| `/status` | GET | Trạng thái hiện tại: activity, focus_score, drowsy_level... |
| `/stats` | GET | Thống kê phiên: thời gian mỗi hoạt động |
| `/absence_log` | GET | Lịch sử vắng mặt |
| `/capture` | GET | Chụp ảnh raw (JSON + base64) |
| `/read_content` | POST | Gửi ảnh → AI đọc nội dung |
| `/chat` | POST | Chat với AI gia sư |
| `/homework_status` | GET | Trạng thái HomeworkMonitor (state, auto_capture_pct, book_visible) |
| `/homework_analyze` | POST | Kích hoạt phân tích AI thủ công cho ảnh đã chụp |
| `/api/display` | POST | Bật/tắt YOLO bounding boxes trên stream |

---

## Kết nối với backend (tutor-airobot-be)

`ai-tutor` gửi ảnh bài tập lên backend để phân tích AI cloud và lưu lịch sử dài hạn.

### Bước 1 — Đảm bảo backend đang chạy

Xem hướng dẫn: [tutor-airobot-be](https://github.com/nhanntv/tutor-airobot-be)

### Bước 2 — Tạo thiết bị và lấy token

1. Mở admin UI (`tutor-airobot-fe`) → đăng nhập (`admin@tutor.local` / `admin123`)
2. Vào **Devices** → **Thêm thiết bị** → đặt tên (vd: `RPi Camera - Phòng A101`)
3. Copy **token** — chỉ hiển thị một lần duy nhất

### Bước 3 — Cấu hình `.env`

```env
DEVICE_TOKEN=<token vừa copy>
BACKEND_URL=http://<ip-backend>:8080
```

### Bước 4 — Khởi động lại

```bash
./run.sh
```

Khi `HomeworkMonitor` phát hiện học sinh làm bài đủ điều kiện, nó tự động gửi ảnh lên backend. Kết quả xuất hiện trên admin dashboard.

**Kiểm tra kết nối qua log:**
```
[HomeworkMonitor] Gửi ảnh lên backend... OK (542ms)
```

Lỗi `401 Unauthorized` → kiểm tra `DEVICE_TOKEN`.
Lỗi `connection refused` → kiểm tra `BACKEND_URL` và backend đang chạy.

---

## Cấu hình nâng cao

Tất cả ngưỡng điều chỉnh được qua `.env` — không cần sửa code:

```env
# Vắng mặt
ABSENCE_SHORT_THRESHOLD=60       # giây → "rời chỗ ngắn"
ABSENCE_LONG_THRESHOLD=300       # giây → "vắng mặt" (5 phút)

# Mất tập trung
DISTRACTION_DURATION=5           # giây nhìn sang nơi khác

# Phone detection
PHONE_MIN_SUSTAINED_FRAMES=36    # ~4s ở 9fps để confirm dùng điện thoại

# Ngủ gật
DROWSY_EYE_CLOSURE_THRESH=0.25   # EAR threshold
DROWSY_YAW_THRESH=0.65           # ngưỡng ngáp

# HomeworkMonitor
HOMEWORK_VISIBLE_SCORE_MIN=45    # điểm tối thiểu để tính homework_visible

# ROI — chỉ phân tích 1 người khi nhiều người ngồi cùng hàng
ROI_ENABLED=true
ROI_X1=0.2
ROI_X2=0.8

# YOLO
YOLO_SKIP_FRAMES=2               # chạy YOLO mỗi N frame (tiết kiệm CPU)
YOLO_CONF_THRESH=0.35

# Camera side (điều chỉnh khi camera đặt lệch)
# CAMERA_SIDE=front               # front / front_left / front_right / left / right
```

Xem đầy đủ: [`docs/business/configuration.md`](docs/business/configuration.md)

---

## Troubleshooting

**Camera không nhận:**
```bash
libcamera-hello --list-cameras
sudo raspi-config  # → Interface Options → Camera → Enable
sudo reboot
```

**FPS thấp (< 8fps):**
```bash
CAMERA_WIDTH=960
CAMERA_HEIGHT=540
YOLO_SKIP_FRAMES=3
```

**"Vắng mặt" ảo (phát hiện sai):**
```bash
ABSENCE_BUFFER_FRAMES=90    # tăng buffer
```

**Gaze detection không chính xác (camera đặt lệch):**
```bash
CAMERA_SIDE=front_right     # camera bên phải người dùng
# hoặc
CAMERA_SIDE=front_left      # camera bên trái người dùng
```

**Nhầm viết bài với dùng máy tính:**
```bash
HOMEWORK_WRITING_MIN_SCORE=50    # hạ ngưỡng (mặc định 60)
```

Xem thêm: [`docs/business/hardware-setup.md`](docs/business/hardware-setup.md)

---

## Chạy toàn bộ hệ thống

```
[Server/PC]
  Terminal 1: cd tutor-airobot-be  &&  ./bin/server   # Go backend :8080
  Terminal 2: cd tutor-airobot-fe  &&  npm run dev     # Admin UI   :5173

[Raspberry Pi]
  Terminal 3: cd ai-tutor          &&  ./run.sh        # Camera app :5000
```

| Dịch vụ | URL |
|---------|-----|
| Camera dashboard (RPi) | `http://<ip-rpi>:5000` |
| Admin dashboard | `http://localhost:5173` |
| Backend API | `http://localhost:8080` |

---

## Tài liệu

| File | Nội dung |
|---|---|
| [`docs/business/overview.md`](docs/business/overview.md) | Tổng quan hệ thống |
| [`docs/business/activity-states.md`](docs/business/activity-states.md) | 15 trạng thái hoạt động |
| [`docs/business/configuration.md`](docs/business/configuration.md) | Tất cả tham số cấu hình |
| [`docs/business/architecture.md`](docs/business/architecture.md) | Kiến trúc & luồng dữ liệu |
| [`docs/business/hardware-setup.md`](docs/business/hardware-setup.md) | Lắp đặt camera |
