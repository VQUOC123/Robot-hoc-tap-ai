# KẾ HOẠCH PHÁT TRIỂN & TIMELINE 8 TUẦN

**DỰ ÁN: ROBOT TRỢ LÝ HỌC TẬP AI CHO TRẺ 6-12 TUỔI (GIAI ĐOẠN POC)**

Quy mô: Team 7 thành viên (3 nhóm) · Thời lượng: 8 tuần · Phần cứng: Raspberry Pi 5 + Pi Camera Module 3 (Autofocus)

---

## Phân nhóm

| Nhóm | Thành viên |
|------|-----------|
| **BE** (Backend) | Phạm Trần Khánh Linh · Dương Thành Long · Trần Đặng Như Quỳnh |
| **Training AI** | Phan Hà Minh Phúc · Nguyễn Văn Quốc |
| **Web \& Service** | Phan Quang Hoàng Anh · Nguyễn Thị Cẩm Nguyên |

---

## Tuần 1 — Giai đoạn 1: Khởi động, Setup môi trường \& Khám phá

26/10–01/11/2026 · Mục tiêu: Toàn bộ môi trường phát triển sẵn sàng, mỗi nhóm chạy được "hello world" trên công nghệ phụ trách.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Nhận hardware và flash OS | BE | Nhận Pi 5 + Camera Module 3 + cáp CSI 22-pin; flash Pi OS 64-bit; test libcamera cơ bản | 26–27/10 |
| 2 | Thí nghiệm Autofocus ban đầu | BE | Test AF Auto vs AF Trigger trên Pi Camera Module 3; khảo sát góc lắp camera | 28–29/10 |
| 3 | Cài đặt MediaPipe Pose | Training AI | Cài MediaPipe Pose / MoveNet trên Pi 5 hoặc laptop; benchmark FPS và CPU ban đầu | 26–28/10 |
| 4 | Cài đặt MediaPipe FaceMesh | Training AI | Cài FaceMesh; viết script test tính EAR (tỷ lệ mở mắt) và yaw/pitch với webcam | 29–01/11 |
| 5 | Setup GitHub Repo | BE | Tạo repo chuẩn, chuẩn hóa Git flow (branch strategy), .gitignore, README; update Sheet timeline | 26–27/10 |
| 6 | Khởi tạo server Go/Fiber | BE | Dựng khung server Go + Fiber, cấu hình cơ bản, Dockerfile ban đầu | 28–01/11 |
| 7 | Test gọi Vision API | Training AI | Đọc docs Vision API Claude/OpenAI; test gửi ảnh mẫu trên Postman/Python; soạn khung Prompt v0 | 29–01/11 |
| 8 | Khởi tạo project Frontend | Web \& Service | Tạo project Vue 3 + Vite + TypeScript; setup Tailwind CSS + shadcn/ui; Pinia store + Axios | 26–29/10 |
| 9 | Thiết kế wireframe Dashboard | Web \& Service | Phác thảo wireframe/mockup giao diện Dashboard phụ huynh trên Figma hoặc giấy | 30–01/11 |

**Đầu ra cuối tuần:** Camera stream chạy được trên Pi; Repo GitHub chuẩn mực; Server Go khung hoạt động; Project Vue 3 khởi tạo; Script test Pose/FaceMesh chạy được trên laptop.

---

## Tuần 2 — Giai đoạn 2: Xây dựng nền tảng camera, tư thế và Backend

