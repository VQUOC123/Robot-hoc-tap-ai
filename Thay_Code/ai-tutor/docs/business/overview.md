# Tổng quan hệ thống AI Tutor / Giám sát Tập trung

## Mục tiêu

Hệ thống sử dụng **Raspberry Pi 5** và **Camera Raspberry Pi v2.1** để tự động quan sát, phân tích và ghi nhận mức độ tập trung của học sinh / nhân viên trong phòng học hoặc văn phòng — mà không cần cài đặt phần mềm trên máy tính của người được quan sát.

---

## Đối tượng sử dụng

| Đối tượng | Bối cảnh | Ghi chú |
|---|---|---|
| **Trung tâm đào tạo** | Phòng học, phòng luyện thi | Camera đặt phía trước học sinh |
| **Doanh nghiệp** | Văn phòng làm việc, coworking | Giám sát năng suất làm việc |
| **Lớp học trực tiếp** | Phòng máy tính, phòng thực hành | Nhiều học sinh cùng hàng |
| **Phòng tự học** | Thư viện, study room | Tự đánh giá mức độ tập trung |

---

## Các trường hợp sử dụng chính

### 1. Giám sát học sinh tại trung tâm đào tạo
- Phát hiện học sinh đang tập trung học (nhìn màn hình, gõ phím, đọc sách)
- Phát hiện học sinh đang dùng điện thoại
- Cảnh báo khi học sinh vắng mặt quá 5 phút
- Ghi nhận lịch sử vắng mặt trong phiên học

### 2. Giám sát nhân viên tại văn phòng
- Xác nhận nhân viên đang làm việc trên máy tính
- Phát hiện mất tập trung (nhìn xung quanh lâu, dùng điện thoại)
- Báo cáo điểm tập trung theo thời gian thực

### 3. Hỗ trợ AI Tutor
- Tự động nhắc nhở học sinh khi mất tập trung
- Gợi ý nghỉ ngơi khi phát hiện có thể buồn ngủ
- Tương tác qua giọng nói (TTS) với ngữ cảnh từ camera

---

## Những gì hệ thống CÓ THỂ phát hiện

| Hành vi | Phương pháp |
|---|---|
| Tập trung làm việc trên máy tính | Gaze (nhìn màn hình) + Hand (gõ phím) |
| Đọc sách / tài liệu | Gaze (nhìn xuống) + Hand (tay nghỉ) |
| Viết bài / ghi chép | Gaze (nhìn xuống) + Hand (cử động nhanh vùng bàn) |
| Dùng điện thoại | Hand zone (giữa/trên) + Gaze (xuống) + Phone score |
| Mất tập trung | Gaze (nhìn sang nơi khác liên tiếp > 5 giây) |
| Buồn ngủ / mệt mỏi | Gaze (nghiêng đầu kéo dài) |
| Rời chỗ ngắn (< 5 phút) | Pose (không detect người > 1.5 giây) |
| Vắng mặt (>= 5 phút) | Pose (không detect người > 5 phút) |

## Những gì hệ thống CHƯA phát hiện

- Phân biệt nói chuyện với người khác vs. tự nói (cần thêm audio)
- Nhận dạng danh tính cụ thể (không có face recognition)
- Theo dõi nhiều người trong cùng một camera cùng lúc (1 camera = 1 vị trí)
- Nội dung trên màn hình (không có screen capture)

---

## Kiến trúc phần cứng

```
┌─────────────────────────────────────────────────────┐
│                  Raspberry Pi 5                      │
│                                                      │
│  Camera v2.1 ──► Picamera2 ──► Frame RGB (1280×720) │
│                                    │                 │
│                          ┌─────────┴──────────┐      │
│                          │   Detectors        │      │
│                          │  ├ PoseDetector    │      │
│                          │  ├ GazeDetector    │      │
│                          │  └ HandDetector    │      │
│                          └─────────┬──────────┘      │
│                                    │                 │
│                          ActivityAnalyzer            │
│                                    │                 │
│                    ┌───────────────┴─────────────┐   │
│                    │  Flask Web Server :5000      │   │
│                    │  - MJPEG stream              │   │
│                    │  - Dashboard HTML            │   │
│                    │  - REST API /status          │   │
│                    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
           │
           └──► Truy cập qua mạng LAN: http://<pi-ip>:5000
```

---

## Yêu cầu phần cứng tối thiểu

| Thành phần | Yêu cầu | Ghi chú |
|---|---|---|
| Board | Raspberry Pi 5 | RPi 4 cũng hoạt động, FPS thấp hơn |
| Camera | Raspberry Pi Camera v2.1 (IMX219) | Hoặc camera tương thích Picamera2 |
| RAM | 4 GB | 8 GB khuyến nghị cho đa luồng |
| Storage | 16 GB microSD | Class 10 trở lên |
| OS | Raspberry Pi OS (Bookworm) | 64-bit |
| Nguồn | 5V / 3A (USB-C) | Chính thức từ Raspberry Pi |

---

## Công nghệ sử dụng

| Module | Thư viện | Mục đích |
|---|---|---|
| Camera | `picamera2` | Capture frame từ camera RPi |
| Pose detection | `mediapipe` Pose | Phát hiện người, tư thế ngồi/đứng |
| Gaze detection | `mediapipe` FaceMesh | Xác định hướng nhìn qua góc đầu |
| Hand detection | `mediapipe` Hands | Vị trí tay, phân loại hoạt động |
| Computer vision | `opencv-python` | Xử lý ảnh, vẽ overlay |
| Web stream | `flask` | Dashboard và MJPEG stream |
| AI / TTS | `openai`, `gTTS` | Nhắc nhở thông minh bằng giọng nói |
| Config | `python-dotenv` | Quản lý biến môi trường |

---

## Truy cập hệ thống

Sau khi khởi động (`python3 main.py`):

| URL | Nội dung |
|---|---|
| `http://<pi-ip>:5000/` | Dashboard chính (camera + trạng thái) |
| `http://<pi-ip>:5000/video_feed` | MJPEG stream thuần |
| `http://<pi-ip>:5000/status` | JSON trạng thái hiện tại |
| `http://<pi-ip>:5000/stats` | JSON thống kê phiên |
| `http://<pi-ip>:5000/absence_log` | JSON lịch sử vắng mặt |
| `http://<pi-ip>:5000/chat` | POST: tương tác với AI tutor |
