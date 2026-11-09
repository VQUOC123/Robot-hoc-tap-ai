# Hướng dẫn cấu hình hệ thống

## Kiến trúc cấu hình

```
constants.py          .env                  Config class
(giá trị mặc định) ──► (override tuỳ môi  ──► (dùng trong code)
                        trường/deployment)
```

**Quy tắc ưu tiên**: `.env` > `constants.py`

- **Thay đổi nhanh / thay đổi mặc định**: sửa `core/constants.py`
- **Thay đổi theo môi trường** (staging/production khác nhau): thêm vào `.env`
- **Code không bao giờ hardcode** ngưỡng — luôn đọc qua `Config`

---

## Cách thay đổi cấu hình

### Cách 1: Sửa `core/constants.py` (khuyến nghị cho điều chỉnh lâu dài)
```python
# core/constants.py
ABSENCE_SHORT_THRESHOLD = 30   # Đổi từ 60s xuống 30s
ABSENCE_LONG_THRESHOLD  = 600  # Đổi từ 5 phút lên 10 phút
```

### Cách 2: Thêm vào `.env` (không cần sửa code)
```bash
# .env
ABSENCE_SHORT_THRESHOLD=30
ABSENCE_LONG_THRESHOLD=600
ROI_ENABLED=true
ROI_X1=0.2
ROI_X2=0.8
```

---

## Tất cả tham số cấu hình

### Nhóm 1: Camera & Stream

| Tham số | Mặc định | Đơn vị | Mô tả |
|---|---|---|---|
| `CAMERA_WIDTH` | 1280 | pixel | Chiều rộng frame |
| `CAMERA_HEIGHT` | 720 | pixel | Chiều cao frame |
| `CAMERA_FPS` | 30 | fps | Số frame/giây |
| `STREAM_HOST` | `0.0.0.0` | - | Địa chỉ lắng nghe web |
| `STREAM_PORT` | 5000 | port | Cổng web server |

**Điều chỉnh thực tế:**
- Giảm `CAMERA_FPS` xuống 15-20 nếu CPU RPi5 quá tải
- `STREAM_HOST=0.0.0.0` cho phép truy cập từ mạng LAN

---

### Nhóm 2: Phát hiện vắng mặt

| Tham số | Mặc định | Đơn vị | Mô tả |
|---|---|---|---|
| `ABSENCE_BUFFER_FRAMES` | 45 | frame | Frame liên tiếp không detect → bắt đầu tính vắng |
| `ABSENCE_SHORT_THRESHOLD` | 60 | giây | Ngưỡng "rời chỗ ngắn" |
| `ABSENCE_LONG_THRESHOLD` | 300 | giây | Ngưỡng "vắng mặt" chính thức |

**Sơ đồ phân loại vắng mặt:**
```
0s ──── BUFFER(1.5s) ──── SHORT(60s) ──── LONG(300s) ──────►
         ↑                   ↑                ↑
    Bắt đầu tính         "Rời chỗ          "Vắng mặt"
    thời gian             ngắn"
```

**Điều chỉnh theo use case:**
| Use case | SHORT | LONG |
|---|---|---|
| Lớp học nghiêm túc | 30s | 180s (3 phút) |
| Mặc định | 60s | 300s (5 phút) |
| Văn phòng linh hoạt | 120s | 600s (10 phút) |
| Ca học dài (3 tiếng) | 60s | 900s (15 phút) |

**Tại sao có `ABSENCE_BUFFER_FRAMES`?**
MediaPipe Pose đôi khi không detect được người trong 1-2 frame (đặc biệt khi nhiều người cùng hàng). Buffer 45 frame (~1.5 giây) giúp tránh false positive "vắng mặt" trong tình huống này.

---

### Nhóm 3: Phát hiện mất tập trung

| Tham số | Mặc định | Đơn vị | Mô tả |
|---|---|---|---|
| `DISTRACTION_DURATION` | 5 | giây | Giây nhìn sang nơi khác liên tiếp → "mất tập trung" |
| `ACTIVITY_SMOOTH_FRAMES` | 45 | frame | Cửa sổ smooth trạng thái |

**Lưu ý `DISTRACTION_DURATION`:**
- Nhìn thoáng qua < 5 giây: KHÔNG tính là mất tập trung (chỉ `present`)
- Nhìn liên tiếp ≥ 5 giây: chuyển sang `distracted`
- Tăng lên 8-10 giây nếu học sinh hay nhìn bảng/giáo viên (môi trường lớp học)
- Giảm xuống 3 giây nếu muốn phát hiện nhanh hơn

---

### Nhóm 4: Phát hiện điện thoại

| Tham số | Mặc định | Phạm vi | Mô tả |
|---|---|---|---|
| `PHONE_DETECTION_ENABLED` | `true` | true/false | Bật/tắt tính năng |
| `PHONE_SCORE_THRESHOLD` | 55 | 0-100 | Điểm tối thiểu để xét phone |
| `PHONE_SCORE_UPPER_THRESHOLD` | 40 | 0-100 | Điểm tối thiểu khi tay ở vùng upper |
| `PHONE_MAX_HAND_SPEED` | 15 | px/frame | Tốc độ tay tối đa khi xét phone |

