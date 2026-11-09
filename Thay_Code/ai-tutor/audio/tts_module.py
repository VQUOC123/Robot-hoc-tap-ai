# audio/tts_module.py
import subprocess
import os
import tempfile
import threading
from pathlib import Path


class TTSModule:
    """
    Text to Speech Module
    Hỗ trợ: gTTS (online) + espeak (offline fallback)
    Sẵn sàng tích hợp AI sau này
    """

    def __init__(self):
        self.is_speaking    = False
        self._lock          = threading.Lock()
        self._use_gtts      = self._check_gtts()
        self._check_audio()
        print("✅ TTS Module sẵn sàng!")

    def _check_gtts(self):
        """Kiểm tra gTTS có available không"""
        try:
            from gtts import gTTS
            return True
        except ImportError:
            print("⚠️ gTTS chưa cài → Dùng espeak")
            return False

    def _check_audio(self):
        """Kiểm tra audio output"""
        try:
            result = subprocess.run(
                ['aplay', '-l'],
                capture_output=True,
                text=True
            )
            if result.stdout:
                print("✅ Audio device tìm thấy")
            else:
                print("⚠️ Không tìm thấy audio device")
        except FileNotFoundError:
            print("⚠️ aplay không tìm thấy")

    # ── Public Methods ───────────────────────────────

    def speak(self, text: str,
              lang: str = 'vi',
              async_mode: bool = True,
              priority: bool = False):
        """
        Đọc text thành giọng nói

        Args:
            text: Nội dung cần đọc
            lang: Ngôn ngữ (vi/en)
            async_mode: True = không chờ xong
            priority: True = ngắt giọng đang đọc
        """
        if not text or not text.strip():
            return

        # Ngắt giọng hiện tại nếu priority
        if priority and self.is_speaking:
            self._stop_current()

        # Không đọc đè nếu đang đọc
        if self.is_speaking and not priority:
            return

        if async_mode:
            t = threading.Thread(
                target=self._speak_sync,
                args=(text, lang),
                daemon=True
            )
            t.start()
        else:
            self._speak_sync(text, lang)

    def speak_for_ai(self, text: str,
                     lang: str = 'vi'):
        """
        Method dành riêng cho AI module gọi
        Luôn async, có thể interrupt
        Sẵn sàng để AI tích hợp sau
        """
        self.speak(
            text,
            lang=lang,
            async_mode=True,
            priority=True
        )

    # ── Private Methods ──────────────────────────────

    def _speak_sync(self, text: str, lang: str):
        """Đọc giọng nói - synchronous"""
        with self._lock:
            self.is_speaking = True

        temp_path = None
        try:
            if self._use_gtts:
                temp_path = self._speak_gtts(
                    text, lang
                )
            else:
                self._speak_espeak(text, lang)

        except Exception as e:
            print(f"❌ Lỗi TTS gTTS: {e}")
            # Fallback espeak
            try:
                self._speak_espeak(text, lang)
            except Exception as e2:
                print(f"❌ Lỗi TTS espeak: {e2}")
                print(f"[TTS]: {text}")
        finally:
            self.is_speaking = False
            if temp_path and \
               os.path.exists(temp_path):
                os.unlink(temp_path)

    def _speak_gtts(self, text: str,
                    lang: str) -> str:
        """Dùng Google TTS (cần internet)"""
        from gtts import gTTS

        tts = gTTS(text=text, lang=lang, slow=False)
        with tempfile.NamedTemporaryFile(
            delete=False, suffix='.mp3'
        ) as f:
            temp_path = f.name

        tts.save(temp_path)

        subprocess.run(
            ['mpg321', '-q', temp_path],
            capture_output=True
        )
        return temp_path

    def _speak_espeak(self, text: str, lang: str):
        """Dùng espeak (offline)"""
        voice = 'vi' if lang == 'vi' else 'en'
        subprocess.run(
            ['espeak-ng',
             '-v', voice,
             '-s', '145',
             '-a', '150',
             text],
            capture_output=True
        )

    def _stop_current(self):
        """Dừng giọng đang phát"""
        try:
            subprocess.run(
                ['pkill', 'mpg321'],
                capture_output=True
            )
            subprocess.run(
                ['pkill', 'espeak-ng'],
                capture_output=True
            )
        except Exception:
            pass
        self.is_speaking = False