# KẾ HOẠCH PHÁT TRIỂN & TIMELINE 8 TUẦN — 3 NHÓM

**DỰ ÁN: ROBOT TRỢ LÝ HỌC TẬP AI CHO TRẺ 6-12 TUỔI (GIAI ĐOẠN POC)**

Quy mô: Team 7 thành viên (3 nhóm) · Thời lượng: 8 tuần · Phần cứng: Raspberry Pi 5 + Pi Camera Module 3

---

## Phân nhóm

| Nhóm | Thành viên |
|------|-----------|
| **BE** (Backend) | Phạm Trần Khánh Linh · Dương Thành Long · Trần Đặng Như Quỳnh |
| **Training AI** | Phan Hà Minh Phúc · Nguyễn Văn Quốc |
| **Web & Service** | Phan Quang Hoàng Anh · Nguyễn Thị Cẩm Nguyên |

---

## Tuần 1 — Giai đoạn 1: Khởi động, Setup môi trường & Khám phá
26/10–01/11/2026 · Mục tiêu: Toàn bộ môi trường phát triển sẵn sàng.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Nhận hardware và flash OS | BE | Nhận Pi 5 + Camera Module 3 + cáp CSI 22-pin; flash Pi OS 64-bit; test libcamera | 26–27/10 |
| 2 | Thí nghiệm Autofocus ban đầu | BE | Test AF Auto vs AF Trigger trên Pi Camera Module 3; khảo sát góc lắp camera | 28–29/10 |
| 3 | Cài đặt MediaPipe Pose | Training AI | Cài MediaPipe Pose / MoveNet trên Pi 5 hoặc laptop; benchmark FPS và CPU | 26–28/10 |
| 4 | Cài đặt MediaPipe FaceMesh | Training AI | Cài FaceMesh; viết script test tính EAR và yaw/pitch với webcam | 29–01/11 |
| 5 | Setup GitHub Repo | BE | Tạo repo chuẩn, chuẩn hóa Git flow, .gitignore, README; update Sheet timeline | 26–27/10 |
| 6 | Khởi tạo server Go/Fiber | BE | Dựng khung server Go + Fiber, cấu hình cơ bản, Dockerfile ban đầu | 28–01/11 |
| 7 | Test gọi Vision API | Training AI | Đọc docs Vision API Claude/OpenAI; test Postman/Python; soạn khung Prompt v0 | 29–01/11 |
| 8 | Khởi tạo project Frontend | Web & Service | Tạo project Vue 3 + Vite + TypeScript; setup Tailwind CSS + shadcn/ui | 26–29/10 |
| 9 | Thiết kế wireframe Dashboard | Web & Service | Phác thảo wireframe/mockup giao diện Dashboard phụ huynh | 30–01/11 |

**Đầu ra cuối tuần:** Camera stream chạy được; Repo GitHub chuẩn; Server Go khung; Project Vue 3 khởi tạo.

---

## Tuần 2 — Giai đoạn 2: Xây dựng nền tảng camera, tư thế và Backend
02/11–08/11/2026 · Mục tiêu: Có dữ liệu tư thế cục bộ và luồng gọi LLM thử nghiệm.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Hoàn thiện module thu hình | BE | Picamera2, cấu hình độ phân giải, đo FPS; mục tiêu A1 ≥ 15 FPS ở 720p | 02–03/11 |
| 2 | Xây dựng ring buffer trong RAM | BE | Giữ khung hình trong RAM, không ghi ảnh/video xuống đĩa | 04–05/11 |
| 3 | Xây dựng pipeline ước lượng tư thế | Training AI | Thử MediaPipe Pose hoặc MoveNet, lấy các landmark cần thiết | 02–04/11 |
| 4 | Tính chỉ số tư thế | Training AI | Tính góc gập cổ, nghiêng vai và chỉ số proxy khoảng cách đầu–mặt bàn | 05–07/11 |
| 5 | Tạo Backend và cơ sở dữ liệu | BE | FastAPI + SQLite, bảng lưu sự kiện, timestamp và loại sự kiện | 04–06/11 |
| 6 | Xây dựng LLM client phiên bản đầu | BE + Training AI | Gọi API vision, timeout/retry, log token và latency; dùng ảnh mẫu được phép | 06–08/11 |
| 7 | Thiết kế giao diện dashboard | Web & Service | Phác thảo thời lượng học, cảnh báo tư thế, lịch sử hỗ trợ bài học | 02–05/11 |
| 8 | Kết nối API events từ BE | Web & Service | Axios gọi API GET events; hiển thị danh sách sự kiện cơ bản | 06–08/11 |
| 9 | Đo hiệu năng baseline | Cả nhóm | Ghi FPS, CPU, nhiệt độ, độ trễ và điều kiện đo | 08/11 |

