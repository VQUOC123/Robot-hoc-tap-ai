# analyzers/homework_monitor.py
"""
HomeworkMonitor — Theo dõi trạng thái làm bài tập của học sinh.

State machine:
  IDLE       → Chưa phát hiện làm bài đủ lâu
  REQUESTING → Đang hỏi học sinh "Cho thầy xem bài?" (countdown)
  CAPTURED   → Đã chụp được ảnh, sẵn sàng gửi AI
  COOLDOWN   → Đợi cooldown trước khi hỏi lại

Transitions:
  IDLE       → REQUESTING : sustained homework >= HOMEWORK_DETECT_DURATION
  REQUESTING → CAPTURED   : auto-capture khi homework_visible đủ lâu + quality OK
                            hoặc user click "Chụp hình" (manual, bỏ qua quality gate)
  REQUESTING → IDLE       : timeout > HOMEWORK_REQUEST_TIMEOUT
  CAPTURED   → COOLDOWN   : user click "Phân tích AI"
  COOLDOWN   → IDLE       : elapsed >= HOMEWORK_COOLDOWN

Quality gate (auto-capture only):
  assess_image_quality() kiểm tra blur, brightness trước khi accept.
  Thử lại tối đa HOMEWORK_QUALITY_RETRIES lần, sau đó chụp dù chất lượng kém.
  Manual capture luôn chụp ngay (user đã chọn frame này).
"""

import time
import cv2
import base64

from core import constants as C
from core.config import Config
from utils.image_utils import assess_image_quality


# Activity nào được tính là "đang làm bài tập"
HOMEWORK_ACTIVITIES = {
    C.ACTIVITY_WRITING_NOTES,
    C.ACTIVITY_READING,
    C.ACTIVITY_FOCUSED_STUDYING,
}


class HomeworkState:
    IDLE       = "idle"
    REQUESTING = "requesting"
    CAPTURED   = "captured"
    COOLDOWN   = "cooldown"


