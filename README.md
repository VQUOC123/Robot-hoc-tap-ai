# Robot Trợ Lý Học Tập AI Cho Trẻ 6–12 Tuổi (POC)

Hệ thống Robot trợ lý học tập AI chạy trên Raspberry Pi 5 kết hợp Computer Vision tại biên (Edge AI) và LLM Vision trên đám mây, tuân thủ nghiêm ngặt nguyên tắc **Privacy by Design** (Luật bảo vệ dữ liệu cá nhân 2026: 0 byte ảnh ghi đĩa, server chặn payload ảnh 422).

---

## 📚 Mục lục tài liệu dự án

| File | Nội dung chính |
|---|---|
| [AI_CONTEXT.md](file:///AI_CONTEXT.md) | Tài liệu tóm tắt kiến trúc, dòng mã, biến trạng thái phục vụ AI Agent Handoff |
| [00_README.md](file:///00_README.md) | Giới thiệu tổng quan gói bàn giao POC |
| [01_Brief_va_Pham_vi.md](file:///01_Brief_va_Pham_vi.md) | Mục tiêu, phạm vi & nguyên tắc bảo mật bắt buộc |
| [02_Kien_thuc_nen_tang.md](file:///02_Kien_thuc_nen_tang.md) | Nền tảng phần cứng Pi 5, camera, AI & pháp lý |
| [03_Yeu_cau_tinh_nang.md](file:///03_Yeu_cau_tinh_nang.md) | Danh sách tính năng, ưu tiên F01–F10 |
| [04_Kien_truc_he_thong.md](file:///04_Kien_truc_he_thong.md) | Kiến trúc Edge / Cloud, State Machine & Luồng dữ liệu |
| [05_Ke_hoach_8_tuan.md](file:///05_Ke_hoach_8_tuan.md) | Kế hoạch chi tiết 8 tuần phát triển |
| [06_Tieu_chi_nghiem_thu.md](file:///06_Tieu_chi_nghiem_thu.md) | Tiêu chí nghiệm thu & phương pháp đo đạc |
| [07_Mau_bao_cao_tuan.md](file:///07_Mau_bao_cao_tuan.md) | Mẫu báo cáo tuần & biên bản thử nghiệm |
| [Y_TUONG_SANG_TAO_ROBOT.md](file:///Y_TUONG_SANG_TAO_ROBOT.md) | Ý tưởng sáng tạo: Emotion Engine, giải lao Gen Alpha, Socratic Tutoring |
| [project_knowledge.md](file:///project_knowledge.md) | Cẩm nang kiến thức hệ thống & checklist Q1–Q13 |

---

## 📂 Cấu trúc mã nguồn

- **`Thay_Code/ai-tutor/`**: Ứng dụng AI biên trên Raspberry Pi 5 (MediaPipe Pose/Face/Hands, DrowsinessTracker, HomeworkMonitor, gTTS, LLM Vision multi-provider).
- **`Thay_Code/tutor-airobot-be/`**: Backend API viết bằng Golang + PostgreSQL quản lý thiết bị, thống kê và prompts.
- **`Thay_Code/tutor-airobot-fe/`**: Frontend Dashboard phụ huynh/giáo viên viết bằng Vue/React + Vite + Tailwind CSS.
- **`hardware_img/`**: Hình ảnh linh kiện, Raspberry Pi 5, Active Cooler, cáp và module camera AI.
