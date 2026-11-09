# Kiến trúc hệ thống

## Tổng quan luồng dữ liệu

```
Camera (30 FPS)
    │
    ▼ frame_rgb (1280×720, RGB888)
┌───────────────────────────────────────────────────────┐
│                    Camera Loop                        │
│  (thread riêng, daemon=True)                         │
│                                                       │
│  [ROI Crop] ← nếu ROI_ENABLED=true                   │
│       │                                               │
│       ▼                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │HandDetector │  │GazeDetector │  │PoseDetector │   │
│  │             │  │             │  │             │   │
│  │ MediaPipe   │  │ MediaPipe   │  │ MediaPipe   │   │
│  │ Hands       │  │ FaceMesh    │  │ Pose        │   │
│  │             │  │             │  │             │   │
│  │ → activity  │  │ → direction │  │ → presence  │   │
│  │ → zone      │  │ → pitch/yaw │  │ → posture   │   │
│  │ → speed     │  │ → roll      │  │ → absence   │   │
│  │ → phone_sc. │  │ → dist_secs │  │   _level    │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │           │
│         └────────────────┴────────────────┘           │
│                          │                            │
│                          ▼                            │
│               ┌──────────────────┐                    │
│               │ ActivityAnalyzer │                    │
│               │                  │                    │
│               │ 1. phone detect  │                    │
│               │ 2. focus score   │                    │
│               │ 3. raw activity  │                    │
│               │ 4. smoothing     │                    │
│               │                  │                    │
│               │ → final_activity │                    │
│               │ → focus_score    │                    │
│               │ → final_status   │                    │
│               └────────┬─────────┘                    │
│                        │                              │
│               current_data dict                       │
└───────────────────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
  StreamModule (Flask)            Terminal log
  ├── /           (dashboard)     (1 dòng, \r overwrite)
  ├── /video_feed (MJPEG)
  ├── /status     (JSON)
  ├── /stats      (JSON)
  ├── /absence_log(JSON)
  └── /chat       (POST → AI)
```

---

## Cấu trúc thư mục

```
/home/pi/ai-tutor/
│
├── main.py                     # Entry point, orchestration, camera loop
│
├── core/
│   ├── __init__.py             # Export: Config, constants
│   ├── config.py               # Đọc .env, fallback về constants
│   └── constants.py            # Tất cả ngưỡng mặc định (có comment)
│
├── camera/
│   ├── __init__.py
│   ├── camera_module.py        # Picamera2 wrapper
│   └── stream_module.py        # Flask server (MJPEG + REST API)
│
├── detectors/
│   ├── __init__.py
│   ├── pose_detector.py        # MediaPipe Pose → tư thế + vắng mặt
│   ├── gaze_detector.py        # MediaPipe FaceMesh → hướng nhìn
│   ├── hand_detector.py        # MediaPipe Hands → hoạt động tay + phone score
│   └── motion_detector.py      # OpenCV frame diff → motion level
│
├── analyzers/
│   ├── __init__.py
│   └── activity_analyzer.py   # Tổng hợp → final_activity + focus_score
│
├── ai/
│   ├── __init__.py
│   └── ai_module.py            # Multi-provider LLM (OpenAI/Claude/Gemini)
│
├── audio/
│   ├── __init__.py
│   ├── tts_module.py           # Text-to-speech (gTTS + espeak fallback)
│   └── stt_module.py           # Speech-to-text (placeholder)
│
├── web/
│   └── templates/
│       └── index.html          # Dashboard UI
│
├── docs/
│   └── business/               # Tài liệu nghiệp vụ (thư mục này)
│
├── logs/                       # Log files
├── requirements.txt
└── .env                        # API keys + config override
```

---

## Chi tiết từng module

### `main.py` — Orchestration
**Nhiệm vụ:**
- Khởi tạo tất cả modules
- Chạy camera loop trong thread riêng
- Chạy Flask server trong thread riêng
- Chia sẻ `current_data` dict giữa các thread

**ROI flow (khi `ROI_ENABLED=true`):**
```python
frame_rgb, frame_bgr = camera.capture()
roi_rgb, roi_bgr, roi_rect = _apply_roi(frame_rgb, frame_bgr)
roi_bgr = hands.detect(roi_rgb, roi_bgr)
roi_bgr = gaze.detect(roi_rgb, roi_bgr)
roi_bgr = pose.detect(roi_rgb, roi_bgr)
frame_bgr[y1:y2, x1:x2] = roi_bgr  # Ghi ngược kết quả
```