**Đầu ra cuối tuần:** Chỉ số tư thế cơ bản; Backend lưu sự kiện; LLM client chạy thử; Baseline đo đạc.

---

## Tuần 3 — Giai đoạn 3: Nhắc nhở tư thế và tập trung — ★ Mốc M1
09/11–15/11/2026 · Mục tiêu: Hoàn thành vòng lặp phát hiện tư thế xấu và nhắc nhở cục bộ.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Hoàn thiện góc camera và autofocus | BE | Chốt vị trí lắp camera, ghi lại góc lắp và cấu hình AF | 09–10/11 |
| 2 | Phát hiện tư thế xấu kéo dài | Training AI | Ngưỡng cấu hình được, mặc định kéo dài 10 giây | 09–11/11 |
| 3 | Xây dựng bộ máy sự kiện | BE | State machine, debounce, cooldown nhắc nhở mặc định ≥ 2 phút | 10–12/11 |
| 4 | Thử đo nhắm mắt và quay đầu | Training AI | Tính EAR, yaw/pitch; đánh giá tính khả thi của B3 | 11–13/11 |
| 5 | Xây dựng cơ chế phát lời nhắc | BE + Training AI | Tạo sự kiện nhắc tư thế; phát thông báo qua giao diện hoặc âm thanh | 12–13/11 |
| 6 | Chặn lưu ảnh/output vào ổ đĩa | BE | Chốt điều kiện: không ghi bất kỳ ảnh nào ra đĩa | 13–14/11 |
| 7 | Dashboard v0 realtime events | Web & Service | Hiển thị realtime sự kiện tư thế/tập trung, status indicators | 09–13/11 |
| 8 | Test Prompt v1 bài tập tiểu học | Training AI | 10 kịch bản bài tập; đo độ trễ LLM và token tiêu thụ | 13–14/11 |
| 9 | Chuẩn bị Demo M1 | Cả nhóm | Tích hợp; chạy thử toàn luồng trên Pi 5; kịch bản demo | 14–15/11 |

**🎯 M1:** Pose ≥ 5fps (Q1) · Nhắc ≤ 3s (Q2) · Cooldown ≥ 2p · Dashboard v0 realtime

---

## Tuần 4 — Giai đoạn 4: Phát hiện trang sách/vở & Dashboard v1
16/11–22/11/2026 · Mục tiêu: Cắt trang vở chính xác, Dashboard biểu đồ thống kê.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Cấu hình AF Trigger theo bbox trang | BE | AfMetering=Windows theo tọa độ bbox; AF Trigger lấy nét vùng trang | 16–18/11 |
| 2 | Pipeline cắt trang deskew | Training AI | OpenCV Canny/Contour + getPerspectiveTransform làm phẳng trang giấy | 16–19/11 |
| 3 | Phát hiện trang ổn định | Training AI | Detect trang ổn định (không tay che, không rung); test 20+ mẫu vở | 19–21/11 |
| 4 | Tinh chỉnh ngưỡng Pose/Attention | Training AI | Phản hồi sau M1; tinh chỉnh ngưỡng trên 3-5 tình nguyện viên | 16–18/11 |
| 5 | API phiên học & thống kê | BE | API log session; API thống kê tần suất nhắc, thời lượng học | 16–19/11 |
| 6 | Test server reject payload ảnh | BE | Test tự động kiểm tra FastAPI reject payload ảnh → HTTP 422 | 20–21/11 |
| 7 | Tối ưu ảnh giảm token cost | BE + Training AI | Downscale ảnh vừa đủ nét đọc chữ để giảm chi phí token | 20–22/11 |
| 8 | Dashboard v1 biểu đồ | Web & Service | Bar chart thời lượng học, line chart tần suất nhắc, danh sách bài | 16–20/11 |
| 9 | Trang chi tiết phiên học | Web & Service | Timeline events, thống kê theo ngày/tuần | 20–22/11 |
| 10 | Tổng hợp báo cáo tuần | BE | Tổng hợp tiến độ, số liệu đo đạc, khó khăn phát sinh | 22/11 |

