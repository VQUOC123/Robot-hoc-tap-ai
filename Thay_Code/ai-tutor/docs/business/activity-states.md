# Activity States — Trạng thái hoạt động

> File tham chiếu cho toàn bộ trạng thái hệ thống detect được.
> Constants định nghĩa tại: `core/constants.py` (Nhóm 15)
> Logic điều kiện tại: `analyzers/activity_analyzer.py::_determine_raw_activity()`

---

## Sơ đồ ưu tiên phát hiện (theo thứ tự từ trên xuống)

```
Frame đến
    │
    ├─ person_present = False → briefly_away / absent
    │
    ├─ is_phone = True        → using_phone
    │
    ├─ distraction_seconds ≥ DISTRACTION_DURATION (5s)
    │    + gaze: left/right/up → distracted
    │
    ├─ YOLO thấy keyboard/mouse + tay typing/pause
    │    + gaze: screen/down/up  → working_computer  ◄─ ưu tiên cao nhất khi làm việc máy
    │
    ├─ YOLO thấy monitor/laptop + gaze: screen/down
    │    + tay typing/pause      → working_computer
    │    + tay khác              → watching_screen
    │
    ├─ YOLO thấy book + gaze: down + tay: no/reading/pause → reading
    │
    ├─ tay typing/pause + gaze: screen/down/up → working_computer
    │
    ├─ tay gesturing + gaze: screen → focused_studying
    │
    ├─ tay writing + gaze: down   → writing_notes
    │
    ├─ gaze: down + tay: no/reading/pause + KHÔNG có screen → reading
    │
    ├─ gaze: screen               → watching_screen
    │
    ├─ gaze: left/right/up
    │    + distraction_seconds ≥ 2s → distracted (nhẹ)
    │    + < 2s                     → present (nhìn quanh)
    │
    ├─ gaze: head_tilt            → drowsy
    │
    └─ mặc định                   → present
```

---

## Chi tiết từng trạng thái

### Nhóm 1: Tập trung làm việc / học tập

#### `working_computer` — Làm việc trên máy tính
- **Constant**: `ACTIVITY_WORKING_COMPUTER` / `STATUS_WORKING_COMPUTER`
- **Điều kiện** (3 trường hợp, ưu tiên theo thứ tự):
  1. **YOLO keyboard/mouse** + tay `typing`/`typing_pause` + gaze `screen`/`down`/`up`
  2. **YOLO monitor/laptop** + tay `typing`/`typing_pause` + gaze `screen`/`down`
  3. **Chỉ hand detector** (không cần YOLO): tay `typing`/`typing_pause` + gaze `screen`/`down`/`up`
- **Ghi chú**: `looking_up` được chấp nhận vì màn hình có thể đặt cao hơn mắt
- **Gaze chấp nhận**: `looking_screen`, `looking_down`, `looking_up`
- **Hand chấp nhận**: `typing`, `typing_pause`
- **Focus score**: ~80–100

#### `focused_studying` — Tập trung học tập (gesture)
- **Constant**: `ACTIVITY_FOCUSED_STUDYING` / `STATUS_FOCUSED_STUDYING`
- **Điều kiện**: tay `gesturing` + gaze `looking_screen`
- **Ghi chú**: Cử động tay trên màn hình (chỉ vào, giải thích...) — `typing` đã được bắt trước bởi `working_computer`
- **Focus score**: ~70–90

#### `writing_notes` — Viết bài / Ghi chép
- **Constant**: `ACTIVITY_WRITING_NOTES` / `STATUS_WRITING_NOTES`
- **Điều kiện**: tay `writing` + gaze `looking_down`
- **Ghi chú**: `writing` = tay ở vùng bottom, tốc độ > `HAND_SPEED_TYPING_MAX` (20 px/frame)
- **Focus score**: ~70–90

#### `reading` — Đọc sách / Tài liệu
- **Constant**: `ACTIVITY_READING` / `STATUS_READING`
- **Điều kiện** (2 trường hợp):
  1. **YOLO book boost**: YOLO thấy sách + gaze `looking_down` + tay `no_hands`/`reading_gesture`/`typing_pause`
  2. **General**: gaze `looking_down` + tay `no_hands`/`reading_gesture`/`typing_pause` **+ KHÔNG có màn hình** (`has_screen=False`)
