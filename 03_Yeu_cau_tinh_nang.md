# 03. Yêu cầu tính năng

Ưu tiên: **M** = Must (bắt buộc đạt), **S** = Should (nên có), **C** = Could (nếu còn thời gian).

## A. Thu hình và phần cứng
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| A1 | Thu khung hình từ camera bằng Picamera2, >= 15 fps ở 720p cho luồng phân tích | M |
| A2 | Điều khiển autofocus: lấy nét theo vùng (AfWindows) + trigger trước khi chụp trang | M |
| A3 | Xác định và ghi lại vị trí/góc lắp camera tối ưu (khung chứa đầu-vai và vùng viết) kèm ảnh minh họa | M |
| A4 | Tách lớp suy luận để thay CPU bằng Hailo sau này | S |
| A5 | Hỗ trợ camera thứ 2 qua cấu hình (không cần dùng ngay) | C |

## B. Tư thế và tập trung (chạy cục bộ)
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| B1 | Ước lượng tư thế, tính >= 3 chỉ số: góc gập cổ, nghiêng vai, khoảng cách đầu-mặt bàn (hoặc proxy) | M |
| B2 | Phát hiện "tư thế xấu kéo dài" với ngưỡng và thời gian kéo dài cấu hình được (mặc định 10 giây) | M |
| B3 | Phát hiện nhắm mắt kéo dài (EAR) và quay đầu rời bàn học kéo dài | S |
| B4 | Cơ chế chống báo nhầm: debounce, cooldown giữa các lần nhắc (mặc định >= 2 phút) | M |
| B5 | Đo lường fps/độ trễ/CPU/nhiệt độ ghi log | M |

## C. Đọc nội dung trang
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| C1 | Tự phát hiện trang sách/vở trong khung, cắt và làm phẳng (deskew) | M |
| C2 | Phát hiện "trang ổn định" (không bị tay che, không rung) để quyết định thời điểm chụp | M |
| C3 | Cổng riêng tư: chặn gửi nếu ảnh cắt có mặt/vùng da vượt ngưỡng; ghi log lý do chặn (không lưu ảnh) | M |
| C4 | Chụp lại tự động khi bị chặn hoặc mờ (tối đa N lần, sau đó báo "chưa đọc được") | S |
| C5 | Đánh giá độ nét/độ sáng ảnh trước khi gửi (Laplacian variance) | S |

## D. Tích hợp LLM
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| D1 | Gửi ảnh trang đã cắt + ngữ cảnh (môn, lớp, câu hỏi của trẻ) đến API vision, nhận phản hồi giảng giải | M |
| D2 | Prompt hệ thống riêng cho lứa 6-12 tuổi, có chế độ "gợi ý từng bước", kiểm thử >= 20 tình huống | M |
| D3 | Xử lý lỗi mạng, timeout, retry; hoạt động suy giảm êm (vẫn nhắc tư thế khi mất mạng) | M |
| D4 | Ghi chi phí/token/độ trễ mỗi lần gọi | M |
| D5 | Tùy chọn đổi nhà cung cấp (Claude/OpenAI) qua cấu hình | S |
| D6 | Phát hiện nội dung cần người lớn (trẻ nhắc tới buồn bã, khó khăn nghiêm trọng) và gắn cờ escalation | S |

## E. Nền tảng phụ huynh/giáo viên (tối giản)
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| E1 | Robot gửi sự kiện dạng văn bản/số lên server (HTTP hoặc MQTT) | M |
| E2 | Server (FastAPI + SQLite/PostgreSQL) lưu sự kiện, **từ chối mọi payload chứa ảnh** | M |
| E3 | Dashboard web: thời lượng học, số lần nhắc tư thế, các bài đã hỗ trợ, cờ cần can thiệp | M |
| E4 | Phụ huynh gửi "yêu cầu" xuống robot (ví dụ lời nhắc tùy chỉnh) | C |
| E5 | Đăng nhập đơn giản, phân quyền phụ huynh/giáo viên | S |

## F. Giọng nói và biểu cảm
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| F1 | Phát lời nhắc/giảng giải bằng TTS (tiếng Việt) | S |
| F2 | Nhận câu hỏi bằng giọng nói (STT) | C |
| F3 | Màn hình/LED biểu cảm đơn giản | C |

## G. Riêng tư và độ tin cậy (xuyên suốt)
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| G1 | Không ghi ảnh/video ra đĩa trong luồng vận hành (có test tự động kiểm chứng) | M |
| G2 | Không có mã nhận diện danh tính (review code cuối đề tài) | M |
| G3 | Cấu hình, key, ngưỡng tách khỏi code | M |
| G4 | Chạy ổn định 2 giờ liên tục; tự khởi động lại dịch vụ khi lỗi (systemd) | S |
| G5 | Log có mức độ, không chứa dữ liệu ảnh/nội dung bài nhạy cảm | M |
