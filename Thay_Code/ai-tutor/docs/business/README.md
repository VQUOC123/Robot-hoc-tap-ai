# Tài liệu nghiệp vụ — AI Tutor / Hệ thống giám sát tập trung

Thư mục này chứa tài liệu mô tả toàn bộ hệ thống từ góc nhìn **nghiệp vụ và kỹ thuật**.
Dùng làm context cho phát triển, bảo trì, và onboarding thành viên mới.

---

## Danh sách tài liệu

| File | Nội dung |
|---|---|
| [overview.md](overview.md) | Tổng quan hệ thống, mục tiêu, use cases, công nghệ |
| [activity-states.md](activity-states.md) | Tất cả trạng thái hoạt động, điều kiện phát hiện, focus scoring |
| [configuration.md](configuration.md) | Hướng dẫn cấu hình đầy đủ, tất cả tham số và cách điều chỉnh |
| [architecture.md](architecture.md) | Kiến trúc hệ thống, luồng dữ liệu, chi tiết từng module |
| [hardware-setup.md](hardware-setup.md) | Lắp đặt phần cứng, vị trí camera, hiệu chỉnh, troubleshooting |

---

## Đọc nhanh theo mục đích

### Muốn hiểu hệ thống làm gì?
→ Đọc [overview.md](overview.md)

### Muốn hiểu hệ thống phân loại hành vi như thế nào?
→ Đọc [activity-states.md](activity-states.md)

### Muốn thay đổi ngưỡng (vắng mặt, mất tập trung, điện thoại...)?
→ Đọc [configuration.md](configuration.md)
→ Sửa `core/constants.py` hoặc thêm vào `.env`

### Muốn hiểu code hoạt động như thế nào?
→ Đọc [architecture.md](architecture.md)

### Muốn lắp đặt camera và thiết bị?
→ Đọc [hardware-setup.md](hardware-setup.md)

---

## Trạng thái hoạt động nhanh

| Activity | Ý nghĩa | Focus |
|---|---|---|
| `working_computer` | Làm việc máy tính | 80–100 |
| `focused_studying` | Học trên máy tính | 70–90 |
| `writing_notes` | Viết bài / Ghi chép | 70–90 |
| `reading` | Đọc sách / Tài liệu | 60–80 |
| `watching_screen` | Xem màn hình / Suy nghĩ | 60–75 |
| `using_phone` | Dùng điện thoại | 20–35 |
| `distracted` | Mất tập trung | 20–40 |
| `drowsy` | Buồn ngủ / Mệt | 30–45 |
| `briefly_away` | Rời chỗ tạm thời (< 5 phút) | 0 |
| `absent` | Vắng mặt (≥ 5 phút) | 0 |
| `present` | Có mặt, chưa rõ hoạt động | 35–50 |

---

## Các file cấu hình quan trọng

| File | Mục đích |
|---|---|
| `core/constants.py` | **Tất cả ngưỡng mặc định** — sửa tại đây để thay đổi hành vi hệ thống |
| `core/config.py` | Đọc `.env`, fallback về `constants.py` — thường không cần sửa |
| `.env` | Override theo môi trường — API keys, tham số tuỳ chỉnh per-deployment |

---

## Lịch sử phát triển

| Phiên bản | Thay đổi chính |
|---|---|
| v1 | Camera loop cơ bản + MediaPipe Pose + Gaze + Hands |
| v2 | Thêm ActivityAnalyzer tổng hợp, focus scoring, Flask stream |
| v3 | Absence buffer, ROI crop, phone detection, activity smoothing |
| v4 | DrowsinessTracker, HomeworkMonitor, YOLO dual-model, pen grip detection |
| v5 | FaceDetector Strategy Pattern, phone temporal filter v3, pen/writing 3-layer protection |
| **v6 (kế hoạch)** | ONNX + Async Hands + Moondream2 + ConfidenceScorer + HomeworkService + SQLite |

---

## Kế hoạch phát triển

→ Xem [`../plan/REFACTOR_PLAN.md`](../plan/REFACTOR_PLAN.md) để biết chi tiết 5 phases.