---

### `detectors/pose_detector.py` — Phát hiện tư thế & vắng mặt
**Input:** frame_rgb, frame_bgr
**Output (result dict):**
```python
{
    "person_present"  : bool,
    "sitting"         : bool,
    "status"          : str,        # Text hiển thị
    "absent_duration" : int,        # Giây kể từ khi rời đi
    "absence_level"   : str,        # "present" | "briefly_away" | "absent"
    "posture"         : str,        # "sitting_good" | "slouching" | ...
    "shoulder_level"  : float,      # Tỷ lệ vị trí vai trong frame
    "absence_count"   : int,        # Số lần vắng mặt trong phiên
    "absence_log"     : list,       # 5 lần vắng mặt gần nhất
}
```

**Absence buffer logic:**
```
Frame không detect người:
  _absence_buffer_count += 1
  if count < ABSENCE_BUFFER_FRAMES (45):
      → Giữ trạng thái cũ (tránh false positive)
  else:
      → _handle_absence() → cập nhật absent_duration và absence_level
```

**Phân loại absence_level:**
- `present`: person_present = True
- `briefly_away`: absent_duration < ABSENCE_LONG_THRESHOLD
- `absent`: absent_duration >= ABSENCE_LONG_THRESHOLD

---

### `detectors/gaze_detector.py` — Phát hiện hướng nhìn
**Input:** frame_rgb
**Output (result dict):**
```python
{
    "face_detected"       : bool,
    "gaze_direction"      : str,    # "looking_screen" | "looking_down" | ...
    "status"              : str,
    "pitch"               : float,  # Góc cúi/ngửa đầu (độ)
    "yaw"                 : float,  # Góc quay trái/phải (độ)
    "roll"                : float,  # Góc nghiêng đầu (độ)
    "distraction_seconds" : int,    # Giây liên tiếp nhìn sang hướng khác
}
```

**Landmark MediaPipe FaceMesh được dùng:**
- Điểm 1 (nose), 152 (chin), 10 (forehead): tính pitch
- Điểm 234 (left ear), 454 (right ear): tính yaw
- Điểm 33 (left eye), 263 (right eye): tính roll

**Bảng phân loại gaze:**
| Điều kiện | Kết quả |
|---|---|
| pitch > GAZE_PITCH_UP (20°) | `looking_up` |
| pitch < GAZE_PITCH_DOWN (-15°) | `looking_down` |
| yaw > GAZE_YAW_THRESHOLD (20°) | `looking_left` |
| yaw < -GAZE_YAW_THRESHOLD (-20°) | `looking_right` |
| \|roll\| > GAZE_ROLL_THRESHOLD (20°) | `head_tilt` |
| else | `looking_screen` |

---

### `detectors/hand_detector.py` — Phát hiện hoạt động tay
**Input:** frame_rgb
**Output (result dict):**
```python
{
    "hand_count"  : int,    # 0, 1, hoặc 2
    "activity"    : str,    # "typing" | "writing" | "possible_phone" | ...
    "status"      : str,
    "speed"       : float,  # Tốc độ trung bình tay (px/frame, 15-frame window)
    "positions"   : list,   # [(x, y), ...] vị trí cổ tay
    "zone"        : str,    # "bottom" | "middle" | "upper" | "none"
    "phone_score" : int,    # 0-100, smoothed over 30 frames
}
```

**Phone score calculation:**
```
score = zone_score + speed_score + hand_count_score
      = (40 nếu middle / 30 nếu upper)
      + (25 nếu speed<5 / 20 nếu 5-15 / 10 nếu 15-25)
      + (15 nếu 1 tay / 5 nếu 2 tay)
= max 80 điểm thô
→ smooth bằng trung bình 30 frame gần nhất
```

**Activity classification theo zone + speed:**
| Zone | Speed | Activity |
|---|---|---|
| bottom | < 5 | `typing_pause` |
| bottom | 5–20 | `typing` |
| bottom | > 20 | `writing` |
| middle | phone_score ≥ 55 | `possible_phone` |
| middle | < 8 | `reading_gesture` |
| middle | 8–25 | `gesturing` |
| middle | > 25 | `active_hands` |
| upper | phone_score ≥ 40 | `possible_phone` |
| upper | < 10 | `face_touch` |
| upper | > 10 | `distracted_hands` |