02/11–08/11/2026 · Mục tiêu: Có dữ liệu tư thế cục bộ và luồng gọi LLM thử nghiệm.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Hoàn thiện module thu hình | BE | Picamera2, cấu hình độ phân giải, đo FPS; mục tiêu A1 ≥ 15 FPS ở 720p | 02–03/11 |
| 2 | Xây dựng ring buffer trong RAM | BE | Giữ khung hình trong RAM, không ghi ảnh/video xuống đĩa trong luồng vận hành | 04–05/11 |
| 3 | Xây dựng pipeline ước lượng tư thế | Training AI | Thử MediaPipe Pose hoặc MoveNet, lấy các landmark cần thiết | 02–04/11 |
| 4 | Tính chỉ số tư thế | Training AI | Tính góc gập cổ, nghiêng vai và chỉ số proxy khoảng cách đầu–mặt bàn | 05–07/11 |
| 5 | Tạo Backend và cơ sở dữ liệu | BE | FastAPI + SQLite, bảng lưu sự kiện, timestamp và loại sự kiện | 04–06/11 |
| 6 | Xây dựng LLM client phiên bản đầu | BE + Training AI | Gọi API vision, timeout/retry, log token và latency; dùng ảnh mẫu được phép | 06–08/11 |
| 7 | Thiết kế giao diện dashboard | Web \& Service | Phác thảo thời lượng học, cảnh báo tư thế, lịch sử hỗ trợ bài học | 02–05/11 |
| 8 | Kết nối API events từ BE | Web \& Service | Dùng Axios gọi API GET events; hiển thị danh sách sự kiện cơ bản lên giao diện | 06–08/11 |
| 9 | Đo hiệu năng baseline | Cả nhóm | Ghi FPS, CPU, nhiệt độ, độ trễ và điều kiện đo | 08/11 |

**Đầu ra cuối tuần:** Hiển thị được chỉ số tư thế cơ bản, có Backend lưu sự kiện và LLM client chạy thử. Đây cũng là tuần đo baseline để điều chỉnh ngưỡng hợp lý.

---

## Tuần 3 — Giai đoạn 3: Nhắc nhở tư thế và tập trung — ★ Mốc M1

09/11–15/11/2026 · Mục tiêu: Hoàn thành vòng lặp phát hiện tư thế xấu và nhắc nhở cục bộ.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Hoàn thiện góc camera và autofocus | BE | Chốt vị trí lắp camera, ghi lại góc lắp và cấu hình AF | 09–10/11 |
| 2 | Phát hiện tư thế xấu kéo dài | Training AI | Ngưỡng cấu hình được, mặc định kéo dài 10 giây | 09–11/11 |
| 3 | Xây dựng bộ máy sự kiện | BE | State machine, debounce, cooldown nhắc nhở mặc định ≥ 2 phút | 10–12/11 |
| 4 | Thử đo nhắm mắt và quay đầu | Training AI | Tính EAR, yaw/pitch; đánh giá tính khả thi của B3 | 11–13/11 |
| 5 | Xây dựng cơ chế phát lời nhắc | BE + Training AI | Tạo sự kiện nhắc tư thế; phát thông báo qua giao diện hoặc âm thanh nếu có | 12–13/11 |
| 6 | Chặn lưu ảnh/output vào ổ đĩa | BE | Chốt lại điều kiện: các file thử nghiệm chạy mà không ghi bất kỳ ảnh nào ra đĩa | 13–14/11 |
| 7 | Dashboard v0 realtime events | Web \& Service | Hiển thị realtime danh sách sự kiện tư thế/tập trung, status indicators (tốt/xấu) | 09–13/11 |
| 8 | Test Prompt v1 với bài tập tiểu học | Training AI | Thử 10 kịch bản bài tập; đo độ trễ LLM và số token tiêu thụ | 13–14/11 |
| 9 | Chuẩn bị Demo M1 | Cả nhóm | Tích hợp TV1+TV2+TV3; chạy thử toàn luồng trên Pi 5; chuẩn bị kịch bản demo | 14–15/11 |

> **🎯 DEMO M1 — Tiêu chí đạt:**
> - Pose CPU ≥ 5 fps (Q1)
> - Độ trễ nhắc nhở ≤ 3s (Q2)
> - Cooldown chống báo nhầm ≥ 2 phút
> - Mã yêu cầu đạt: B1, B2, B4, B5, A1, A2, A3

**Đầu ra cuối tuần:** Hệ thống chạy cục bộ trên Pi 5 phát hiện \& nhắc tư thế xấu/mất tập trung ổn định. Dashboard v0 hiển thị events realtime.

---

## Tuần 4 — Giai đoạn 4: Phát hiện trang sách/vở \& Dashboard v1

