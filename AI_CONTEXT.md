# AI_CONTEXT — Robot Học Tập (AI Study Assistant)
> **AI Handoff Instructions**: Read this file first. Use the Line-Range Index in Section 2 to read only targeted line slices (`StartLine`/`EndLine`) instead of full files. Update this file after every code change.

## 1. Overview, Stack & Commands
- **Purpose**: Hệ thống Robot trợ lý học tập AI cho trẻ 6–12 tuổi (POC 8 tuần) trên Raspberry Pi 5. Giám sát tư thế ngồi, cắt trang vở đọc bài qua LLM Vision, tuân thủ Privacy-by-Design (Luật bảo vệ dữ liệu cá nhân 2026: 0 byte ảnh ghi đĩa, server chặn payload ảnh 422).
- **Git Repository**: `https://github.com/VQUOC123/Robot-hoc-tap-ai.git` (Remote `origin`, branch `main`).
- **Core Educational Persona**: Robot đóng vai "vừa là Thầy Cô uyên bác, vừa là Bạn Thân đồng hành" — ưu tiên số 1 là giữ tâm trạng bé luôn thoải mái, giảm stress tối đa, không tạo áp lực sợ hãi, khích lệ tự tin.
- **Reference Base (Thay_Code)**: Đã trích xuất thành công 3 project của Thầy từ thẻ nhớ vào `Thay_Code/`:
  1. `ai-tutor/`: Python edge app chạy trên Pi 5 (MediaPipe Face/Hands/Pose + YOLO, Drowsiness, HomeworkMonitor, gTTS/espeak, LLM multi-provider).
  2. `tutor-airobot-be/`: Golang backend API + PostgreSQL.
  3. `tutor-airobot-fe/`: React + Vite + Tailwind admin dashboard.
- **Strategy & Policy**: Kế thừa module phần cứng/camera/TTS từ code Thầy; tái cấu trúc module AI tư thế và Socratic tutoring theo hướng nhẹ hơn (bỏ bớt YOLO nặng nếu thừa), cấy Emotion Engine, Privacy Gate lọc mặt/da, và cơ chế giải lao / mini-game bắt trend Gen Alpha.
- **Stack / Runtime**: Python 3.14 (venv), Google MediaPipe 0.10.35, OpenCV 4.9+, Picamera2, FastAPI, Pydantic v2, Uvicorn, Anthropic/OpenAI Vision SDK.

## 2. File & Line-Range Symbol Index
| File | Line Range | Symbols / Selectors | Responsibility |
|---|---|---|---|
| `Thay_Code/ai-tutor/main.py` | `L1-L300` | `main()`, `AITutor` | Core loop của Thầy chạy trên Pi 5 |
| `Thay_Code/ai-tutor/detectors/` | Full | `FaceDetector`, `PoseDetector`, `HandDetector` | Các bộ trích xuất mốc cơ thể và tay |
| `Thay_Code/ai-tutor/analyzers/` | Full | `HomeworkMonitor`, `DrowsinessTracker` | Logic theo dõi trạng thái học và buồn ngủ |
| `Thay_Code/ai-tutor/audio/` | Full | `TTSModule`, `STTModule` | Điều khiển loa I2S phát âm thanh tiếng Việt |
| `Thay_Code/ai-tutor/ai/` | Full | `AIModule` | Client gọi OpenAI, Claude, Gemini, OpenRouter |
| `Y_TUONG_SANG_TAO_ROBOT.md` | `L1-L150` | Toàn bộ ý tưởng sáng tạo | Cơ chế dò sóng sở thích, mini-game giải lao thông minh, giọng nói cảm xúc & Socratic tutoring |
| `project_knowledge.md` | `L1-L320` | Toàn văn kiến thức tuần 1-8 | Tài liệu nền tảng kiến thức hệ thống, công thức góc, schema, checklist Q1-Q13 |
| `Timeline_3_Nhom.md` | `L1-L170` | Phân công 3 nhóm (BE, Training AI, Web & Service) | Timeline nhiệm vụ 8 tuần chi tiết theo STT, phân công và đầu ra |
| `timeline-8-tuan-chi-tiet.md` | `L1-L206` | Kế hoạch tuần 1-8 mở rộng | Khung phân công, giai đoạn triển khai và mốc demo |
| `ai_core/posture_math.py` | `L1-L45` | `calculate_angle_2d`, `calculate_shoulder_tilt`, `calculate_neck_tilt` | Module tính góc cột sống/gập cổ thuần tự code của nhóm |
| `ai_core/posture_tracker.py` | `L1-L60` | `PostureDebounceTracker` | Quản lý state machine Debounce 10s & Cooldown 2 phút chuẩn Q2 |
| `ai_core/main_monitor.py` | `L1-L100` | `run_posture_monitor` | Ứng dụng AI biên Pose Landmarker tích hợp HUD giám sát tư thế cho Tuần 1-3 |
| `ai_core/llm_socratic.py` | `L1-L50` | `SOCRATIC_SYSTEM_PROMPT`, `SAMPLE_TEST_SCENARIOS` | Khung Prompt sư phạm gợi mở & kịch bản kiểm thử Tuần 3 |