class HomeworkMonitor:
    """
    Theo dõi trạng thái làm bài tập theo state machine.

    Usage (trong main loop):
        monitor.update(activity, homework_visible, frame_bgr)  # → dict cho UI

    Khi user click "Chụp hình" (manual):
        ok = monitor.do_capture(raw_frame_bgr)   # → True nếu thành công

    Khi user click "Phân tích AI":
        image_b64 = monitor.trigger_analyze()    # → base64 để gửi AI
    """

    def __init__(self):
        self.state        = HomeworkState.IDLE
        self._sustained_t = 0.0    # Giây làm bài liên tục
        self._request_t   = 0.0    # Thời điểm bắt đầu REQUESTING
        self._cooldown_t  = 0.0    # Thời điểm bắt đầu cooldown
        self._last_t      = time.time()

        self._captured_b64 = None  # Base64 ảnh đã chụp
        self._analysis     = None  # Kết quả AI phân tích

        # Auto-capture: frame counter khi homework_visible=True liên tiếp
        self._auto_capture_frames = 0

        # Sticky visible: lưu timestamp lần cuối homework_visible=True.
        # _update_idle dùng để tránh decay ngay khi homework_visible bị False 1-2 frames.
        self._last_homework_visible_t = 0.0

        # Quality gate (auto-capture)
        self._quality_retries  = 0
        self._quality_warn_msg = ""   # Lý do fail để hiện lên UI

        # Ngưỡng từ Config (có thể override qua .env)
        self._detect_dur              = Config.HOMEWORK_DETECT_DURATION
        self._timeout                 = Config.HOMEWORK_REQUEST_TIMEOUT
        self._cooldown_dur            = Config.HOMEWORK_COOLDOWN
        self._AUTO_CAPTURE_FRAMES     = Config.HOMEWORK_AUTO_CAPTURE_FRAMES
        self._MAX_QUALITY_RETRIES     = Config.HOMEWORK_QUALITY_RETRIES
        self._request_msg             = getattr(C, 'HOMEWORK_REQUEST_MSG',
                                                "Bạn đang làm bài tập phải không? "
                                                "Cho thầy xem bài với nhé! 📖")

        print("✅ HomeworkMonitor sẵn sàng!")

    # ── Public API ────────────────────────────────────────────────────

    def update(self, activity: str,
               homework_visible: bool = False,
               frame=None) -> dict:
        """
        Cập nhật state mỗi frame.

        Args:
            activity         : final_activity từ ActivityAnalyzer
            homework_visible : True khi writing_score >= min AND has_book/notepaper
            frame            : BGR frame để auto-capture (None = không auto-capture)

        Returns: dict trạng thái cho UI
        """
        now = time.time()
        dt  = now - self._last_t
        self._last_t = now

        is_homework = activity in HOMEWORK_ACTIVITIES

        if self.state == HomeworkState.IDLE:
            self._update_idle(is_homework, homework_visible, dt, now)

        elif self.state == HomeworkState.REQUESTING:
            self._update_requesting(now, homework_visible, frame)

        elif self.state == HomeworkState.CAPTURED:
            pass   # Chờ user click "Phân tích AI"

        elif self.state == HomeworkState.COOLDOWN:
            self._update_cooldown(now)

        return self._build_status(now, homework_visible)

    def do_capture(self, frame_bgr) -> bool:
        """
        Gọi khi user bấm "Chụp hình" trong REQUESTING state.
        Manual capture — không áp dụng quality gate, chụp ngay.
        Vẫn kiểm tra quality để hiển thị cảnh báo trên UI.

        Returns True nếu encode thành công.
        """
        if self.state != HomeworkState.REQUESTING:
            return False

        # Kiểm tra quality để lấy warning message (không block capture)
        quality = assess_image_quality(frame_bgr)
        if not quality.is_acceptable:
            self._quality_warn_msg = self._build_quality_warn(quality, prefix="⚠️ ")
        else:
            self._quality_warn_msg = ""

        self._do_encode(frame_bgr)
        if self._captured_b64:
            self._quality_retries  = 0
            self._auto_capture_frames = 0
            self.state = HomeworkState.CAPTURED
            return True
        return False

    def trigger_analyze(self) -> str | None:
        """
        Gọi khi user bấm "Phân tích AI".
        Returns base64 image nếu có ảnh, None nếu không.
        Chuyển state → COOLDOWN.
        """
        if self.state == HomeworkState.CAPTURED and self._captured_b64:
            b64 = self._captured_b64
            self._captured_b64     = None
            self._quality_warn_msg = ""
            self._cooldown_t       = time.time()
            self.state             = HomeworkState.COOLDOWN
            print("[HomeworkMonitor] → COOLDOWN: Đã gửi ảnh để phân tích")
            return b64
        return None

    def set_analysis(self, result: dict):
        """Lưu kết quả AI để hiển thị trên UI."""
        self._analysis = result

    def get_state(self) -> str:
        return self.state

    # ── Private: state handlers ───────────────────────────────────────

    def _update_idle(self, is_homework: bool, homework_visible: bool,
                     dt: float, now: float):
        # Tích lũy khi activity thuộc HOMEWORK_ACTIVITIES HOẶC khi homework_visible=True.
        # Lý do: học sinh có thể bị classify là working_computer (vì có màn hình laptop
        # trước mặt) trong khi thực tế đang viết bài tập. homework_visible dựa trên
        # weighted confidence (pen + writing motion + gaze) nên đủ tin cậy để dùng riêng.

        # Sticky: lưu timestamp khi homework_visible=True.
        # recent_hw_visible = True trong 3s sau lần cuối detect, tránh decay ngay
        # khi hand detector dao động 1-2 frame gây homework_visible=False tạm thời.
        if homework_visible:
            self._last_homework_visible_t = now
        recent_hw_visible = (now - self._last_homework_visible_t) < 3.0

        if is_homework or recent_hw_visible:
            # homework_visible tích lũy nhanh hơn 1.5× (bài tập nhìn rõ)
            increment = dt * 1.5 if homework_visible else dt
            self._sustained_t += increment
            if self._sustained_t >= self._detect_dur:
                self._request_t       = now
                self._analysis        = None
                self._quality_retries = 0
                self._quality_warn_msg = ""
                self._auto_capture_frames = 0
                self.state            = HomeworkState.REQUESTING
                print(f"[HomeworkMonitor] → REQUESTING "
                      f"(sustained {self._sustained_t:.1f}s)")
        else:
            # Decay nhanh khi không làm bài
            self._sustained_t = max(0.0, self._sustained_t - dt * 2)

    def _update_requesting(self, now: float, homework_visible: bool, frame):
        elapsed   = now - self._request_t
        remaining = self._timeout - elapsed

        # Auto-capture: tích lũy frame khi homework_visible=True
        if homework_visible and frame is not None:
            self._auto_capture_frames += 1
            if self._auto_capture_frames >= self._AUTO_CAPTURE_FRAMES:
                self._try_auto_capture(frame)
                if self.state == HomeworkState.CAPTURED:
                    return
        else:
            self._auto_capture_frames = max(0, self._auto_capture_frames - 1)

        if remaining <= 0:
            # Timeout — giữ 50% progress để không phải đợi lại từ đầu
            self._sustained_t         = self._detect_dur * 0.5
            self._auto_capture_frames = 0
            self._quality_retries     = 0
            self._quality_warn_msg    = ""
            self.state                = HomeworkState.IDLE
            print("[HomeworkMonitor] → IDLE: Timeout, user không chụp")

    def _try_auto_capture(self, frame):
        """
        Auto-capture với quality gate.

        Nếu quality fail: retry tối đa _MAX_QUALITY_RETRIES lần.
        Sau max retries: chụp dù chất lượng không đạt (không block mãi).
        """
        quality = assess_image_quality(frame)

        if quality.is_acceptable or self._quality_retries >= self._MAX_QUALITY_RETRIES:
            # Chụp: quality OK, hoặc đã hết số lần retry
            if not quality.is_acceptable:
                print(f"[HomeworkMonitor] Quality gate: max retries, chụp dù chất lượng kém")
            self._do_encode(frame)
            if self._captured_b64:
                self._quality_retries  = 0
                self._quality_warn_msg = ("" if quality.is_acceptable
                                          else self._build_quality_warn(quality, prefix="⚠️ "))
                self._auto_capture_frames = 0
                self.state = HomeworkState.CAPTURED
                print("[HomeworkMonitor] → CAPTURED: Auto-capture"
                      f" (retries={self._quality_retries})")
        else:
            # Quality fail, thử lại
            self._quality_retries    += 1
            self._auto_capture_frames = 0   # reset để chờ thêm AUTO_CAPTURE_FRAMES frame nữa
            self._quality_warn_msg    = self._build_quality_warn(quality)
            print(f"[HomeworkMonitor] Quality fail "
                  f"({self._quality_retries}/{self._MAX_QUALITY_RETRIES}): "
                  f"{self._quality_warn_msg} "
                  f"(blur={quality.blur_score:.0f} bright={quality.brightness:.0f})")

    def _build_quality_warn(self, quality, prefix: str = "") -> str:
        """Tạo message mô tả lý do quality fail."""
        reasons = []
        if quality.blur_score < Config.IMAGE_QUALITY_MIN_BLUR_SCORE:
            reasons.append("ảnh mờ")
        if quality.brightness < Config.IMAGE_QUALITY_MIN_BRIGHTNESS:
            reasons.append("quá tối")
        elif quality.brightness > Config.IMAGE_QUALITY_MAX_BRIGHTNESS:
            reasons.append("quá sáng")
        if not reasons:
            reasons.append("chất lượng chưa đạt")
        return prefix + ", ".join(reasons)

    def _update_cooldown(self, now: float):
        if now - self._cooldown_t >= self._cooldown_dur:
            self._sustained_t = 0.0
            self.state        = HomeworkState.IDLE
            print("[HomeworkMonitor] → IDLE: Cooldown xong")

    def _do_encode(self, frame_bgr):
        """Encode frame → base64 JPEG."""
        ret, buf = cv2.imencode(
            '.jpg', frame_bgr,
            [cv2.IMWRITE_JPEG_QUALITY, 92]
        )
        if ret:
            self._captured_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
            print("[HomeworkMonitor] Đã encode ảnh bài tập")

    # ── Build UI status ───────────────────────────────────────────────

    def _build_status(self, now: float, homework_visible: bool = False) -> dict:
        base = {
            "state"        : self.state,
            "message"      : "",
            "countdown"    : 0,
            "progress"     : 0,         # 0-100, % tiến độ detect trong IDLE
            "has_image"    : self._captured_b64 is not None,
            "analysis"     : self._analysis,
            "book_visible" : homework_visible,
            "quality_warn" : self._quality_warn_msg,  # "" = không có vấn đề gì
        }

        if self.state == HomeworkState.IDLE:
            pct = min(100, int(self._sustained_t / self._detect_dur * 100))
            base["progress"] = pct

        elif self.state == HomeworkState.REQUESTING:
            elapsed   = now - self._request_t
            remaining = max(0, int(self._timeout - elapsed))
            base["message"]   = self._request_msg
            base["countdown"] = remaining
            # Tiến độ auto-capture (0-100%)
            if self._AUTO_CAPTURE_FRAMES > 0:
                base["auto_capture_pct"] = min(
                    100, int(self._auto_capture_frames / self._AUTO_CAPTURE_FRAMES * 100)
                )

        elif self.state == HomeworkState.CAPTURED:
            if self._quality_warn_msg:
                base["message"] = f"✅ Đã chụp! ({self._quality_warn_msg})"
            else:
                base["message"] = "✅ Đã chụp bài tập! Bấm 'Phân tích' để gửi AI."

        elif self.state == HomeworkState.COOLDOWN:
            elapsed   = now - self._cooldown_t
            remaining = max(0, int(self._cooldown_dur - elapsed))
            base["message"] = f"Đã phân tích xong. Hỏi lại sau {remaining}s."

        return base
