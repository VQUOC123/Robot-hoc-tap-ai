# AI Tutor — Refactor & Implementation Plan
> **Mục tiêu:** Hệ thống giám sát học sinh trên Raspberry Pi 5 — detect chính xác trạng thái học tập,
> chụp ảnh bài tập chất lượng cao, gửi lên server phân tích; đảm bảo hiệu năng ổn định, không lag, không quá nhiệt.
>
> **Phiên bản:** 1.1 | **Ngày:** 2026-04-13 | **Phần cứng:** RPi 5 8GB + Camera v2.1 (IMX219)

---

## Mục lục

1. [Phân tích hiện trạng](#1-phân-tích-hiện-trạng)
2. [Kiến trúc mục tiêu](#2-kiến-trúc-mục-tiêu)
3. [Cấu trúc thư mục sau refactor](#3-cấu-trúc-thư-mục-sau-refactor)
4. [Phase 1 — Performance Foundation](#4-phase-1--performance-foundation)
5. [Phase 2 — Accuracy Enhancement (ConfidenceScorer)](#5-phase-2--accuracy-enhancement-confidencescorer)
6. [Phase 3 — Homework Capture Pipeline](#6-phase-3--homework-capture-pipeline)
7. [Phase 4 — Voice Interaction (Mic + Speaker)](#7-phase-4--voice-interaction-mic--speaker)
8. [Phase 5 — Robot AI API (Future)](#8-phase-5--robot-ai-api-future)
9. [Design Principles & Patterns](#9-design-principles--patterns)
10. [Hướng dẫn cài đặt từng Phase](#10-hướng-dẫn-cài-đặt-từng-phase)
11. [Constants & Configuration Reference](#11-constants--configuration-reference)
12. [Benchmark & Performance Targets](#12-benchmark--performance-targets)

---

## 1. Phân tích hiện trạng

### 1.1 Strengths — Giữ nguyên
| Component | Điểm mạnh | Quyết định |
|-----------|-----------|-----------|
| `yolo_detector.py` | Producer-consumer pattern, non-blocking | Giữ, chuyển sang ONNX |
| `face_detector.py` | Strategy Pattern + round-robin (1 person/frame) | Giữ nguyên |
| `drowsiness_tracker.py` | 6-signal temporal (SRP, injected) | Giữ nguyên |
| `homework_monitor.py` | State machine rõ ràng | Refactor thành HomeworkService |
| `core/config.py` + `constants.py` | Không hardcode, .env override | Giữ, bổ sung thêm |
| `camera_module.py` | Dual-stream, snapshot không cần mode-switch | Giữ nguyên |
| `ai/ai_module.py` | Multi-provider, lazy import | Giữ, tách cloud AI |

### 1.2 Bottlenecks — Cần sửa
| Vấn đề | Nguyên nhân | Tác động | Giải pháp |
|--------|-------------|----------|-----------|
| MediaPipe Hands **blocking** ~77ms | Chạy đồng bộ trong main loop | Pipeline ~150ms, 6-7fps | Async worker thread |
| YOLO PyTorch ~110ms | Chưa convert ONNX | 2.75× chậm hơn cần | Export ONNX |
| Activity dùng **binary rules** | Không có confidence score | Nhiều false positive/negative | Weighted confidence |
| Activity dùng **binary rules** | 20-step waterfall | False positive phone/writing | ConfidenceScorer weighted |
| Homework capture **thiếu quality check** | Chụp ngay khi trigger | Ảnh mờ, notebook nhỏ | Image quality gate |
| Không có **analytics storage** | Không ghi SQLite | Không report cho giáo viên | SQLite session log |

### 1.3 Gaps — Thiếu hoàn toàn
- ~~`ConfidenceScorer` — weighted multi-signal score thay binary rules~~ **✅ Phase 2 DONE**
- ~~`SignalBundle` — frozen dataclass tổng hợp signals từ 3 detectors~~ **✅ Phase 2 DONE**
- ~~`homework_visible` flag — detect bài tập rõ để chụp hình~~ **✅ Phase 2 DONE**
- ~~`AsyncWorker` base class — tái sử dụng cho YOLO, Hands~~ **✅ Phase 1 DONE**
- ~~`HandDetector` async — MediaPipe không block main loop~~ **✅ Phase 1 DONE**
- ~~YOLO ONNX export — 110ms → 40ms~~ **✅ Phase 1 DONE** (`yolo26n.onnx` đã có)
- ~~`ImageQualityChecker` gate — blur/brightness trước khi capture~~ **✅ Phase 3 (partial) DONE**
- `AlertService` — TTS prompts (cần speaker hardware)
- `HomeworkService` — server upload thật (cần `HOMEWORK_SERVER_URL`)
- `SessionStorage` — SQLite analytics (optional, server đã handle)
- Voice feedback loop — mic + STT (cần USB mic hardware)

---

## 2. Kiến trúc mục tiêu

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                             │
│  web/templates/index.html  ←→  camera/stream_module.py         │
│  Flask routes, MJPEG stream, REST endpoints                     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│  APPLICATION LAYER (Use Cases / Orchestration)                  │
│  analyzers/activity_analyzer.py   ← tổng hợp signals           │
│  analyzers/drowsiness_tracker.py  ← temporal drowsy             │
│  services/homework_service.py     ← capture + verify + upload   │
│  services/alert_service.py        ← TTS alerts, voice prompts   │
│  services/confidence_scorer.py    ← weighted multi-signal       │
└──────────────┬─────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────┐
│  DETECTION LAYER (Signal Extraction)                            │
│  detectors/face_detector.py    → FaceResult                     │
│  detectors/hand_detector.py    → HandResult                     │
│  detectors/yolo_detector.py    → YoloResult  [ONNX, async]      │
│  detectors/multi_person_tracker.py → [PersonSession]            │
└──────────────┬──────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────┐
│  INFRASTRUCTURE LAYER (Hardware & External Models)              │
│  camera/camera_module.py       → Picamera2, dual-stream         │
│  ai/local_verifier.py          → Moondream2 (async, on-device)  │
│  ai/cloud_ai.py                → OpenAI/Claude/Gemini           │
│  storage/session_db.py         → SQLite analytics               │
│  audio/tts_module.py           → espeak / gTTS                  │
│  audio/stt_module.py           → Whisper (future)               │
└─────────────────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────┐
│  CORE LAYER (Domain: Config, Constants, Types, Utilities)       │
│  core/config.py     core/constants.py     core/thermal.py       │
│  core/types.py      (NEW: dataclasses, enums, protocols)        │
│  core/exceptions.py (NEW: custom exceptions)                    │
│  utils/async_worker.py    (NEW: base class cho async threads)   │
│  utils/image_utils.py     (NEW: resize, quality, encode)        │
│  utils/time_utils.py      (NEW: duration format, timestamps)    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Threading Model (sau refactor)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Thread 1: MAIN LOOP (10fps throttled)                              │
│  ├── camera.capture_frame() → 1280×720 RGB                          │
│  ├── face_detector.detect()   [~25ms, round-robin]                  │
│  ├── yolo_detector.submit()   [~1ms, non-blocking]                  │
│  ├── hand_detector.submit()   [~1ms, non-blocking]  ← MỚI           │
│  ├── yolo_result = yolo_detector.get_result()       [~1ms cache]    │
│  ├── hand_result = hand_detector.get_result()       [~1ms cache]    │
│  ├── confidence_scorer.score(face, hand, yolo)                      │
│  ├── activity_analyzer.analyze(signals)                             │
│  ├── homework_service.update(activity, frame)                       │
│  └── stream.update_frame()                                          │
│                                                                     │
│  Thread 2: YOLO ONNX Worker (đã có)                                 │
│  ├── Nhận frame qua Event                                           │
│  ├── Resize → 320×320 → ONNX inference (~40ms)                      │
│  └── Cache result (lock-free read)                                  │
│                                                                     │
│  Thread 3: Hand Async Worker (MỚI — copy pattern YOLO)              │
│  ├── Nhận frame qua Event                                           │
│  ├── MediaPipe Hands inference (~77ms)                              │
│  └── Cache result (lock-free read)                                  │
│                                                                     │
│  Thread 4: Flask Server                                             │
│  ├── MJPEG stream (20fps cap)                                       │
│  ├── REST API: /status, /homework/*, /capture                       │
│  └── Homework upload → Cloud AI                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Cấu trúc thư mục sau refactor

```
/home/pi/ai-tutor/
│
├── main.py                          # Entry point — khởi tạo và start threads
│
├── core/                            # CORE LAYER — không import layer trên
│   ├── __init__.py
│   ├── config.py                    # Đọc .env, fallback constants
│   ├── constants.py                 # TẤT CẢ default values (không hardcode ở file khác)
│   ├── thermal.py                   # CPU thermal management
│   ├── types.py                     # NEW: Dataclasses, Enums, Protocol interfaces
│   └── exceptions.py               # NEW: Custom exceptions (DetectorError, etc.)
│
├── utils/                           # NEW — Utilities, không có business logic
│   ├── __init__.py
│   ├── async_worker.py             # NEW: AsyncWorker base class (reuse YOLO/Hands/Moondream)
│   ├── image_utils.py              # NEW: resize, quality_score, encode_jpeg, crop_roi
│   └── time_utils.py               # NEW: format_duration, timestamp, elapsed
│
├── infrastructure/                  # INFRASTRUCTURE LAYER
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── camera_module.py        # Picamera2 wrapper (dual-stream)
│   │   └── stream_module.py        # Flask MJPEG + REST API routes
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── local_verifier.py       # NEW: Moondream2 async verifier
│   │   └── cloud_ai.py             # Đổi tên từ ai_module.py
│   │
│
├── detectors/                       # DETECTION LAYER
│   ├── __init__.py
│   ├── face_detector.py            # MediaPipe Face Landmarker + Pose fallback
│   ├── hand_detector.py            # MediaPipe Hands (chuyển sang AsyncWorker)
│   ├── yolo_detector.py            # YOLO ONNX + AsyncWorker (refactor)
│   └── multi_person_tracker.py     # Multi-person orchestrator
│
├── analyzers/                       # APPLICATION LAYER — Analysis
│   ├── __init__.py
│   ├── activity_analyzer.py        # 15-state classifier (+ confidence scoring)
│   └── drowsiness_tracker.py       # 6-signal temporal (giữ nguyên)
│
├── services/                        # NEW — APPLICATION LAYER — Use Cases
│   ├── __init__.py
│   ├── homework_service.py         # Tách từ homework_monitor.py + thêm quality gate
│   ├── confidence_scorer.py        # NEW: Weighted multi-signal scoring
│   └── alert_service.py            # NEW: TTS alerts, voice prompts
│
├── audio/
│   ├── __init__.py
│   ├── tts_module.py               # Text-to-speech (giữ)
│   └── stt_module.py               # Speech-to-text (giữ, tích hợp sau)
│
├── web/
│   └── templates/
│       └── index.html              # Dashboard (giữ, cập nhật UI)
│
├── models/                         # Model files (gitignore, download on setup)
│   ├── face_landmarker.task        # MediaPipe (~14MB)
│   ├── yolo26n.onnx                # NEW: ONNX version
│   ├── yolo26n-objv1-150.onnx     # NEW: ONNX version
│   └── moondream/                  # NEW: Moondream2 model files
│
├── storage/                        # Runtime data (gitignore)
│   └── captures/                   # Homework images (temp, xoá sau khi upload)
│
├── docs/
│   ├── business/                   # Tài liệu nghiệp vụ (hiện tại)
│   └── plan/
│       └── REFACTOR_PLAN.md        # File này
│
├── logs/                           # Log files
├── requirements.txt                # Python dependencies
├── requirements-local-ai.txt       # NEW: Moondream2 dependencies
├── setup.sh                        # System setup (cập nhật thêm Moondream)
├── run.sh                          # Khởi động app
└── .env                            # API keys + config override
```

**Nguyên tắc import:**
- `core/` → không import gì từ project
- `utils/` → chỉ import từ `core/`
- `detectors/` → import từ `core/`, `utils/`
- `analyzers/`, `services/` → import từ `core/`, `utils/`, `detectors/`
- `infrastructure/` → import từ tất cả layers dưới
- `main.py` → import từ tất cả

---

## 4. Phase 1 — Performance Foundation

> **Mục tiêu:** Pipeline từ ~150ms → ~65ms. Detection FPS: 6-7 → 12-15fps. Nhiệt độ giảm ~8-10°C.

### 4.1 Task 1.1 — AsyncWorker Base Class

**File tạo mới:** `utils/async_worker.py`

**Mục đích:** Abstract base class tái sử dụng cho bất kỳ detector nào cần chạy inference async.
Tránh duplicate threading boilerplate giữa YOLO, Hands, và Moondream2.

**Interface:**
```python
class AsyncWorker(ABC):
    """Producer-consumer base cho inference workers.

    Subclass chỉ cần override:
      - _load_model() → khởi tạo model
      - _run_inference(frame: np.ndarray) → Any

    Sử dụng latest-frame-wins (không queue) vì:
      - Luôn xử lý frame mới nhất, không xử lý frame cũ đã lỗi thời
      - Tránh backlog khi inference chậm hơn camera FPS
    """

    def submit(self, frame: np.ndarray) -> None:
        """Non-blocking: gửi frame để xử lý."""

    def get_result(self) -> Any:
        """Non-blocking: lấy kết quả cache gần nhất."""

    def stop(self) -> None:
        """Dừng worker thread (graceful shutdown)."""

    @abstractmethod
    def _load_model(self) -> None: ...

    @abstractmethod
    def _run_inference(self, frame: np.ndarray) -> Any: ...
```

**Lưu ý khi implement:**
- Dùng `threading.Event` cho submit signal (không dùng queue — latest-frame-wins)
- Lock riêng biệt cho `_pending_frame` và `_cached_result` (không hold 2 locks cùng lúc → tránh deadlock)
- `_stop_event` để graceful shutdown khi app tắt
- Log error nhưng không crash thread khi inference thất bại (worker tự recover)

### 4.2 Task 1.2 — Refactor YoloDetector dùng AsyncWorker

**File sửa:** `detectors/yolo_detector.py`

**Thay đổi:**
- Kế thừa `AsyncWorker` thay vì tự viết threading logic
- `_load_model()`: load cả primary + secondary model
- `_run_inference()`: inference + merge kết quả 2 models → return `YoloResult`
- **Giữ nguyên** public interface: `submit()`, `get_result()`, `start()`, `stop()`

**Output type** — tạo trong `core/types.py`:
```python
@dataclass
class YoloResult:
    detections: list[Detection]       # list các bbox đã detect
    has_phone: bool
    has_laptop: bool
    has_keyboard: bool
    has_mouse: bool
    has_book: bool
    has_bottle: bool
    has_cup: bool
    has_pen: bool
    has_notepaper: bool
    has_person: bool
    timestamp: float                  # time.monotonic() khi inference xong
```

### 4.3 Task 1.3 — HandDetector chuyển sang Async

**File sửa:** `detectors/hand_detector.py`

**Thay đổi:**
- Wrap MediaPipe Hands inference trong `AsyncWorker`
- Main loop không block 77ms nữa (1-2 frame delay không đáng kể)
- Thêm `resize_for_inference()` từ `utils/image_utils.py`: resize xuống 480×360
  trước khi feed vào MediaPipe (tay không cần full 720p)
- **Giữ nguyên** public interface

**Output type** — trong `core/types.py`:
```python
@dataclass
class HandResult:
    hand_count: int
    activity: str                     # "typing" | "writing" | "possible_phone" | ...
    speed: float                      # px/frame, 15-frame window
    zone: str                         # "upper" | "middle" | "bottom" | "none"
    phone_score: int                  # 0-100
    pen_grip: bool
    positions: list[tuple[float, float]]
    timestamp: float
```

### 4.4 Task 1.4 — YOLO ONNX Export

**Script tạo mới:** `scripts/export_onnx.py`

**Mục đích:** Chạy 1 lần để export `.pt` → `.onnx`, lưu vào `models/`.

```python
# scripts/export_onnx.py
"""
Export YOLO models sang ONNX format.
Chạy: python3 scripts/export_onnx.py

Benchmark RPi5:
  PyTorch .pt:  ~110ms/inference
  ONNX:         ~40ms/inference (2.75x speedup)
"""
```

**Cập nhật `setup.sh`:** thêm step tự động export ONNX sau khi download `.pt`.

**Cập nhật `yolo_detector.py`:** ưu tiên load `.onnx` nếu có, fallback về `.pt`.

### 4.5 Task 1.5 — ImageUtils

**File tạo mới:** `utils/image_utils.py`

**Functions (tái sử dụng ở nhiều nơi):**
```python
def resize_for_inference(frame: np.ndarray, target_size: int) -> np.ndarray:
    """Resize giữ aspect ratio, pad về target_size × target_size."""

def encode_jpeg(frame: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    """Encode frame sang JPEG bytes."""

def assess_image_quality(frame: np.ndarray, roi: Rect | None = None) -> ImageQuality:
    """Đánh giá chất lượng ảnh: blur score, brightness, contrast, bbox coverage."""

def crop_roi(frame: np.ndarray, roi: Rect) -> np.ndarray:
    """Crop frame theo ROI rect."""

def draw_overlay(frame: np.ndarray, detections: list, labels: dict) -> np.ndarray:
    """Vẽ bbox + label lên frame."""
```

**`ImageQuality` dataclass** — trong `core/types.py`:
```python
@dataclass
class ImageQuality:
    blur_score: float       # Laplacian variance — cao = nét
    brightness: float       # 0-255 mean
    contrast: float         # stddev
    coverage_ratio: float   # bbox_area / frame_area (notebook trong frame)
    is_acceptable: bool     # blur > MIN_BLUR_SCORE and coverage > MIN_COVERAGE
```

Constants mới trong `constants.py`:
```python
# Group 19 — Image Quality Gate
IMAGE_QUALITY_MIN_BLUR_SCORE = 80.0     # Laplacian variance
IMAGE_QUALITY_MIN_COVERAGE = 0.08       # Notebook chiếm ≥8% frame
IMAGE_QUALITY_MIN_BRIGHTNESS = 40       # Không tối quá
IMAGE_QUALITY_MAX_BRIGHTNESS = 220      # Không sáng quá
```

### 4.6 Task 1.6 — TimeUtils & Core Types

**File tạo mới:** `utils/time_utils.py`
```python
def format_duration(seconds: float) -> str:
    """30 → "30 giây", 90 → "1 phút 30 giây", 3600 → "1 giờ"."""

def monotonic_elapsed(start: float) -> float:
    """time.monotonic() - start."""

def seconds_to_hms(seconds: float) -> tuple[int, int, int]:
    """(hours, minutes, seconds)."""
```

**File tạo mới:** `core/types.py` — tập trung tất cả shared dataclasses, enums:
```python
from enum import Enum
from dataclasses import dataclass, field

class ActivityState(str, Enum):
    SLEEPING          = "sleeping"
    USING_PHONE       = "using_phone"
    DISTRACTED        = "distracted"
    DROWSY            = "drowsy"
    EATING_DRINKING   = "eating_drinking"
    WORKING_COMPUTER  = "working_computer"
    WRITING_NOTES     = "writing_notes"
    READING           = "reading"
    FOCUSED_STUDYING  = "focused_studying"
    WATCHING_SCREEN   = "watching_screen"
    TALKING           = "talking"
    PLAYING           = "playing"
    PRESENT           = "present"
    BRIEFLY_AWAY      = "briefly_away"
    ABSENT            = "absent"

class DrowsinessLevel(int, Enum):
    ALERT    = 0
    MILD     = 1
    MODERATE = 2
    SEVERE   = 3

class HomeworkState(str, Enum):
    IDLE       = "idle"
    REQUESTING = "requesting"
    CAPTURED   = "captured"
    VERIFYING  = "verifying"   # NEW: Moondream2 đang verify
    COOLDOWN   = "cooldown"

@dataclass
class DetectionSignals:
    """Tổng hợp tất cả signals từ 3 detectors — input cho ConfidenceScorer."""
    face: FaceResult | None = None
    hand: HandResult | None = None
    yolo: YoloResult | None = None
    timestamp: float = field(default_factory=time.monotonic)

@dataclass
class ActivityResult:
    state: ActivityState
    confidence: float            # 0.0 - 1.0
    focus_score: int             # 0-100
    status_text: str
    details: dict[str, str]
    is_homework_activity: bool   # writing_notes | reading | focused_studying
```

**File tạo mới:** `core/exceptions.py`:
```python
class DetectorError(Exception):    """Lỗi trong quá trình detect."""
class ModelLoadError(DetectorError): """Không load được model."""
class InferenceError(DetectorError): """Lỗi khi chạy inference."""
class CameraError(Exception):      """Lỗi camera."""
class StorageError(Exception):     """Lỗi database."""
```

### 4.7 Expected Results — Phase 1

| Metric | Trước | Sau |
|--------|-------|-----|
| Pipeline latency/frame | ~150-180ms | ~60-70ms |
| Detection FPS | 6-7fps | 12-15fps |
| CPU usage (idle) | ~85% | ~60-65% |
| Temperature | ~78-82°C | ~68-72°C |
| MediaPipe Hands blocking | 77ms | ~1ms (async cache) |
| YOLO latency | ~110ms | ~40ms |

---

## 5. Phase 2 — Accuracy Enhancement (ConfidenceScorer)

> **Mục tiêu:** Tăng accuracy detect các trạng thái borderline.
> Thay thế 20-step binary waterfall bằng weighted confidence scoring.
> **✅ COMPLETED** — Không dùng local AI model (quá nặng cho RPi5).

### 5.1 Quyết định kiến trúc — Không dùng Moondream2

| Option | Pros | Cons | Quyết định |
|--------|------|------|-----------|
| Moondream2 local | Hiểu hình ảnh sâu | 2-3GB RAM, 0.5-2s, quá nhiệt | ❌ Loại |
| ConfidenceScorer + rules | 0ms, 0 RAM, deterministic | Không hiểu ảnh thật | ✅ Chọn |

**Lý do:** RPi5 trong robot enclosure kín → heat budget hạn chế.
Moondream2 2B params → 1-3GB RAM + CPU heat. ConfidenceScorer xử lý
signal đã có từ MediaPipe/YOLO → zero overhead, cải thiện accuracy
bằng cách kết hợp thông minh hơn (thay vì binary waterfall).

### 5.2 ✅ Task 2.1 — SignalBundle + ActivityClassifiers

**Files đã tạo:**
- `analyzers/signals.py` — `SignalBundle`, `HandSignals`, `GazeSignals`, `ObjectSignals`
- `analyzers/activity_classifier.py` — 10 classifiers: Writing, Reading, Computer,
  Phone, Distracted, Talking, Eating, Playing, FocusedStudying, WatchingScreen

**Design (Strategy Pattern):**
```python
class ActivityClassifier(ABC):
    @property @abstractmethod
    def activity(self) -> str: ...

    @abstractmethod
    def score(self, signals: SignalBundle) -> int:
        """0-100: 0 = hard blocked, 50-100 = classify khi vượt threshold."""

    def is_possible(self, signals: SignalBundle) -> bool:
        return True  # override cho gate conditions (cần có_screen, etc.)
```

**Ví dụ WritingClassifier weights:**
```
pen_grip=True    → +35  (pinch grip = chắc chắn cầm bút)
hand=="writing"  → +25  (speed > TYPING_MAX ở bottom zone)
gaze_down        → +18  (nhìn xuống vở)
has_pen (YOLO)   → +15  (bút trong scene)
has_notepaper    → +12
has_book         → +8
zone_bottom      → +7
phone_in_hand    → 0    (hard block)
gaze_screen      → -20
phone_score>=55  → -25  (KHÔNG phải bút)
```

### 5.3 ✅ Task 2.2 — ConfidenceScorer Orchestrator

**File đã tạo:** `analyzers/confidence_scorer.py`

```python
class ConfidenceScorer:
    def score_all(self, signals: SignalBundle) -> dict[str, int]: ...
    def classify(self, signals: SignalBundle) -> tuple[str, int]: ...
    def classify_excluding(self, signals, exclude: set) -> tuple[str, int]: ...
    def writing_score(self, signals: SignalBundle) -> int: ...
    def phone_score(self, signals: SignalBundle) -> int: ...
```

**Thresholds (constants.py Group 21):**
```python
CONFIDENCE_WRITING_THRESHOLD  = 50  # Cần nhiều signal để tránh false positive
CONFIDENCE_READING_THRESHOLD  = 40
CONFIDENCE_COMPUTER_THRESHOLD = 45
CONFIDENCE_PHONE_THRESHOLD    = 45  # raw score → feed vào temporal filter
CONFIDENCE_MIN_CLASSIFY       = 30
HOMEWORK_WRITING_MIN_SCORE    = 60  # + book/notepaper → homework_visible
```

### 5.4 ✅ Task 2.3 — Tích hợp vào ActivityAnalyzer

**File sửa:** `analyzers/activity_analyzer.py`

**Thay đổi đã thực hiện:**
1. Import `SignalBundle`, `ConfidenceScorer`
2. `self._scorer = ConfidenceScorer()` trong `__init__`
3. Build `SignalBundle` sau reclassification (has_keyboard/has_book)
4. Steps 1-6 (hard intercepts) giữ nguyên: absence, sleeping, phone, distracted, drowsy, eating
5. Steps 7-17 thay bằng `self._scorer.classify_excluding(signals, {phone/distracted/eating})`
6. Talking/playing vẫn dùng temporal frame counter (để tránh flicker)
7. Thêm vào result dict: `homework_visible`, `homework_writing_score`, `homework_book_detected`

**Result dict mới:**
```python
{
    ...
    "homework_visible"      : bool,   # writing_score>=60 AND has_book/notepaper
    "homework_writing_score": int,    # 0-100, raw WritingClassifier score
    "homework_book_detected": bool,   # has_book OR has_notepaper
}
```

**Backward compatible:** `analyze(hand_info, gaze_info, pose_info) -> dict` không đổi.

---

## 6. Phase 3 — Homework Capture Pipeline

> **Mục tiêu:** Khi detect học sinh đang làm bài tập → yêu cầu giơ bài →
> auto-capture khi `homework_visible=True` → quality gate → upload lên server phân tích.
>
> **Không dùng local AI model (Moondream2 quá nặng cho RPi5).**
> `homework_visible` từ ConfidenceScorer đã đủ để verify (Phase 2 ✅).

### 6.1 Workflow đầy đủ

```
[Detect: writing_notes | reading | focused_studying, sustained ≥ 30s]
          │
          ▼
[HomeworkMonitor: state = REQUESTING]  ← ✅ đã implement
  - Hiển thị: "Đang theo dõi bài tập..."
  - Countdown: 20s timeout
  - homework_visible=True → auto-capture sau 3s liên tiếp
  - Hoặc: user click "Chụp hình" thủ công
          │
          │ homework_visible=True (ConfidenceScorer: writing_score≥60 + book)
          ▼
[ImageQualityChecker.assess()]         ← Phase 3 cần implement
  - blur_score ≥ MIN_BLUR_SCORE?
  - notebook coverage ≥ MIN_COVERAGE?
  - brightness trong khoảng?
    │ Fail → UI thông báo "Ảnh chưa rõ" → quay lại REQUESTING
    │ Pass ↓
          ▼
[HomeworkMonitor: state = CAPTURED]    ← ✅ đã implement
  - camera.capture_snapshot() → 2560×1920 (main stream, không ngắt lores)
  - Lưu vào storage/captures/{session_id}/{timestamp}.jpg
  - TTS (tùy chọn): "Đã chụp bài tập! Đang gửi lên phân tích..."
          │
          ▼
[CloudAI.analyze_homework(image_b64)]  ← ✅ đã implement (ai/ai_module.py)
  - Response: {doing_hw, subject, grade, hw_type, progress, correct, help, confidence}
          │
          ▼
[HomeworkMonitor: state = COOLDOWN]    ← ✅ đã implement
  - Hiển thị kết quả trên dashboard
  - Cooldown: 120s trước khi trigger lại
```

### 6.2 Task 3.1 — HomeworkService

**File tạo mới:** `services/homework_service.py`
(Tách và nâng cấp từ `analyzers/homework_monitor.py`)

**Thay đổi so với HomeworkMonitor hiện tại (Phase 3 cần implement):**
1. Thêm `ImageQualityChecker` gate trước khi accept capture
2. Thêm TTS prompts qua `AlertService` (tùy chọn, cần speaker)
3. Upload metadata kèm image (student context, date, subject hint)
4. Retry logic khi quality fail (tối đa HOMEWORK_QUALITY_RETRIES lần)

> **Không cần VERIFYING state / LocalVerifier:** `homework_visible` từ ConfidenceScorer
> (writing_score ≥ 60 + book/notepaper) đã thay thế role của Moondream2 verify.

**Constants mới (group 18 cập nhật):**
```python
# Group 18 — Homework Monitor (cập nhật)
HOMEWORK_DETECT_DURATION      = 30    # giây sustained trước khi trigger
HOMEWORK_REQUEST_TIMEOUT      = 20    # giây timeout REQUESTING state
HOMEWORK_COOLDOWN_SECONDS     = 120   # giây cooldown sau analyze
HOMEWORK_AUTO_CAPTURE         = True  # Tự chụp khi quality pass
HOMEWORK_QUALITY_RETRIES      = 3     # Số lần thử lại nếu quality fail
HOMEWORK_QUALITY_CHECK_ENABLED = True  # Bật/tắt ImageQualityChecker gate
HOMEWORK_TTS_PROMPTS_ENABLED  = True  # Bật/tắt TTS nhắc học sinh
```

### 6.3 Task 3.2 — AlertService *(chi tiết: `docs/plan/ALERT_VOICE_PLAN.md`)*

**File tạo mới:** `services/alert_service.py`

**Mục đích:** Tập trung tất cả logic alert/TTS, tránh scatter TTS calls khắp nơi.

```python
class AlertService:
    """Quản lý TTS alerts và notifications."""

    def speak(self, message: str, priority: AlertPriority = AlertPriority.NORMAL) -> None:
        """Non-blocking TTS. High priority ngắt message đang phát."""

    def alert_distracted(self, student_name: str, duration_s: float) -> None:
        """TTS nhắc mất tập trung."""

    def alert_phone_detected(self, student_name: str) -> None:
        """TTS cảnh báo dùng điện thoại."""

    def prompt_homework_show(self, student_name: str) -> None:
        """TTS yêu cầu giơ bài."""

    def confirm_homework_captured(self) -> None:
        """TTS xác nhận đã chụp."""

    def speak_homework_result(self, result: dict) -> None:
        """TTS đọc kết quả phân tích bài tập."""
```

**Thông điệp TTS** — lưu trong `constants.py` (group 21):
```python
# Group 21 — TTS Messages (Vietnamese)
TTS_DISTRACTED      = "{name} ơi, hãy tập trung vào bài học nhé!"
TTS_PHONE_ALERT     = "{name}, hãy cất điện thoại và tập trung học nào!"
TTS_HOMEWORK_SHOW   = "Em có thể giơ bài tập lên cho thầy cô xem không?"
TTS_HOMEWORK_RETRY  = "Ảnh chưa rõ lắm, em giơ bài cao hơn và gần hơn nhé!"
TTS_HOMEWORK_OK     = "Cảm ơn em! Đang gửi bài tập lên phân tích..."
TTS_HOMEWORK_RESULT = "Bài tập {subject} của em đạt {progress}%. {help}"
TTS_SLEEPING_ALERT  = "{name} ơi! Tỉnh dậy và tiếp tục học nào!"
```

### 6.4 Task 3.3 — Cloud AI (Homework Analysis)

**File đổi tên:** `ai/ai_module.py` → `infrastructure/ai/cloud_ai.py`

**Bổ sung:**
```python
def analyze_homework(
    self,
    image_b64: str,
    metadata: HomeworkMetadata,   # student_id, date, subject_hint, assignment_id
) -> HomeworkAnalysisResult:
    """
    Gửi ảnh bài tập lên Cloud AI để phân tích.

    Output: {
        doing_hw: bool,
        subject: str,           # "Toán" | "Văn" | "Anh" | ...
        grade: str,             # "Lớp 5" | ...
        hw_type: str,           # "exercise" | "reading" | "project"
        progress: int,          # 0-100%
        correct: int,           # 0-100% (độ chính xác ước tính)
        help: str,              # Gợi ý, nhận xét
        confidence: int,        # 0-100%
        assignment_match: bool, # Có khớp assignment_id không (nếu có)
    }
    """
```

**`HomeworkMetadata` dataclass** — trong `core/types.py`:
```python
@dataclass
class HomeworkMetadata:
    student_id: str
    date: str                    # ISO format
    subject_hint: str = ""       # Gợi ý môn học (nếu biết)
    assignment_id: str = ""      # ID bài về nhà (nếu có từ server)
    session_duration_s: float = 0.0
    focus_score_avg: float = 0.0
```

### 6.5 Task 3.4 — Logging (Không dùng SQLite)

**Quyết định:** Không dùng SQLite trong Phase 3. Lý do:
- Core workflow không cần: Pi chỉ detect → capture → upload server
- Server đã handle lưu trữ kết quả phía mình
- SQLite là analytics feature (teacher reports, history) → implement sau nếu cần

**Thay thế đơn giản:** Log ra file text/JSON khi cần debug:
```python
# Trong HomeworkService — chỉ log khi DEBUG=true
if Config.DEBUG_MODE:
    log_path = Path("logs") / f"homework_{date}.jsonl"
    log_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
```

**Khi nào thêm SQLite:** Nếu cần báo cáo offline cho giáo viên trực tiếp từ Pi,
hoặc cần buffer khi server không khả dụng → tạo `infrastructure/storage/session_db.py` lúc đó.

---

## 7. Phase 4 — Voice Interaction (Mic + Speaker) *(chi tiết: `docs/plan/ALERT_VOICE_PLAN.md`)*

> **Phụ thuộc phần cứng:** USB microphone hoặc ReSpeaker HAT.
> Phase này implement sau khi detect accuracy đã đạt mục tiêu.

### 7.1 Workflow Voice

```
[HomeworkService: REQUESTING]
  → Speaker: "Em giơ bài tập lên nhé"
  → Mic: Listen for 5s (wake word hoặc voice activity)
  → STT: "Thầy ơi em làm xong rồi" → trigger auto-capture
  → Fallback: countdown 20s → auto-capture nếu quality OK
```

### 7.2 STT Options trên RPi5

| Model | RAM | Latency | Accuracy (Vietnamese) |
|-------|-----|---------|----------------------|
| Whisper tiny (GGUF) | ~200MB | ~0.5s | Tốt |
| Whisper base (GGUF) | ~400MB | ~1s | Tốt hơn |
| Vosk small-vi | ~50MB | ~0.1s realtime | Chấp nhận |

**Khuyến nghị:** Whisper tiny GGUF qua `whisper-cpp-python` — cân bằng tốt giữa accuracy và latency.

### 7.3 Task 4.1 — Cập nhật stt_module.py

**Interface chuẩn:**
```python
class STTModule:
    def listen_for_response(self, timeout_s: float = 5.0) -> str | None:
        """Lắng nghe và trả về text, hoặc None nếu timeout/không nghe thấy."""

    def listen_hotword(self, hotwords: list[str], timeout_s: float = 10.0) -> str | None:
        """Lắng nghe hotword cụ thể (ví dụ: "xong", "làm xong", "báo cáo")."""
```

---

## 8. Phase 5 — Robot AI API (Future)

> Implement sau khi accuracy ổn định và Phase 4 hoàn thành.
> Không implement trong các phases hiện tại.

### 8.1 Planned API

```
WebSocket: ws://<pi-ip>:5001/events
  ← Push events: {type, student_id, activity, confidence, timestamp}

REST:
  GET  /api/students          → list active students + current state
  GET  /api/student/{id}      → detailed state, focus timeline
  POST /api/command           → {type: "alert"|"praise"|"prompt_homework"}
  GET  /api/report?date=today → session summary for teacher
```

### 8.2 Khi nào chuyển sang Phase 5

- Detection accuracy ≥ 90% trên các trường hợp thực tế
- Phase 3 (Homework) hoàn chỉnh và ổn định
- Hardware Robot AI đã sẵn sàng

---

## 9. Design Principles & Patterns

### 9.1 SOLID

| Nguyên tắc | Áp dụng |
|-----------|---------|
| **S**RP | Mỗi class 1 nhiệm vụ: `ConfidenceScorer` chỉ tính score, `AlertService` chỉ quản lý alerts, `ImageQualityChecker` chỉ assess quality |
| **O**CP | `AsyncWorker` base class → mở rộng bằng subclass (YOLO, Hands, Moondream), không sửa base |
| **L**SP | `LocalVerifier` và `CloudAI` đều implement `IVerifier` protocol → hoán đổi được |
| **I**SP | `IDetector`, `IAnalyzer`, `IVerifier` — interface nhỏ, không fat interface |
| **D**IP | `HomeworkService` nhận `LocalVerifier`, `CloudAI`, `AlertService` qua constructor injection |

### 9.2 Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| Strategy | `FaceDetector` backends (Landmarker/Pose) | Đã có, giữ |
| Observer | `LocalVerifier.verify_async(callback)` | Decouple verify result từ main loop |
| Template Method | `AsyncWorker._load_model()` + `_run_inference()` | DRY cho YOLO/Hands/Moondream |
| State Machine | `HomeworkService` (IDLE→REQUESTING→VERIFYING→CAPTURED→COOLDOWN) | Rõ ràng, dễ test |
| Factory | `CloudAI._get_provider()` | Multi-provider, lazy init |
| Value Object | `DetectionSignals`, `ImageQuality`, `ActivityScore` | Immutable, dễ test |

### 9.3 DRY — Tránh duplicate

| Code cũ (duplicate) | Giải pháp |
|--------------------|-----------|
| Threading boilerplate trong YOLO và (sẽ có) Hands | `AsyncWorker` base class |
| JPEG encode ở nhiều nơi | `utils/image_utils.encode_jpeg()` |
| Duration format scatter | `utils/time_utils.format_duration()` |
| TTS calls scatter | `services/alert_service.py` |
| Magic numbers trong analyzer | Move hết vào `constants.py` group mới |

### 9.4 Constants — Không hardcode

**Rule:** Mọi số magic đều phải có tên constant trong `constants.py`.
Override bằng `.env` cho từng deployment.

```python
# BAD
if duration > 30:          # magic number
    capture()

# GOOD
if duration > HOMEWORK_DETECT_DURATION:
    capture()
```

---

## 10. Hướng dẫn cài đặt từng Phase

### 10.1 Phase 1 — Không cần model mới

```bash
# 1. Export YOLO sang ONNX (chạy 1 lần, ~2-5 phút)
cd /home/pi/ai-tutor
source venv/bin/activate
python3 scripts/export_onnx.py

# 2. Cài onnxruntime (nếu chưa có)
pip install onnxruntime

# 3. Chạy và kiểm tra FPS
./run.sh --debug-fps
```

**Verify:** FPS hiển thị ≥ 12fps, nhiệt độ < 75°C sau 30 phút.

### 10.2 Phase 2 — ✅ DONE (ConfidenceScorer, không cần cài thêm)

Phase 2 đã hoàn thành. Không cần cài model local (Moondream2 bị loại bỏ).

**Verify Phase 2:**
```bash
source venv/bin/activate
python3 -c "
from analyzers import ActivityAnalyzer, ConfidenceScorer, SignalBundle
aa = ActivityAnalyzer()
print('Phase 2 OK — ConfidenceScorer active')
"
```

### 10.3 Phase 3 — Homework Pipeline

```bash
# Tạo thư mục storage
mkdir -p /home/pi/ai-tutor/storage/captures

# Test quality checker
python3 scripts/test_quality.py --image test_images/homework.jpg
# Expected: blur_score=120.5, coverage=0.15, is_acceptable=True

# Test full homework flow (manual trigger)
./run.sh --test-homework
```

**Cấu hình server upload trong .env:**
```bash
HOMEWORK_SERVER_URL=https://your-server.com/api/homework
HOMEWORK_SERVER_API_KEY=your-key
HOMEWORK_AUTO_CAPTURE=true
HOMEWORK_VERIFIER_ENABLED=true
HOMEWORK_TTS_PROMPTS_ENABLED=true
```

### 10.4 Cập nhật setup.sh

```bash
# Thêm vào setup.sh các flags mới:
#   --with-local-ai    → cài moondream
#   --with-onnx        → export ONNX models
#   --with-storage     → tạo SQLite + captures dir
#   --with-audio       → cài whisper-cpp-python (Phase 4)
```

### 10.5 Cập nhật run.sh

```bash
#!/usr/bin/env bash
# Khởi động AI Tutor
cd "$(dirname "$0")"
source venv/bin/activate

# Pre-compile picamera2 bytecode nếu chưa có
PICAMERA_CACHE="/usr/lib/python3/dist-packages/picamera2/__pycache__"
if [ ! -d "$PICAMERA_CACHE" ]; then
    echo "Compiling picamera2 bytecode..."
    python3 -m compileall /usr/lib/python3/dist-packages/picamera2/ 2>/dev/null
fi

# Ưu tiên ONNX models nếu có
if [ -f "models/yolo26n.onnx" ]; then
    export YOLO_USE_ONNX=true
fi

python3 main.py "$@"
```

---

## 11. Constants & Configuration Reference

### 11.1 Groups hiện tại (1-18)
*(Xem `core/constants.py` — 18 groups hiện có)*

### 11.2 Groups đã thêm và cần thêm

**✅ Đã có (constants.py Group 19-21):**
```python
# ─── Group 19 — Image Quality Gate ──────────────────────────────
IMAGE_QUALITY_MIN_BLUR_SCORE  = 80.0   # Laplacian variance
IMAGE_QUALITY_MIN_COVERAGE    = 0.08   # Notebook ≥8% frame
IMAGE_QUALITY_MIN_BRIGHTNESS  = 40
IMAGE_QUALITY_MAX_BRIGHTNESS  = 220
JPEG_QUALITY                  = 90
SNAPSHOT_JPEG_QUALITY         = 95

# ─── Group 20 — YOLO ONNX ────────────────────────────────────────
YOLO_USE_ONNX                 = True
YOLO_ONNX_PROVIDERS           = ["CPUExecutionProvider"]
# ... (xem constants.py)

# ─── Group 21 — Confidence Scoring ───────────────────────────────
CONFIDENCE_MIN_CLASSIFY       = 30
CONFIDENCE_WRITING_THRESHOLD  = 50
CONFIDENCE_READING_THRESHOLD  = 40
CONFIDENCE_COMPUTER_THRESHOLD = 45
CONFIDENCE_PHONE_THRESHOLD    = 45
CONFIDENCE_FOCUSED_THRESHOLD  = 45
CONFIDENCE_WATCHING_THRESHOLD = 40
CONFIDENCE_TALKING_THRESHOLD  = 40
CONFIDENCE_EATING_THRESHOLD   = 40
CONFIDENCE_PLAYING_THRESHOLD  = 40
CONFIDENCE_DISTRACTED_THRESHOLD = 30
HOMEWORK_WRITING_MIN_SCORE    = 60   # + book/notepaper → homework_visible
```

**Cần thêm cho Phase 3 (server upload + TTS):**
```python
# ─── Group 22 — Homework Server Upload ───────────────────────────
HOMEWORK_SERVER_URL           = ""     # https://your-server.com/api/homework
HOMEWORK_SERVER_API_KEY       = ""
HOMEWORK_UPLOAD_TIMEOUT_S     = 30.0
HOMEWORK_UPLOAD_RETRY         = 2
HOMEWORK_MAX_IMAGE_SIZE_KB    = 2048   # Compress nếu > 2MB

# ─── Group 23 — TTS Messages ─────────────────────────────────────
TTS_DISTRACTED       = "{name} ơi, hãy tập trung vào bài học nhé!"
TTS_PHONE_ALERT      = "{name}, hãy cất điện thoại và tập trung học nào!"
TTS_SLEEPING_ALERT   = "{name} ơi! Tỉnh dậy và tiếp tục học nào!"
TTS_HOMEWORK_SHOW    = "Em có thể giơ bài tập lên cho thầy cô xem không?"
TTS_HOMEWORK_RETRY   = "Ảnh chưa rõ lắm, em giơ bài cao hơn và gần hơn nhé!"
TTS_HOMEWORK_OK      = "Cảm ơn em! Đang gửi bài tập lên phân tích..."
TTS_HOMEWORK_RESULT  = "Bài tập {subject} của em đạt {progress}%. {help}"
```

---

## 12. Benchmark & Performance Targets

### 12.1 Targets sau từng Phase

| Metric | Baseline | Phase 1 | Phase 2 ✅ | Phase 3 |
|--------|----------|---------|-----------|---------|
| Detection FPS | 6-7fps | **12-15fps** | ~7-9fps | ~7-9fps |
| Pipeline latency | ~150ms | **~65ms** | ~120ms | ~120ms |
| CPU usage (steady) | ~85% | **~60%** | ~85% | ~85% |
| Temperature (steady) | ~80°C | **~70°C** | ~80°C | ~80°C |
| Activity accuracy | ~75% | ~78% | **~88%** | ~90% |
| Homework trigger accuracy | ~65% | ~65% | **~85%** | **~92%** |
| RAM usage | ~4.2GB | ~4.4GB | ~4.3GB | ~4.4GB |

> **Lưu ý Phase 2:** Không dùng local AI model → RAM/CPU không thay đổi đáng kể.
> Performance gain sẽ đến từ Phase 1 (ONNX + async hand detector).

### 12.2 Test Cases cần verify trước khi sang Phase tiếp theo

**Phase 1 pass criteria:**
- [ ] FPS ≥ 12fps sustained sau 30 phút
- [ ] Nhiệt độ ≤ 75°C sau 30 phút
- [ ] Không có 1 activity false positive nào mới (regression test)
- [ ] YOLO ONNX output khớp với PyTorch output (diff < 0.01)

**Phase 2 pass criteria: ✅ DONE**
- [x] ConfidenceScorer thay thế 20-step binary waterfall
- [x] 10 ActivityClassifiers (Strategy Pattern, stateless)
- [x] SignalBundle frozen dataclass (HandSignals + GazeSignals + ObjectSignals)
- [x] `homework_visible` flag trong result dict
- [x] HomeworkMonitor.update() nhận `homework_visible` + auto-capture
- [x] Tests pass: writing, phone temporal filter, computer, absence

**Phase 3 pass criteria:**
- [ ] Homework capture tự động khi quality pass
- [ ] Ảnh upload có blur_score ≥ MIN_BLUR_SCORE
- [ ] Cloud AI nhận ảnh và trả về kết quả trong 30s
- [ ] TTS prompt nghe rõ ràng
- [ ] SQLite log đầy đủ session data

---

## Phụ lục A — Lý do không dùng Gemma local

| Model | RAM | Latency (RPi5) | Vấn đề |
|-------|-----|----------------|--------|
| Gemma 2B Q4 | ~3-4GB | 2-5s/response | Quá chậm cho verify |
| Gemma 2B Q8 | ~5-6GB | 5-10s/response | Chiếm gần hết RAM |
| Moondream2 int8 | ~2-3GB | 0.5-2s | Phù hợp: nhanh, nhẹ, vision |

**Kết luận:** Gemma chỉ phù hợp nếu cần chat/reasoning. Use case của chúng ta chỉ cần binary yes/no visual verify → Moondream2 là lựa chọn tốt hơn.

---

## Phụ lục B — Lý do không dùng Coral TPU

Coral TPU (Google Edge TPU) có thể tăng tốc TFLite models lên 10-30× nhưng:
- Yêu cầu compile model sang `.tflite` EdgeTPU format (không phải tất cả ops đều hỗ trợ)
- Giá ~$60-80 USD (Coral USB Accelerator)
- MediaPipe TFLite đã có backend native trên RPi5 (ARM Cortex-A76)
- Phase 1 ONNX optimization đã đủ target FPS

→ **Không cần thiết trong giai đoạn hiện tại.** Cân nhắc nếu cần scale lên ≥ 4 học sinh cùng lúc.

---

*Tài liệu này cần được cập nhật sau mỗi Phase hoàn thành.*
*Xem thêm: `docs/business/architecture.md`, `docs/business/activity-states.md`*