16/11–22/11/2026 · Mục tiêu: Cắt trang vở chính xác, nâng cấp Dashboard biểu đồ thống kê.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Cấu hình AF Trigger theo bbox trang | BE | AfMetering=Windows theo tọa độ bbox trang; AF Trigger tự lấy nét vùng trang trước khi chụp | 16–18/11 |
| 2 | Xây dựng pipeline cắt trang deskew | Training AI | OpenCV Canny/Contour tìm trang sách/vở; getPerspectiveTransform làm phẳng trang giấy | 16–19/11 |
| 3 | Phát hiện trang ổn định | Training AI | Thuật toán detect trang ổn định (không tay che, không rung); test trên 20+ mẫu vở thực tế | 19–21/11 |
| 4 | Tinh chỉnh ngưỡng Pose/Attention | Training AI | Thu thập phản hồi sau M1; tinh chỉnh ngưỡng góc/EAR trên 3-5 tình nguyện viên | 16–18/11 |
| 5 | API phiên học \& thống kê | BE | API ghi log session (start/end, duration); API thống kê tần suất nhắc, thời lượng học | 16–19/11 |
| 6 | Test server từ chối payload ảnh | BE | Viết test case tự động kiểm tra FastAPI từ chối payload có ảnh → HTTP 422 (Q11) | 20–21/11 |
| 7 | Tối ưu ảnh giảm token cost LLM | BE + Training AI | Thử nghiệm downscale ảnh trang vở vừa đủ nét đọc chữ để giảm chi phí token | 20–22/11 |
| 8 | Dashboard v1 biểu đồ thống kê | Web \& Service | Biểu đồ thời lượng học (bar chart), tần suất nhắc (line chart), danh sách bài cần can thiệp | 16–20/11 |
| 9 | Trang chi tiết phiên học | Web \& Service | Thiết kế trang chi tiết: timeline events trong phiên, thống kê theo ngày/tuần | 20–22/11 |
|10| Tổng hợp báo cáo tuần | BE | Như Quỳnh tổng hợp báo cáo tiến độ, số liệu đo đạc, khó khăn phát sinh | 22/11 |

**Đầu ra cuối tuần:** Cắt trang đúng chuẩn trên ≥20 ảnh thực tế; Dashboard v1 hiển thị đầy đủ biểu đồ \& sự kiện; Server reject ảnh 422 pass test.

---

## Tuần 5 — Giai đoạn 5: Tích hợp Cổng riêng tư \& LLM — ★ Mốc M2

23/11–29/11/2026 · Mục tiêu: Vòng lặp đầy đủ Chụp trang → Cổng riêng tư → LLM phản hồi sư phạm.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Đồng bộ luồng chụp HD | BE | Khi phát hiện trang ổn định → AF Trigger → chụp frame chất lượng cao | 23–24/11 |
| 2 | Xây dựng Privacy Gate đa tầng | Training AI | Face detection + phân tích vùng da HSV < 15%; chặn tuyệt đối ảnh có mặt/da | 23–26/11 |
| 3 | Bộ ảnh đối kháng test Privacy Gate | Training AI | Xây bộ 50+ ảnh đối kháng test; đảm bảo chặn mặt/da ≥ 98% (Q9) | 26–27/11 |
| 4 | Hoàn thiện 20+ kịch bản test Prompt | Training AI | Giọng điệu gợi mở, từ chối bài xấu, "không chắc" khi ảnh mờ; đo token/latency | 23–26/11 |
| 5 | API log LLM response \& chi phí token | BE | API ghi log phản hồi LLM, chi phí token, độ trễ; endpoint thống kê cost | 23–26/11 |
| 6 | Tích hợp toàn luồng E2E | BE + Training AI | Edge → Cổng riêng tư → Cloud LLM → phản hồi; test end-to-end trên Pi 5 | 26–28/11 |
| 7 | Duy trì ổn định pose/attention nền | Training AI | Luồng pose + attention chạy nền 5-10 fps ổn định khi có thêm Privacy Gate + LLM | 25–27/11 |
| 8 | Dashboard hiển thị log LLM \& cost | Web \& Service | Tích hợp hiển thị phản hồi LLM, lịch sử bài học, biểu đồ chi phí token | 23–27/11 |
| 9 | Chuẩn bị Demo M2 | Cả nhóm | Chạy thử toàn luồng; chuẩn bị kịch bản demo; đo đạc Q5, Q9, Q11 | 28–29/11 |