## 3. Architecture, State & Critical Invariants
- **Privacy by Design**:
  - **Q10**: 0 byte ảnh/video được ghi xuống ổ đĩa trong luồng vận hành (chỉ lưu RAM Ring Buffer).
  - **Q11**: Server FastAPI dùng `model_config = ConfigDict(extra='forbid')`, ném lỗi HTTP 422 khi nhận payload có trường ảnh.
  - **Không nhận diện khuôn mặt**: Chỉ lấy pose landmark và eye aspect ratio (EAR).
  - **Privacy Gate**: Cắt trang phẳng (deskew), chặn gửi cloud nếu mặt hoặc diện tích da tay > 15%.
- **Edge State Machine**: `IDLE` -> `OBSERVE` (5-10 FPS) -> `NUDGE` (Debounce >= 10s, Cooldown >= 2m) -> `CAPTURE_PAGE` -> `GATE` -> `ASK_LLM` -> `SPEAK`.

## 4. Completed Work Log (Features & Bugfixes)
- **[Extracted Teacher's Codebase]**:
  - Đã mount thành công phân vùng `rootfs` từ thẻ nhớ microSD 64GB.
  - Đã copy trọn vẹn 3 dự án cốt lõi của Thầy vào thư mục `Thay_Code/`: `ai-tutor`, `tutor-airobot-be`, `tutor-airobot-fe`.
  - Phân tích kiến trúc mã nguồn của Thầy: MediaPipe + YOLO + gTTS + Claude/OpenAI multi-provider.
- **[Git Initialization & Repository Setup]**:
  - Khởi tạo git repository, cấu hình remote `origin https://github.com/VQUOC123/Robot-hoc-tap-ai.git`.
  - Thiết lập `.gitignore` bảo vệ API keys (`.env`), loại bỏ file nén SD card khổng lồ (>3.4GB), `venv` và `node_modules`.
  - Sao lưu lịch sử submodule vào `.git_backups/` và tích hợp toàn bộ source code vào repo chính.

- **[Git Sync & PR Merge Pull]**:
  - Đã pull thành công PR #1 (`585092b` merged by `PhanHoangAnh19`) từ nhánh `origin/main`.
  - Cập nhật 2 tài liệu kế hoạch phát triển mới: `Timeline_3_Nhom.md` và `timeline-8-tuan-chi-tiet.md` (phân bổ nhiệm vụ cho 3 nhóm BE, Training AI, Web & Service).
- **[Training AI Module Implementation (Tuần 1-2-3)]**:
  - Tự thiết kế và hiện thực module thuần của nhóm tại `ai_core/`: `posture_math.py`, `posture_tracker.py`, `main_monitor.py`, `llm_socratic.py`.
  - Không sao chép nguyên mẫu mã nguồn cũ của Thầy; tuân thủ chuẩn Google MediaPipe Tasks API v0.10.35, góc gập cổ >25°, lệch vai >10°, debounce 10s và cooldown 2 phút.

## 5. Current Status & Pending Roadmap
- **Status**: Nhóm Training AI (Quốc & Phúc) đã hoàn thiện bộ mã nguồn cốt lõi tuần 1-2-3 tại `ai_core/`, sẵn sàng test camera và tích hợp cho Mốc Demo M1.
- **Next Steps**:
  1. Quốc chạy kiểm thử trực tiếp camera với `python3 ai_core/main_monitor.py`.
  2. Bắn sự kiện JSON sang API của nhóm BE (Linh, Long, Quỳnh).
