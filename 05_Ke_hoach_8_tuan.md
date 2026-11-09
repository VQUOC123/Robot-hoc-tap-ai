# 05. Kế hoạch 8 tuần

## Phân công (đề xuất, có thể đổi sau tuần 1)
- **SV A – Perception (edge):** camera/AF, tư thế, tập trung, phát hiện trang, cổng riêng tư.
- **SV B – Cloud & nền tảng:** LLM client + prompt, event engine, server, dashboard, đánh giá chi phí/độ trễ.
- Cả hai: tích hợp, kiểm thử, tài liệu. Review code chéo mỗi tuần.

## Lịch
| Tuần | SV A | SV B | Sản phẩm cuối tuần |
|---|---|---|---|
| 1 | Cài Pi OS, kiểm tra camera, Picamera2; thí nghiệm AF (Auto vs Windows+Trigger); thử vị trí lắp camera | Dựng repo, CI/test cơ bản; đọc docs API vision; gọi LLM thử với ảnh trang mẫu; thiết kế schema sự kiện | Camera chạy, ảnh nét; báo cáo AF; repo khung |
| 2 | Pose cục bộ + các chỉ số góc; đo fps/CPU/nhiệt; ring buffer RAM | Prompt v1 cho 6-12 tuổi; client có retry/timeout; log token/latency; server FastAPI + DB | Demo: hiện góc cổ/vai realtime; gọi LLM end-to-end bằng ảnh có sẵn |
| 3 | Attention (EAR, yaw/pitch); chọn ngưỡng ban đầu | Event engine: debounce, cooldown, state machine | **Mốc M1 (demo 1):** nhắc tư thế/tập trung cục bộ chạy được |
| 4 | Phát hiện trang + deskew; phát hiện trang ổn định; AF theo bbox trang | Dashboard v1 (hiển thị sự kiện); schema validation từ chối ảnh | Cắt trang đúng trên >= 20 ảnh thử |
| 5 | Cổng riêng tư (face + skin) + bộ thử nghiệm đối kháng | Tích hợp luồng trang -> LLM -> phản hồi; bộ 20+ tình huống đánh giá prompt | **Mốc M2 (demo 2):** chụp trang -> cổng -> LLM -> giảng giải |
| 6 | Tối ưu hiệu năng; chống báo nhầm; (Could) TTS | Escalation flag (D6); đo chi phí; (Should) đăng nhập | Báo cáo hiệu năng và chi phí |
| 7 | Tích hợp end-to-end, systemd, soak test 2 giờ | Kiểm thử tự động (G1: không ghi đĩa), review code G2 | Bản release candidate; kết quả soak test |
| 8 | Đánh giá cuối theo file 06; sửa lỗi | Báo cáo cuối, tài liệu hướng dẫn chạy/hạn chế/đề xuất tiếp theo | **Mốc M3: demo cuối + báo cáo + bàn giao** |

## Mốc đánh giá của giảng viên
- **M1 (cuối tuần 3):** B1, B2, B4, B5, A1-A3 đạt.
- **M2 (cuối tuần 5):** C1-C3, D1-D4, E1-E2 đạt.
- **M3 (cuối tuần 8):** toàn bộ yêu cầu Must đạt theo file 06; báo cáo và demo.

## Rủi ro và cách xử lý
| Rủi ro | Cách xử lý |
|---|---|
| Fps thấp trên CPU | Giảm độ phân giải phân tích, chạy pose 5 fps, thử mô hình lite; đề xuất mua Hailo nếu không đạt |
| 1 camera không vừa cả tư thế lẫn đọc chữ | Đo ở tuần 1; kích hoạt phương án 2 camera (A5) |
| Chữ viết tay khó đọc | Đo riêng, báo cáo giới hạn; prompt yêu cầu LLM nói "không chắc" |
| Tay che trang/AF bắt nhầm | AF theo AfWindows + trang ổn định + chụp lại |
| Báo nhầm tư thế gây phiền | Debounce, cooldown, ngưỡng có thể chỉnh |
| Chi phí API vượt dự kiến | Giảm kích thước ảnh, chỉ gọi khi có sự kiện, đặt hạn mức ngày |
| Vi phạm riêng tư do lỗi code | Test tự động G1, review chéo, quy tắc mục 01 |
| Mạng yếu | Suy giảm êm (D3) |