**Cách tính phone score (trong HandDetector):**
```
Phone Score = Điểm vùng tay + Điểm tốc độ + Điểm số tay

Vùng tay:
  - middle zone  → +40 điểm
  - upper zone   → +30 điểm
  - bottom zone  → không xét (đang gõ phím)

Tốc độ:
  - < 5 px/frame  → +25 (đứng yên, đọc phone)
  - 5-15 px/frame → +20 (scroll nhẹ)
  - 15-25 px/frame → +10 (chuyển động trung bình)

Số tay:
  - 1 tay → +15 (cầm phone 1 tay phổ biến)
  - 2 tay → +5
```

**Quyết định cuối (trong ActivityAnalyzer):**
- Phone score ≥ 55 + Gaze `looking_down` → `using_phone`
- Phone score ≥ 55 + Gaze `looking_screen` + tay middle/upper + speed < 15 → `using_phone`
- Tay upper + Gaze `looking_down` + phone score ≥ 40 → `using_phone`

**Điều chỉnh:**
- Hay nhận nhầm đồ vật khác là phone: tăng `PHONE_SCORE_THRESHOLD` lên 65-70
- Khó phát hiện phone: giảm `PHONE_SCORE_THRESHOLD` xuống 45-50

---

### Nhóm 5: ROI — Vùng phân tích (phòng nhiều người)

| Tham số | Mặc định | Phạm vi | Mô tả |
|---|---|---|---|
| `ROI_ENABLED` | `false` | true/false | Bật/tắt ROI cropping |
| `ROI_X1` | 0.15 | 0.0–1.0 | Bắt đầu vùng phân tích (% chiều ngang) |
| `ROI_X2` | 0.85 | 0.0–1.0 | Kết thúc vùng phân tích (% chiều ngang) |
| `ROI_Y1` | 0.0 | 0.0–1.0 | Bắt đầu vùng phân tích (% chiều dọc) |
| `ROI_Y2` | 1.0 | 0.0–1.0 | Kết thúc vùng phân tích (% chiều dọc) |

**Khi nào bật ROI?**
- Camera thấy 2+ học sinh cùng hàng → hệ thống nhận nhầm người bên cạnh
- Bật `ROI_ENABLED=true` và điều chỉnh X1/X2 để chỉ bao gồm vị trí của học sinh cần theo dõi

**Ví dụ cấu hình ROI cho các vị trí ngồi:**
```
Camera nhìn thẳng, học sinh ở giữa frame:
  ROI_X1=0.2, ROI_X2=0.8

Học sinh ngồi lệch bên phải frame:
  ROI_X1=0.5, ROI_X2=1.0

Camera đặt cao, cần crop bớt phần trên:
  ROI_Y1=0.2, ROI_Y2=1.0
```

---

### Nhóm 6: Motion Detector

| Tham số | Mặc định | Phạm vi | Mô tả |
|---|---|---|---|
| `MOTION_THRESHOLD` | 20 | 5–50 | Độ nhạy phát hiện chuyển động |
| `MOTION_MIN_AREA` | 500 | 100–5000 | Diện tích tối thiểu (px²) của vùng chuyển động |

---

### Nhóm 7: Gaze Detector — Góc đầu

| Tham số | Mặc định | Đơn vị | Mô tả |
|---|---|---|---|
| `GAZE_PITCH_UP` | 20 | độ | Ngưỡng ngửa đầu → "nhìn lên" |
| `GAZE_PITCH_DOWN` | -15 | độ | Ngưỡng cúi đầu → "nhìn xuống" |
| `GAZE_YAW_THRESHOLD` | 20 | độ | Ngưỡng quay đầu trái/phải |
| `GAZE_ROLL_THRESHOLD` | 20 | độ | Ngưỡng nghiêng đầu → "buồn ngủ" |

```
                  looking_up
                  (pitch > 20°)
                      ↑
looking_left ←── looking_screen ──→ looking_right
(yaw > 20°)    (mặc định/trung tâm)  (yaw < -20°)
                      ↓
                  looking_down
                  (pitch < -15°)
```

**Điều chỉnh theo vị trí camera:**
- Camera đặt thấp hơn mặt: tăng `GAZE_PITCH_UP` lên 25-30
- Camera đặt cao hơn mặt: điều chỉnh `GAZE_PITCH_DOWN` xuống -20
- Học sinh hay nhìn màn hình phụ bên cạnh: tăng `GAZE_YAW_THRESHOLD` lên 25-30

---

### Nhóm 8: Hand Detector — Phân vùng tay