- **Ghi chú quan trọng**: `has_screen=False` bắt buộc ở trường hợp 2 để tránh nhầm với người làm việc máy tính khi tay không detect được từ góc camera
- **Focus score**: ~60–80

#### `watching_screen` — Xem màn hình / Suy nghĩ
- **Constant**: `ACTIVITY_WATCHING_SCREEN` / `STATUS_WATCHING_SCREEN`
- **Điều kiện** (2 trường hợp):
  1. YOLO thấy màn hình + gaze `screen`/`down` + tay KHÔNG typing
  2. gaze `looking_screen` (không có YOLO)
- **Focus score**: ~60–75

---

### Nhóm 2: Mất tập trung

#### `distracted` — Mất tập trung
- **Constant**: `ACTIVITY_DISTRACTED` / `STATUS_FMT_DISTRACTED` (format string)
- **Điều kiện**: gaze `looking_left`/`looking_right`/`looking_up` liên tục ≥ `DISTRACTION_DURATION` giây
- **Ngưỡng điều chỉnh**: `DISTRACTION_DURATION` trong `constants.py` (mặc định 5s)
- **Phiên bản nhẹ**: gaze nhìn sang + 2–5s → `STATUS_FMT_DISTRACTED_SHORT`
- **Focus score**: ~20–40

#### `using_phone` — Dùng điện thoại
- **Constant**: `ACTIVITY_USING_PHONE` / `STATUS_USING_PHONE`
- **Điều kiện** (kết hợp nhiều tín hiệu trong `_detect_phone()`):
  - YOLO thấy phone + gaze `down`/`screen` → phone trên bàn
  - phone_score ≥ `PHONE_SCORE_THRESHOLD` (55) + gaze `down` → cầm phone nhìn xuống
  - phone_score ≥ 55 + gaze `screen` + tay `middle`/`upper` + speed < `PHONE_MAX_HAND_SPEED` (15) → cầm phone ngang mặt
  - tay `upper` + gaze `down` + phone_score ≥ `PHONE_SCORE_UPPER_THRESHOLD` (40) → cầm phone lên cao
- **Focus score**: ~20–35

#### `drowsy` — Buồn ngủ / Mệt mỏi
- **Constant**: `ACTIVITY_DROWSY` / `STATUS_DROWSY`
- **Điều kiện**: gaze `head_tilt` (góc roll > `GAZE_ROLL_THRESHOLD`, mặc định 20°)
- **Focus score**: ~30–45

---

### Nhóm 3: Vắng mặt

#### `briefly_away` — Rời khỏi vị trí tạm thời
- **Constant**: `ACTIVITY_BRIEFLY_AWAY` / `STATUS_FMT_BRIEFLY_AWAY_SHORT` / `STATUS_FMT_BRIEFLY_AWAY_MED`
- **Điều kiện**: `person_present=False` sau ≥ `ABSENCE_BUFFER_FRAMES` (45) frame liên tiếp

| Thời gian | Template | Ý nghĩa |
|---|---|---|
| 0 – `ABSENCE_SHORT_THRESHOLD` (60s) | `STATUS_FMT_BRIEFLY_AWAY_SHORT` | Vừa rời đi |
| 60s – `ABSENCE_LONG_THRESHOLD` (300s) | `STATUS_FMT_BRIEFLY_AWAY_MED` | Rời chỗ ngắn |

- **Ngưỡng điều chỉnh**: `ABSENCE_SHORT_THRESHOLD`, `ABSENCE_LONG_THRESHOLD`, `ABSENCE_BUFFER_FRAMES`
- **Focus score**: 0 (không smooth — cập nhật ngay lập tức)

#### `absent` — Vắng mặt chính thức
- **Constant**: `ACTIVITY_ABSENT` / `STATUS_FMT_ABSENT`
- **Điều kiện**: `person_present=False` ≥ `ABSENCE_LONG_THRESHOLD` giây (mặc định 300s = 5 phút)
- **Focus score**: 0 (không smooth)

---

### Nhóm 4: Có mặt chưa xác định

#### `present` — Có mặt
- **Constant**: `ACTIVITY_PRESENT` / `STATUS_PRESENT` / `STATUS_LOOKING_AROUND`
- **Điều kiện**: phát hiện người nhưng không thỏa bất kỳ điều kiện nào ở trên
- **Focus score**: ~35–50

