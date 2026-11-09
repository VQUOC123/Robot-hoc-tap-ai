# 04. Kiến trúc hệ thống

## 1. Hai lớp xử lý
```
+------------------ Raspberry Pi 5 (EDGE) ------------------+          +---- CLOUD ----+
| Camera -> Capture (RAM only)                              |          |               |
|   |-> Posture/Attention  -> Event Engine --(text/số)------+--------> | Backend API   |--> Dashboard
|   |-> Page Detector -> Deskew -> Privacy Gate --(ảnh trang)-+------> | LLM API       |
|                                      ^ chặn nếu có mặt/da  |          +---------------+
|   LLM reply -> Dialog Manager -> TTS/hiển thị             |
+-----------------------------------------------------------+
```
- **Edge** làm mọi việc tần suất cao và nhạy cảm (tư thế, mặt, tập trung). Không gì liên quan cơ thể/mặt trẻ rời thiết bị.
- **Cloud LLM** chỉ nhận ảnh trang sách/vở đã cắt và qua cổng riêng tư.
- **Backend** chỉ nhận sự kiện dạng văn bản/số.

## 2. Module (đề xuất cấu trúc repo)
```
robot/
  edge/
    capture/        # Picamera2, autofocus, ring buffer RAM
    perception/     # pose.py, attention.py, page_detect.py (backend suy luận thay được)
    privacy/        # gate.py (face/skin check), kiểm tra không ghi đĩa
    events/         # event_engine.py (debounce, cooldown, state machine)
    llm/            # client.py (Claude/OpenAI), prompts/
    dialog/         # tts, stt (tùy chọn)
    config.yaml
  server/
    api.py          # FastAPI, schema Pydantic KHÔNG có trường ảnh
    db.py
    web/            # dashboard
  eval/             # script đo, bộ dữ liệu thử nghiệm (không commit ảnh)
  tests/            # test tự động, gồm test "không ghi ảnh ra đĩa"
  docs/
```

## 3. Máy trạng thái chính (edge)
`IDLE` -> (phát hiện người ngồi) -> `OBSERVE` (tư thế/tập trung, 5-10 fps)
`OBSERVE` -> (sự kiện xấu kéo dài) -> `NUDGE` (nhắc, cooldown) -> `OBSERVE`
`OBSERVE` -> (trang ổn định hoặc trẻ hỏi) -> `CAPTURE_PAGE` (AF trigger, chụp) -> `GATE`
`GATE` -> pass -> `ASK_LLM` -> `SPEAK` -> `OBSERVE`; fail -> chụp lại hoặc báo "chưa đọc được".
Mất mạng: `ASK_LLM` bị bỏ qua, các trạng thái còn lại vẫn chạy.

## 4. Cổng riêng tư (chi tiết)
Điều kiện gửi ảnh: (1) ảnh là kết quả cắt từ contour trang (không phải khung hình gốc); (2) face detector không tìm thấy mặt; (3) tỷ lệ pixel màu da < ngưỡng cấu hình (mặc định 15%, cần chỉnh theo thực nghiệm đa dạng tông da/ánh sáng); (4) ảnh chỉ tồn tại trong bộ nhớ và bị giải phóng sau khi gửi. Mọi lần chặn ghi log (lý do, thời điểm), không kèm ảnh.

## 5. Schema sự kiện (ví dụ)
```json
{"device_id":"robot-01","ts":"2026-11-03T15:32:10+07:00","type":"posture_alert",
 "data":{"neck_angle_deg":41,"duration_s":14}}
{"type":"help_session","data":{"subject":"toan","grade":3,"llm_latency_ms":3200,"tokens_in":1400,"tokens_out":260,"escalate":false}}
```
Server validate bằng schema cứng, trường lạ/ảnh -> trả 422.

## 6. Công nghệ gợi ý
Python 3.11+, Picamera2, OpenCV, MediaPipe, NumPy, FastAPI, SQLite (POC), SDK Claude/OpenAI, systemd, pytest. Cho phép thay thế nếu có lý do, ghi lại trong báo cáo.