**Đầu ra cuối tuần:** Cắt trang ≥20 mẫu; Dashboard v1 biểu đồ; Server reject 422 pass test.

---

## Tuần 5 — Giai đoạn 5: Tích hợp Cổng riêng tư & LLM — ★ Mốc M2
23/11–29/11/2026 · Mục tiêu: Vòng lặp Chụp trang → Cổng riêng tư → LLM phản hồi.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Đồng bộ luồng chụp HD | BE | Trang ổn định → AF Trigger → chụp frame HD | 23–24/11 |
| 2 | Privacy Gate đa tầng | Training AI | Face detection + da HSV < 15%; chặn tuyệt đối ảnh có mặt/da | 23–26/11 |
| 3 | Bộ ảnh đối kháng test Gate | Training AI | 50+ ảnh đối kháng; chặn mặt/da ≥ 98% (Q9) | 26–27/11 |
| 4 | 20+ kịch bản test Prompt | Training AI | Giọng gợi mở, từ chối bài xấu, "không chắc" khi mờ | 23–26/11 |
| 5 | API log LLM & chi phí token | BE | Ghi log phản hồi LLM, chi phí token, latency; endpoint thống kê | 23–26/11 |
| 6 | Tích hợp toàn luồng E2E | BE + Training AI | Edge → Cổng riêng tư → Cloud LLM → phản hồi; test E2E trên Pi 5 | 26–28/11 |
| 7 | Duy trì pose/attention nền | Training AI | Ổn định 5-10 fps khi có thêm Privacy Gate + LLM | 25–27/11 |
| 8 | Dashboard log LLM & cost | Web & Service | Hiển thị phản hồi LLM, lịch sử bài, biểu đồ chi phí | 23–27/11 |
| 9 | Chuẩn bị Demo M2 | Cả nhóm | Chạy thử toàn luồng; kịch bản demo; đo Q5, Q9, Q11 | 28–29/11 |

**🎯 M2:** Cắt trang ≥ 90% (Q5) · Chặn mặt/da ≥ 98% (Q9) · Server reject 422 (Q11) · LLM E2E

---

## Tuần 6 — Giai đoạn 6: Tối ưu hiệu năng & Tính năng bổ trợ
30/11–06/12/2026 · Mục tiêu: Giảm false-positive, thêm Should/Could, tối ưu tổng thể.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Khảo sát camera thứ 2 | BE | Feasibility study A5 (Could); tối ưu pipeline Picamera2 | 30/11–02/12 |
| 2 | Đánh giá báo nhầm Q4 | Training AI | Mục tiêu ≤ 1/10 phút; tinh chỉnh lọc nhiễu | 30/11–03/12 |
| 3 | Laplacian & auto-retry chụp | Training AI | Đánh giá độ nét C5; tự động chụp lại tối đa N lần C4 | 03–05/12 |
| 4 | Escalation flag D6 | Training AI | Trẻ buồn bã/khó khăn → gửi cờ cảnh báo | 04–06/12 |
| 5 | Auth JWT & phân quyền | BE | JWT login/refresh; phân quyền phụ huynh/giáo viên E5 | 30/11–04/12 |
| 6 | Redis JWT blacklist | BE | Redis blacklist logout; middleware auth protected routes | 04–06/12 |
| 7 | TTS tiếng Việt | BE + Training AI | Tích hợp TTS F1 (Could); test phát giọng nói nhắc nhở | 05–06/12 |
| 8 | Auth UI & phân quyền giao diện | Web & Service | Form login/register; route guard; giao diện theo role | 30/11–04/12 |
| 9 | Báo cáo hiệu năng tổng hợp | Cả nhóm | FPS, CPU, nhiệt, latency, false-positive, chi phí API | 06/12 |