> **🎯 DEMO M2 — Tiêu chí đạt:**
> - Cắt trang ≥ 90% (Q5)
> - Chặn mặt/da ≥ 98% (Q9)
> - Server từ chối ảnh → HTTP 422 (Q11)
> - Mã yêu cầu đạt: C1, C2, C3, D1, D2, D3, D4, E1, E2

**Đầu ra cuối tuần:** Vòng lặp Chụp trang → Cổng riêng tư chặn an toàn → LLM giải thích bài end-to-end. Dashboard hiển thị đầy đủ log \& cost.

---

## Tuần 6 — Giai đoạn 6: Tối ưu hóa hiệu năng \& Tính năng bổ trợ

30/11–06/12/2026 · Mục tiêu: Giảm false-positive, thêm tính năng Should/Could, tối ưu hiệu năng tổng thể.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Khảo sát camera thứ 2 | BE | Feasibility study cho camera thứ 2 (A5 - Could); tối ưu pipeline Picamera2 | 30/11–02/12 |
| 2 | Đánh giá tỷ lệ báo nhầm Q4 | Training AI | Đo false-positive: mục tiêu ≤ 1 lần/10 phút; tinh chỉnh thuật toán lọc nhiễu | 30/11–03/12 |
| 3 | Tích hợp Laplacian \& auto-retry chụp | Training AI | Đánh giá độ nét ảnh bằng Laplacian (C5); tự động chụp lại tối đa N lần nếu mờ (C4) | 03–05/12 |
| 4 | Tích hợp Escalation flag | Training AI | Cơ chế D6: khi trẻ bày tỏ buồn bã/khó khăn vượt mức → gửi cờ cảnh báo | 04–06/12 |
| 5 | Auth JWT \& phân quyền | BE | Xây dựng Auth JWT (đăng nhập, refresh token); phân quyền phụ huynh/giáo viên (E5) | 30/11–04/12 |
| 6 | Redis JWT blacklist \& middleware | BE | Redis blacklist cho logout; middleware auth cho protected routes | 04–06/12 |
| 7 | Thử nghiệm TTS tiếng Việt | BE + Training AI | Tích hợp TTS module (F1 - Could); test phát giọng nói nhắc nhở bằng tiếng Việt | 05–06/12 |
| 8 | Auth UI \& phân quyền giao diện | Web \& Service | Form login/register; route guard theo role; giao diện khác nhau cho phụ huynh vs giáo viên | 30/11–04/12 |
| 9 | Báo cáo hiệu năng tổng hợp | Cả nhóm | Lập báo cáo tổng hợp: FPS, CPU, nhiệt, latency, false-positive, chi phí API | 06/12 |

**Đầu ra cuối tuần:** Báo cáo toàn diện hiệu năng phần cứng và chi phí API; Auth hoạt động; Các tính năng Should/Could sẵn sàng; TTS demo.

---

## Tuần 7 — Giai đoạn 7: Đóng gói hệ thống, Soak Test \& Kiểm thử an toàn

07/12–13/12/2026 · Mục tiêu: Bản Release Candidate ổn định, pass toàn bộ test an toàn và privacy.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Đóng gói systemd daemon | BE + Training AI | Đóng gói toàn bộ dịch vụ edge thành systemd daemon; cơ chế auto-restart khi gặp lỗi | 07–09/12 |
| 2 | Soak test 2 giờ liên tục | Training AI | Chạy quan sát tư thế/attention 2 giờ liên tục; kiểm soát nhiệt CPU < 80°C (Q12) | 09–11/12 |
| 3 | Test Q10: Audit 0 byte ảnh ghi đĩa | BE + Training AI | Audit toàn bộ file/IO syscall trong 1 giờ; chứng minh 0 byte ảnh ghi ra đĩa | 10–11/12 |
| 4 | Graceful degradation khi mất mạng | Training AI | Kịch bản D3: mạng rớt → vẫn nhắc tư thế bình thường; LLM queue khi reconnect | 07–09/12 |
| 5 | Rà soát code 0 nhận diện danh tính | BE | Review toàn bộ codebase: cam kết 0 dòng code nhận diện danh tính (G2) | 11–12/12 |
| 6 | Docker container + health check | BE | Đóng gói server thành Docker container; health check endpoint; CI/CD pipeline hoàn chỉnh | 07–10/12 |
| 7 | Test bảo mật API | BE | Test auth bypass, injection, concurrent requests; xóa toàn bộ dữ liệu test nhạy cảm | 10–12/12 |
| 8 | Mobile responsive \& polish UI | Web \& Service | Responsive design tablet/mobile; polish animations, loading states, error handling | 07–11/12 |
| 9 | Cross-browser \& performance testing | Web \& Service | Tối ưu lazy loading, code splitting; kiểm tra Chrome/Firefox/Safari/Edge |

