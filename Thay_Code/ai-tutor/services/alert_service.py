# services/alert_service.py
"""
AlertService — Tập trung tất cả TTS alerts.

Wrapper domain-specific trên audio.tts_module.TTSModule.
Thêm debounce để không spam alerts liên tục mỗi frame.

Usage:
    alerts = AlertService()
    alerts.prompt_homework()          # "Em giơ bài tập lên..."
    alerts.alert_phone()              # "Hãy cất điện thoại..."
    alerts.alert_distracted(seconds)  # "Mất tập trung rồi..."
"""
import time


class AlertService:
    def __init__(self, enabled: bool = True,
                 phone_delay: float = 30.0,
                 distract_delay: float = 20.0,
                 tts_speed: int = 140):
        self._enabled        = enabled
        self._phone_delay    = phone_delay
        self._distract_delay = distract_delay
        self._tts            = None

        # Timestamps of last alert per category (debounce)
        self._last_phone_t    = 0.0
        self._last_distract_t = 0.0
        self._last_sleep_t    = 0.0

        # Last spoken message — luôn lưu dù TTS bật hay tắt, để hiển thị trên UI
        self._last_msg  : str   = ""
        self._last_msg_t: float = 0.0

        if enabled:
            try:
                from audio.tts_module import TTSModule
                self._tts = TTSModule()
                print("✅ AlertService sẵn sàng (TTS bật)")
            except Exception as e:
                print(f"⚠️ AlertService: Không khởi tạo được TTSModule — {e}")
        else:
            print("ℹ️ AlertService: TTS tắt (TTS_ENABLED=false)")

    # ── Core speak ────────────────────────────────────────────────────

    def speak(self, text: str, interrupt: bool = False) -> None:
        """Non-blocking TTS. interrupt=True để ngắt giọng đang đọc.
        Luôn lưu message vào _last_msg dù TTS bật hay tắt — để hiển thị trên UI."""
        self._last_msg   = text
        self._last_msg_t = time.time()
        if not self._enabled or not self._tts:
            return
        self._tts.speak(text, lang='vi', async_mode=True, priority=interrupt)

    def get_last_alert(self) -> dict | None:
        """
        Trả về alert cuối cùng nếu còn trong window 8 giây, dùng cho UI toast.
        Returns: {"text": str, "age": float} hoặc None nếu không có / đã cũ.
        """
        if not self._last_msg:
            return None
        age = time.time() - self._last_msg_t
        if age > 8.0:
            return None
        return {"text": self._last_msg, "age": round(age, 1)}

    # ── Domain-specific alerts ────────────────────────────────────────

    def prompt_homework(self) -> None:
        """Nhắc học sinh giơ bài tập lên để chụp (mỗi lần vào REQUESTING)."""
        self.speak("Em giơ bài tập lên cho thầy cô xem với nhé!")

    def alert_quality_fail(self) -> None:
        """Ảnh mờ hoặc tối → yêu cầu giơ bài rõ hơn."""
        self.speak("Ảnh chưa rõ lắm, em giơ bài cao hơn và gần hơn nhé!")

    def confirm_captured(self) -> None:
        """Xác nhận đã chụp ảnh bài tập thành công."""
        self.speak("Đã chụp bài tập! Đang phân tích...")

    def alert_phone(self, name: str = "") -> bool:
        """
        Cảnh báo dùng điện thoại (có debounce).
        Returns True nếu đã phát âm, False nếu bị debounce.
        """
        now = time.time()
        if now - self._last_phone_t < self._phone_delay:
            return False
        self._last_phone_t = now
        who = name + " ơi, " if name else ""
        self.speak(f"{who}hãy cất điện thoại và tập trung học nào!", interrupt=True)
        return True

    def alert_distracted(self, seconds: int = 0, name: str = "") -> bool:
        """
        Nhắc khi mất tập trung kéo dài (có debounce).
        Returns True nếu đã phát âm.
        """
        now = time.time()
        if now - self._last_distract_t < self._distract_delay:
            return False
        self._last_distract_t = now
        who = name + " ơi, " if name else ""
        self.speak(f"{who}tập trung vào bài học nhé!", interrupt=True)
        return True

    def alert_sleeping(self, name: str = "") -> bool:
        """
        Cảnh báo ngủ gật (debounce 60s — không hét mỗi giây).
        Returns True nếu đã phát âm.
        """
        now = time.time()
        if now - self._last_sleep_t < 60.0:
            return False
        self._last_sleep_t = now
        who = name + " ơi! " if name else ""
        self.speak(f"{who}Tỉnh dậy và tiếp tục học nào!", interrupt=True)
        return True
