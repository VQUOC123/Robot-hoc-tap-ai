# audio/stt_module.py
import subprocess
import threading
import queue
import os
import tempfile


class STTModule:
    """
    Speech to Text Module
    Hiện tại: Chuẩn bị sẵn cấu trúc
    Sau này: Tích hợp Whisper API hoặc
             Vosk (offline)
    """

    def __init__(self):
        self.is_listening   = False
        self.result_queue   = queue.Queue()
        self._callback      = None
        self._check_mic()
        print("✅ STT Module sẵn sàng!")

    def _check_mic(self):
        """Kiểm tra microphone"""
        try:
            result = subprocess.run(
                ['arecord', '-l'],
                capture_output=True,
                text=True
            )
            if 'card' in result.stdout.lower():
                print("✅ Microphone tìm thấy")
            else:
                print(
                    "⚠️ Không tìm thấy microphone\n"
                    "   STT sẽ không hoạt động\n"
                    "   Thêm USB mic để dùng tính năng này"
                )
        except FileNotFoundError:
            print("⚠️ arecord không tìm thấy")

    # ── Public Methods ───────────────────────────────

    def start_listening(self, callback=None,
                        duration: int = 5):
        """
        Bắt đầu lắng nghe microphone

        Args:
            callback: Hàm gọi khi có kết quả
                      callback(text: str)
            duration: Giây lắng nghe (0 = liên tục)
        """
        if self.is_listening:
            print("⚠️ Đang lắng nghe rồi!")
            return

        self._callback = callback
        self.is_listening = True

        t = threading.Thread(
            target=self._listen_loop,
            args=(duration,),
            daemon=True
        )
        t.start()

    def stop_listening(self):
        """Dừng lắng nghe"""
        self.is_listening = False

    def listen_once(self, duration: int = 5) -> str:
        """
        Lắng nghe 1 lần và trả về text
        Blocking call
        """
        return self._record_and_transcribe(duration)

    # ── Sẵn Sàng Cho AI ─────────────────────────────

    def listen_for_ai(self,
                      callback,
                      wake_word: str = "thầy ơi"):
        """
        Lắng nghe với wake word
        Chỉ gọi callback khi nghe thấy wake word
        Sẵn sàng để AI tích hợp sau

        Args:
            callback: Gọi với câu hỏi sau wake word
            wake_word: Từ kích hoạt
        """
        print(
            f"👂 Đang chờ wake word: '{wake_word}'"
        )
        # TODO: Implement wake word detection
        # Sẽ dùng Porcupine hoặc Vosk
        pass

    # ── Private Methods ──────────────────────────────

    def _listen_loop(self, duration: int):
        """Vòng lặp lắng nghe liên tục"""
        while self.is_listening:
            text = self._record_and_transcribe(
                duration
            )
            if text and self._callback:
                self._callback(text)

    def _record_and_transcribe(self,
                                duration: int = 5
                                ) -> str:
        """
        Ghi âm và chuyển thành text
        Hiện tại: Placeholder
        Sau này: Tích hợp Whisper/Vosk
        """
        temp_path = None
        try:
            # Tạo file tạm
            with tempfile.NamedTemporaryFile(
                delete=False, suffix='.wav'
            ) as f:
                temp_path = f.name

            # Ghi âm
            subprocess.run([
                'arecord',
                '-d', str(duration),
                '-f', 'cd',
                '-r', '16000',
                '-c', '1',
                temp_path
            ], capture_output=True)

            # TODO: Transcribe audio
            # Option 1: Whisper API (online)
            # Option 2: Vosk (offline)
            # Hiện tại return empty
            return ""

        except Exception as e:
            print(f"❌ Lỗi STT: {e}")
            return ""
        finally:
            if temp_path and \
               os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_status(self) -> dict:
        return {
            "is_listening": self.is_listening,
            "has_mic"     : True,
            "engine"      : "placeholder"
        }