---

## Điểm tập trung (Focus Score 0–100)

Tính trong `_calc_focus_score()`. Constants trong `constants.py` (Nhóm 9: `SCORE_*`).

```
Focus Score = Điểm tư thế + Điểm gaze + Điểm tay − Điểm trừ
```

| Nguồn | Tình huống | Điểm | Constant |
|---|---|---|---|
| **Tư thế** | Ngồi | +30 | `SCORE_SITTING` |
| | Ngồi thẳng (bonus) | +10 | `SCORE_SITTING_GOOD` |
| | Đứng | +10 | `SCORE_STANDING` |
| **Gaze** | Nhìn màn hình | +40 | `SCORE_GAZE_SCREEN` |
| | Nhìn xuống | +30 | `SCORE_GAZE_DOWN` |
| | Nghiêng đầu | +10 | `SCORE_GAZE_TILT` |
| | Nhìn lên/trái/phải | +5 | `SCORE_GAZE_OTHER` |
| **Tay** | Gõ phím | +20 | `SCORE_HAND_TYPING` |
| | Viết bài | +20 | `SCORE_HAND_WRITING` |
| | Tay nghỉ trên bàn phím | +15 | `SCORE_HAND_TYPING_PAUSE` |
| | Tay nghỉ khi đọc | +15 | `SCORE_HAND_READING` |
| | Cử động tay | +10 | `SCORE_HAND_GESTURING` |
| | Không thấy tay | +10 | `SCORE_HAND_NONE` |
| | Tay gần mặt | +5 | `SCORE_HAND_FACE` |
| | Tay chuyển động nhiều | +5 | `SCORE_HAND_ACTIVE` |
| **Trừ** | Dùng điện thoại | −30 | `SCORE_PENALTY_PHONE` |
| | Mất tập trung kéo dài | −20 | `SCORE_PENALTY_DISTRACTION` |

---

## Smoothing

- Cửa sổ smooth: `ACTIVITY_SMOOTH_FRAMES` frame (mặc định 45, ≈ 1.5 giây ở 30fps)
- Cơ chế: lấy trạng thái **phổ biến nhất** trong cửa sổ (Counter.most_common)
- Trạng thái KHÔNG smooth: `absent`, `briefly_away` (cập nhật ngay lập tức)
- Bắt đầu smooth: sau ≥ 15 frame có dữ liệu

---

## Thêm trạng thái mới

1. Thêm vào `core/constants.py` (Nhóm 15):
   ```python
   ACTIVITY_MY_NEW_STATE = "my_new_state"
   STATUS_MY_NEW_STATE   = "🆕 Trạng thái mới"
   ```

2. Thêm logic vào `analyzers/activity_analyzer.py::_determine_raw_activity()`:
   ```python
   if <điều kiện>:
       return C.ACTIVITY_MY_NEW_STATE, C.STATUS_MY_NEW_STATE
   ```
   Chú ý: thứ tự if-elif quan trọng — trạng thái ưu tiên cao hơn phải đặt trước.

3. Cập nhật file này với điều kiện và mô tả mới.

---

## Nguồn tín hiệu đầu vào

| Tín hiệu | Nguồn | Giá trị khả dụng |
|---|---|---|
| `gaze` | FaceDetector (Landmarker/Pose) | `looking_screen`, `looking_down`, `looking_up`, `looking_left`, `looking_right`, `head_tilt`, `unknown` |
| `hand_activity` | HandDetector | `typing`, `typing_pause`, `writing`, `reading_gesture`, `gesturing`, `no_hands`, `face_touch`, `active_hands`, `possible_phone`, `distracted_hands` |
| `hand_zone` | HandDetector | `bottom` (bàn phím), `middle` (lòng), `upper` (đầu), `none` |
| `has_keyboard` | YOLO hoặc inferred từ `typing` | bool |
| `has_mouse` | YOLO | bool |
| `has_screen` | YOLO (monitor + laptop) | bool |
| `has_book` | YOLO | bool |
| `has_phone` | YOLO | bool |
| `distraction_seconds` | GazeDetector tracking | số giây liên tiếp |
| `person_present` | Pose/YOLO | bool |
| `absence_level` | PersonSession | `present`, `briefly_away`, `absent` |