**Đầu ra cuối tuần:** Báo cáo hiệu năng; Auth hoạt động; Should/Could sẵn sàng; TTS demo.

---

## Tuần 7 — Giai đoạn 7: Đóng gói, Soak Test & Kiểm thử an toàn
07/12–13/12/2026 · Mục tiêu: Release Candidate ổn định, pass test an toàn & privacy.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Đóng gói systemd daemon | BE + Training AI | Toàn bộ edge thành systemd; auto-restart khi lỗi | 07–09/12 |
| 2 | Soak test 2 giờ | Training AI | Quan sát tư thế/attention 2h; CPU < 80°C (Q12) | 09–11/12 |
| 3 | Test Q10: Audit 0 byte ảnh | BE + Training AI | Audit IO syscall 1 giờ; chứng minh 0 byte ảnh ghi đĩa | 10–11/12 |
| 4 | Graceful degradation offline | Training AI | D3: mạng rớt vẫn nhắc tư thế; LLM queue khi reconnect | 07–09/12 |
| 5 | Rà soát code G2 | BE | Review codebase: 0 dòng nhận diện danh tính | 11–12/12 |
| 6 | Docker + health check | BE | Docker container server; health check; CI/CD hoàn chỉnh | 07–10/12 |
| 7 | Test bảo mật API | BE | Auth bypass, injection, concurrent; xóa data test nhạy cảm | 10–12/12 |
| 8 | Mobile responsive & polish | Web & Service | Responsive tablet/mobile; animations, loading, error handling | 07–11/12 |
| 9 | Cross-browser & performance | Web & Service | Lazy loading, code splitting; Chrome/Firefox/Safari/Edge | 11–13/12 |
| 10 | Integration test toàn diện | Cả nhóm | Test tự động G1/G2; regression test toàn hệ thống | 12–13/12 |

**Đầu ra cuối tuần:** Release Candidate; Soak test 2h pass; Test G1/G2 100%; UI polished.

---

## Tuần 8 — Giai đoạn 8: Nghiệm thu, Báo cáo & Bàn giao — ★ Mốc M3
14/12–20/12/2026 · Mục tiêu: Demo hoàn chỉnh 10 phút, bàn giao 100% MUST.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Đo đạc chính thức Q1–Q13 | Cả nhóm | 13 tiêu chí định lượng theo phương pháp File 06 | 14–16/12 |
| 2 | Tổng kết chi phí API | BE + Training AI | Chi phí token/giờ; so sánh Claude vs OpenAI vs Gemini | 14–15/12 |
| 3 | Tài liệu triển khai | BE | Deploy từ máy sạch ≤ 30 phút (Q13); README hoàn chỉnh | 15–17/12 |
| 4 | Tài liệu API & kiến trúc | BE | Swagger/OpenAPI; sơ đồ kiến trúc hệ thống | 16–17/12 |
| 5 | Dọn dẹp data & bảo mật | Training AI | Xóa/mã hóa ảnh tình nguyện viên; 0 ảnh trên git | 14–16/12 |
| 6 | Dọn dẹp API key & config | BE | Xóa key khỏi git history; .env trong .gitignore | 16–17/12 |
| 7 | Tài liệu sử dụng Dashboard | Web & Service | User guide phụ huynh/giáo viên; screenshot trang chính | 14–16/12 |
| 8 | Slide/poster Demo | Web & Service | Slide 10 phút; screenshot Dashboard; video demo ngắn | 16–18/12 |
| 9 | Báo cáo kỹ thuật cuối kỳ | BE | Báo cáo kỹ thuật, bảng Q1-Q13, biên bản nghiệm thu | 17–19/12 |
| 10 | Demo trực tiếp 10 phút | Cả nhóm | Demo trước Hội đồng/Giảng viên; trình bày & trả lời | 19–20/12 |

**🎯 M3:** 100% MUST · Soak 2h CPU < 80°C · 0 byte ảnh · Code 0 nhận diện · Deploy ≤ 30p