---

## Tuần 8 — Giai đoạn 8: Nghiệm thu tổng thể, Báo cáo \& Bàn giao — ★ Mốc M3

14/12–20/12/2026 · Mục tiêu: Demo hoàn chỉnh 10 phút, bàn giao 100% yêu cầu MUST.

| STT | Nhiệm Vụ | Phân Công | Chi tiết/đầu ra | Thời gian |
|:---:|----------|:---------:|-----------------|:---------:|
| 1 | Đo đạc chính thức Q1 → Q13 | Cả nhóm | Đo đạc toàn bộ 13 tiêu chí định lượng theo đúng phương pháp File 06 | 14–16/12 |
| 2 | Tổng kết chi phí vận hành API | BE + Training AI | Chi phí trung bình token/giờ học; so sánh Claude vs OpenAI vs Gemini | 14–15/12 |
| 3 | Tài liệu hướng dẫn triển khai | BE | Hướng dẫn deploy từ máy sạch trong ≤ 30 phút (Q13); README hoàn chỉnh | 15–17/12 |
| 4 | Tài liệu API \& kiến trúc | BE | Swagger/OpenAPI documentation; sơ đồ kiến trúc hệ thống hoàn chỉnh | 16–17/12 |
| 5 | Dọn dẹp data \& bảo mật | Training AI | Xóa/mã hóa toàn bộ ảnh thực nghiệm tình nguyện viên; kiểm tra 0 ảnh trên git | 14–16/12 |
| 6 | Dọn dẹp API key \& config | BE | Xóa API key khỏi git history nếu lỡ commit; kiểm tra .env trong .gitignore | 16–17/12 |
| 7 | Tài liệu hướng dẫn sử dụng Dashboard | Web \& Service | Viết user guide cho phụ huynh/giáo viên; screenshot các trang chính | 14–16/12 |
| 8 | Chuẩn bị slide/poster Demo | Web \& Service | Slide trình bày 10 phút; ảnh chụp màn hình Dashboard; video demo ngắn nếu cần | 16–18/12 |
| 9 | Báo cáo kỹ thuật cuối kỳ | BE | Như Quỳnh tổng hợp: báo cáo kỹ thuật, bảng Q1-Q13, biên bản nghiệm thu | 17–19/12 |
|10| Demo trực tiếp 10 phút | Cả nhóm | Tham gia buổi Demo trước Hội đồng/Giảng viên; trình bày \& trả lời câu hỏi | 19–20/12 |

> **🎯 DEMO M3 — Tiêu chí nghiệm thu:**
> - 100% yêu cầu MUST đạt
> - Soak test 2h ổn định, CPU < 80°C (Q12)
> - 0 byte ảnh ghi đĩa (Q10)
> - Review code 0 nhận diện danh tính (G2)
> - Triển khai từ máy sạch ≤ 30 phút (Q13)
> - Bảng đo đạc Q1-Q13 đầy đủ

**Đầu ra cuối tuần:** Bàn giao toàn bộ Repo sạch, Tài liệu đặc tả hoàn chỉnh, Demo trực tiếp 10 phút thành công.

---

## Tổng hợp Deliverables theo Mốc

| Mốc | Tuần | Tiêu chí chính | Nhóm chịu trách nhiệm Demo |
|:----:|:----:|----------------|:---------------------------:|
| **M1** | 3 | Pose ≥ 5fps · Nhắc ≤ 3s · Cooldown ≥ 2p | Training AI + BE |
| **M2** | 5 | Cắt trang ≥ 90% · Chặn mặt ≥ 98% · Server reject 422 | Training AI + BE + Web |
| **M3** | 8 | 100% MUST · Soak 2h · 0 byte ảnh · Deploy ≤ 30p | Cả nhóm |