---

### `analyzers/activity_analyzer.py` — Tổng hợp & quyết định
**Input:** hand_info, gaze_info, pose_info
**Output:**
```python
{
    "final_status"   : str,     # Text hiển thị trên dashboard
    "final_activity" : str,     # Activity code (xem activity-states.md)
    "focus_score"    : int,     # 0-100
    "details"        : {
        "hand"        : str,
        "gaze"        : str,
        "pose"        : str,
        "phone"       : str,    # "" hoặc "📱 Score: X%"
        "distraction" : str,    # "" hoặc "⚠️ Mất TT: Xs"
    },
    "session_time"   : int,     # Giây từ khi khởi động
    "is_phone"       : bool,
    "distraction_s"  : int,
    "absence_level"  : str,
}
```

**Decision tree:**
```
person_present?
├── False → _classify_absence(absent_duration, absence_level)
│           ├── absent_duration >= LONG → "absent"
│           ├── absent_duration >= SHORT → "briefly_away" (rời chỗ ngắn)
│           └── else → "briefly_away" (vừa rời đi)
│
└── True →
    is_phone? → "using_phone"
    distraction_seconds >= DISTRACTION_DURATION AND gaze in [left/right/up]?
        → "distracted"
    (typing/typing_pause) AND looking_screen?
        → "working_computer"
    (typing/typing_pause/gesturing) AND looking_screen?
        → "focused_studying"
    writing AND looking_down?
        → "writing_notes"
    looking_down AND (no_hands/reading_gesture/typing_pause)?
        → "reading"
    looking_screen?
        → "watching_screen"
    looking_left/right/up AND distraction_seconds >= 2?
        → "distracted"
    head_tilt?
        → "drowsy"
    else → "present"
```

---

## Threading model

```
Main thread
├── Khởi tạo tất cả modules
├── Start camera_loop thread (daemon)
├── Start stream.run thread (daemon)
└── Loop: time.sleep(1) [giữ process sống]

camera_loop thread (daemon)
├── Capture frame (~30 FPS)
├── [ROI crop nếu enabled]
├── hands.detect() → vẽ overlay + cập nhật result
├── gaze.detect()  → vẽ overlay + cập nhật result
├── pose.detect()  → vẽ overlay + cập nhật result
├── analyzer.analyze() → final activity
├── Cập nhật current_data (shared dict)
├── stream.update_frame() → gửi frame cho MJPEG
└── Print terminal log

stream thread (daemon)
├── Flask /         → render dashboard HTML
├── Flask /video_feed → đọc current_frame → encode JPEG → stream
├── Flask /status   → return current_data as JSON
├── Flask /stats    → return analyzer.get_stats() as JSON
├── Flask /absence_log → return pose.absence_log as JSON
└── Flask /chat     → gọi AI module → trả về response
```

---

## Data flow giữa các class

```
Config (singleton class)
  ↓ đọc bởi
PoseDetector.__init__()
GazeDetector.__init__()
HandDetector.__init__()
ActivityAnalyzer.__init__()
StreamModule.__init__()
  ↓
Tất cả dùng cùng ngưỡng từ Config
  (Config đọc từ .env, fallback về constants.py)
```

---

## Lưu ý hiệu năng trên Raspberry Pi 5

| Module | Mô hình | Thời gian/frame (ước tính) |
|---|---|---|
| PoseDetector | MediaPipe Pose (complexity=0) | 15–30 ms |
| GazeDetector | MediaPipe FaceMesh | 10–20 ms |
| HandDetector | MediaPipe Hands | 15–25 ms |
| ActivityAnalyzer | Rule-based (Python) | < 1 ms |
| JPEG encode | OpenCV | 2–5 ms |
| **Tổng** | | **~40–80 ms → 12–25 FPS** |

**Tối ưu hóa nếu FPS thấp:**
1. Giảm `CAMERA_FPS` xuống 15
2. Giảm `CAMERA_WIDTH/HEIGHT` xuống 960×540
3. Tắt một detector nếu không cần (`PHONE_DETECTION_ENABLED=false`)
4. Bật ROI để xử lý vùng nhỏ hơn