| Tham số | Mặc định | Phạm vi | Mô tả |
|---|---|---|---|
| `HAND_ZONE_UPPER_RATIO` | 0.30 | 0.1–0.5 | Ranh giới upper/middle (% chiều cao) |
| `HAND_ZONE_BOTTOM_RATIO` | 0.60 | 0.4–0.8 | Ranh giới middle/bottom (% chiều cao) |
| `HAND_SPEED_STILL` | 5 | px/frame | Tốc độ tối đa: "tay đứng yên" |
| `HAND_SPEED_TYPING_MAX` | 20 | px/frame | Tốc độ tối đa: "đang gõ phím" |
| `HAND_SPEED_READING` | 8 | px/frame | Tốc độ tối đa: "đang đọc" (vùng middle) |
| `HAND_SPEED_GESTURE_MAX` | 25 | px/frame | Tốc độ tối đa: "cử động tay" |
| `HAND_SPEED_FACE_MAX` | 10 | px/frame | Tốc độ tối đa: "tay gần mặt" |

```
Frame phân vùng tay:
┌─────────────────────────────────┐  y = 0%
│  UPPER ZONE  (y < 30%)          │ ← Đầu/mặt
│  Ngưỡng: HAND_ZONE_UPPER_RATIO  │
├─────────────────────────────────┤  y = 30%
│  MIDDLE ZONE (30% < y < 60%)    │ ← Ngực/lòng/điện thoại
│  Ngưỡng: HAND_ZONE_BOTTOM_RATIO │
├─────────────────────────────────┤  y = 60%
│  BOTTOM ZONE (y > 60%)          │ ← Bàn/bàn phím
└─────────────────────────────────┘  y = 100%
```

---

### Nhóm 9: Focus Scoring

| Tham số | Mặc định | Mô tả |
|---|---|---|
| `SCORE_SITTING` | 30 | Điểm khi đang ngồi |
| `SCORE_SITTING_GOOD` | 10 | Bonus khi ngồi đúng tư thế |
| `SCORE_STANDING` | 10 | Điểm khi đứng |
| `SCORE_GAZE_SCREEN` | 40 | Nhìn màn hình |
| `SCORE_GAZE_DOWN` | 30 | Nhìn xuống (đọc/viết) |
| `SCORE_GAZE_TILT` | 10 | Nghiêng đầu |
| `SCORE_GAZE_OTHER` | 5 | Nhìn hướng khác |
| `SCORE_HAND_TYPING` | 20 | Gõ phím |
| `SCORE_HAND_WRITING` | 20 | Viết bài |
| `SCORE_HAND_TYPING_PAUSE` | 15 | Tay nghỉ trên bàn phím |
| `SCORE_HAND_READING` | 15 | Tay nghỉ khi đọc |
| `SCORE_HAND_GESTURING` | 10 | Cử động tay |
| `SCORE_HAND_NONE` | 10 | Không thấy tay |
| `SCORE_HAND_FACE` | 5 | Tay gần mặt |
| `SCORE_HAND_ACTIVE` | 5 | Tay chuyển động nhiều |
| `SCORE_PENALTY_PHONE` | -30 | Trừ điểm: dùng điện thoại |
| `SCORE_PENALTY_DISTRACTION` | -20 | Trừ điểm: mất tập trung |

---

### Nhóm 10: Tutor & AI

| Tham số | Mặc định | Mô tả |
|---|---|---|
| `STUDENT_NAME` | `bạn` | Tên hiển thị trong tin nhắn AI |
| `DISTRACTION_THRESHOLD` | 10 | % thời gian mất tập trung → AI cảnh báo |
| `REMINDER_COOLDOWN` | 60 | Giây tối thiểu giữa 2 lần AI nhắc nhở |

---

## Ví dụ cấu hình theo môi trường

### Môi trường A: Phòng luyện thi nghiêm túc
```bash
# .env
ABSENCE_SHORT_THRESHOLD=30      # Cảnh báo sớm sau 30s
ABSENCE_LONG_THRESHOLD=180      # Vắng mặt sau 3 phút
DISTRACTION_DURATION=3          # Phát hiện mất tập trung nhanh hơn
PHONE_SCORE_THRESHOLD=50        # Nhạy hơn với phone
REMINDER_COOLDOWN=30            # Nhắc nhở thường xuyên hơn
```

### Môi trường B: Văn phòng coworking linh hoạt
```bash
# .env
ABSENCE_SHORT_THRESHOLD=120     # 2 phút rời chỗ là bình thường
ABSENCE_LONG_THRESHOLD=900      # Vắng mặt sau 15 phút mới ghi nhận
DISTRACTION_DURATION=10         # Nhìn xung quanh lâu hơn là bình thường
PHONE_DETECTION_ENABLED=false   # Không check điện thoại
```

### Môi trường C: Phòng nhiều học sinh cùng hàng
```bash
# .env
ROI_ENABLED=true
ROI_X1=0.2
ROI_X2=0.8
ABSENCE_BUFFER_FRAMES=60        # Buffer cao hơn để tránh false positive
```
