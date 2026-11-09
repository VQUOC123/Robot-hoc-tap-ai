# AlertService TTS + Voice STT — Implementation Plan
> **Phụ thuộc:** Phase 3 (HomeworkMonitor) ✅ phải hoàn thành trước.
> **Ưu tiên:** AlertService TTS trước (không cần hardware mới), STT sau (cần USB mic).

---

## 1. AlertService — TTS (Text-to-Speech)

### 1.1 Hardware & Dependencies

| Item | Chi tiết |
|------|----------|
| Speaker | 3.5mm jack RPi5 hoặc USB speaker |
| `espeak-ng` | **Đã có sẵn** trong Raspberry Pi OS — không cần cài thêm |

**Test trước khi implement:**
```bash
espeak-ng -v vi -s 140 "Xin chào, đây là tiếng Việt"
# Nếu không nghe được: kiểm tra volume
amixer sset 'PCM' 80%
```

### 1.2 File cần tạo: `services/alert_service.py`

```python
# services/alert_service.py
"""
AlertService — Tập trung tất cả TTS alerts.

Dùng espeak-ng (offline, tiếng Việt) chạy non-blocking trong daemon thread.
Không cần cài thêm package.

Usage:
    alerts = AlertService()
    alerts.prompt_homework()          # "Em giơ bài tập lên..."
    alerts.alert_phone()              # "Hãy cất điện thoại..."
    alerts.alert_distracted(seconds)  # "Mất tập trung rồi..."
"""
import subprocess
import threading


_ESPEAK_CMD = ['/usr/bin/espeak-ng', '-v', 'vi', '-s', '140']


class AlertService:
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._lock    = threading.Lock()
        self._proc    = None   # Process hiện đang nói

    def speak(self, text: str, interrupt: bool = False) -> None:
        """
        Non-blocking TTS. Chạy espeak-ng trong daemon thread.

        Args:
            text      : Văn bản cần đọc (tiếng Việt).
            interrupt : True = ngắt giữa chừng nếu đang nói.
        """
        if not self._enabled:
            return
        if interrupt:
            self._stop_current()
        threading.Thread(
            target=self._speak_blocking,
            args=(text,),
            daemon=True,
        ).start()

    def _speak_blocking(self, text: str) -> None:
        proc = subprocess.Popen(
            _ESPEAK_CMD + [text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with self._lock:
            self._proc = proc
        proc.wait()
        with self._lock:
            if self._proc is proc:
                self._proc = None

    def _stop_current(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                self._proc = None

    # ── Domain-specific alerts ────────────────────────────────────────

    def prompt_homework(self) -> None:
        """Nhắc học sinh giơ bài tập lên để chụp."""
        self.speak("Em giơ bài tập lên cho thầy cô xem với nhé!")

    def alert_quality_fail(self) -> None:
        """Ảnh mờ hoặc tối → yêu cầu giơ bài rõ hơn."""
        self.speak("Ảnh chưa rõ lắm, em giơ bài cao hơn và gần hơn nhé!")

    def confirm_captured(self) -> None:
        """Xác nhận đã chụp ảnh bài tập thành công."""
        self.speak("Đã chụp bài tập! Đang phân tích...")

    def alert_phone(self, name: str = "") -> None:
        """Cảnh báo dùng điện thoại."""
        who = name + " ơi, " if name else ""
        self.speak(f"{who}hãy cất điện thoại và tập trung học nào!", interrupt=True)

    def alert_distracted(self, seconds: int = 0, name: str = "") -> None:
        """Nhắc khi mất tập trung kéo dài."""
        who = name + " ơi, " if name else ""
        self.speak(f"{who}tập trung vào bài học nhé!", interrupt=True)

    def alert_sleeping(self, name: str = "") -> None:
        """Cảnh báo ngủ gật."""
        who = name + " ơi! " if name else ""
        self.speak(f"{who}Tỉnh dậy và tiếp tục học nào!", interrupt=True)
```

### 1.3 Tích hợp vào `main.py`

```python
# main.py — thêm vào __init__:
from services.alert_service import AlertService
self.alerts = AlertService(enabled=Config.TTS_ENABLED)

# Trong main loop, sau khi có analysis + hw_status:
# Trigger khi HomeworkMonitor vào REQUESTING
if (hw_status["state"] == "requesting"
        and getattr(self, "_hw_was_requesting", False) is False):
    self.alerts.prompt_homework()
self._hw_was_requesting = (hw_status["state"] == "requesting")

# Trigger khi quality fail xuất hiện lần đầu
quality_warn = hw_status.get("quality_warn", "")
if quality_warn and not getattr(self, "_hw_quality_warned", False):
    self.alerts.alert_quality_fail()
self._hw_quality_warned = bool(quality_warn)
```

### 1.4 Constants cần thêm (`constants.py` Group 22)

```python
# ─── Group 22 — TTS / Alert Service ──────────────────────────────
TTS_ENABLED           = True    # Bật/tắt toàn bộ TTS (False nếu không có speaker)
TTS_SPEED             = 140     # Tốc độ đọc espeak-ng (từ/phút, 80-300)
TTS_VOICE             = "vi"    # Giọng đọc espeak-ng
TTS_PHONE_ALERT_DELAY = 30      # Giây giữa 2 lần alert phone (tránh spam)
TTS_DISTRACT_DELAY    = 20      # Giây giữa 2 lần alert distracted
```

**Override qua `.env`:**
```bash
TTS_ENABLED=false   # Tắt hoàn toàn nếu không có speaker
TTS_SPEED=120       # Chậm hơn nếu khó nghe
```

---

## 2. Voice STT — Speech-to-Text

### 2.1 Hardware cần có

**USB Microphone** — bất kỳ loại nào:
- Logitech USB desktop mic (~200-300k VND)
- Microphone tích hợp webcam USB
- Điện thoại kết nối qua phần mềm (DroidCam, WO Mic)

**Kiểm tra sau khi cắm:**
```bash
# Liệt kê thiết bị ghi âm
arecord -l

# Test ghi âm 3 giây
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 3 test.wav
aplay test.wav   # Nghe lại kiểm tra

# Nếu hw:1,0 không đúng → thay bằng device ID từ arecord -l
```

### 2.2 Chọn STT Engine

| Engine | RAM | Latency | Vi | Cài |
|--------|-----|---------|-----|-----|
| **Vosk small-vi** (khuyến nghị) | ~50MB | realtime | Tốt | `pip install vosk` + model 50MB |
| **faster-whisper tiny** | ~200MB | ~0.5s/clip | Tốt hơn | `pip install faster-whisper` |

**Khuyến nghị: Vosk small-vi** — nhẹ hơn, chạy realtime, đủ để detect hotwords.

**Cài Vosk:**
```bash
source venv/bin/activate
pip install vosk pyaudio

# Download model tiếng Việt (~50MB)
cd /home/pi/ai-tutor/models
wget https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip
unzip vosk-model-small-vn-0.4.zip
mv vosk-model-small-vn-0.4 vosk-vi
```

### 2.3 File cần tạo: `audio/stt_module.py`

```python
# audio/stt_module.py
"""
STTModule — Nhận dạng giọng nói để detect hotwords.

Dùng Vosk (offline, ~50MB) chạy realtime trong background thread.
Use case chính: phát hiện học sinh nói "xong rồi" / "báo cáo"
để trigger auto-capture homework mà không cần click.

Usage:
    stt = STTModule()
    stt.start()

    # Trong main loop:
    hotword = stt.get_hotword()   # None hoặc từ đã detect
    if hotword in ("xong", "xong rồi", "báo cáo"):
        homework_monitor.do_capture(frame)
"""
import threading
import queue
import json
from pathlib import Path


HOTWORDS = {"xong", "xong rồi", "báo cáo", "thầy ơi", "cô ơi", "cho xem"}


class STTModule:
    def __init__(self,
                 model_path: str = "models/vosk-vi",
                 device_index: int | None = None,
                 sample_rate: int = 16000):
        self._model_path  = model_path
        self._device_idx  = device_index
        self._sample_rate = sample_rate
        self._hotword_q   = queue.Queue(maxsize=10)
        self._stop_event  = threading.Event()
        self._thread      = None
        self._ready       = False

    def start(self) -> bool:
        """Khởi động background thread. Returns False nếu model/mic không có."""
        if not Path(self._model_path).exists():
            print(f"[STT] Model không tìm thấy: {self._model_path}")
            return False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()

    def get_hotword(self) -> str | None:
        """Non-blocking: lấy hotword gần nhất detect được, None nếu chưa có."""
        try:
            return self._hotword_q.get_nowait()
        except queue.Empty:
            return None

    @property
    def is_ready(self) -> bool:
        return self._ready

    def _loop(self) -> None:
        try:
            import vosk
            import pyaudio
        except ImportError:
            print("[STT] Cần cài: pip install vosk pyaudio")
            return

        model = vosk.Model(self._model_path)
        rec   = vosk.KaldiRecognizer(model, self._sample_rate)
        pa    = pyaudio.PyAudio()

        stream = pa.open(
            format            = pyaudio.paInt16,
            channels          = 1,
            rate              = self._sample_rate,
            input             = True,
            input_device_index= self._device_idx,
            frames_per_buffer = 4000,
        )
        self._ready = True
        print("✅ STTModule sẵn sàng (Vosk realtime)")

        while not self._stop_event.is_set():
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result()).get("text", "")
                self._check_hotwords(result)
            else:
                partial = json.loads(rec.PartialResult()).get("partial", "")
                self._check_hotwords(partial)

        stream.stop_stream()
        stream.close()
        pa.terminate()

    def _check_hotwords(self, text: str) -> None:
        if not text:
            return
        text_lower = text.lower().strip()
        for hw in HOTWORDS:
            if hw in text_lower:
                try:
                    self._hotword_q.put_nowait(hw)
                except queue.Full:
                    pass
                print(f"[STT] Hotword: '{hw}'")
                break
```

### 2.4 Tích hợp vào `main.py`

```python
# main.py — thêm optional STT:
from audio.stt_module import STTModule

# Trong __init__ (chỉ khởi động nếu có model):
self.stt = STTModule() if Config.STT_ENABLED else None
if self.stt:
    self.stt.start()

# Trong main loop:
if self.stt:
    hotword = self.stt.get_hotword()
    if hotword and hw_status["state"] == "requesting":
        ok = self.homework_monitor.do_capture(frame_bgr)
        if ok:
            self.alerts.confirm_captured()
```

### 2.5 Constants cần thêm (`constants.py` Group 23)

```python
# ─── Group 23 — Speech-to-Text ────────────────────────────────────
STT_ENABLED         = False   # Tắt mặc định — chỉ bật khi có mic
STT_MODEL_PATH      = "models/vosk-vi"
STT_DEVICE_INDEX    = None    # None = auto-detect thiết bị đầu tiên
STT_SAMPLE_RATE     = 16000   # Hz (Vosk cần 16kHz)
```

---

## 3. Thứ tự implement

```
Bước 1: Test espeak-ng (5 phút)
  espeak-ng -v vi "Xin chào" → nghe thử

Bước 2: Tạo services/alert_service.py  (30 phút)
  + Thêm TTS_ENABLED vào constants.py + config.py
  + Tích hợp vào main.py (3-4 trigger points)
  + Test: distracted/phone alert chạy không block camera

Bước 3: Mua/cắm USB mic  (hardware)
  arecord -l → xác nhận device index

Bước 4: Cài Vosk + download model (15 phút)
  pip install vosk pyaudio
  download vosk-model-small-vn-0.4 → models/vosk-vi/

Bước 5: Tạo audio/stt_module.py  (1-2 giờ)
  + Test hotword detection độc lập
  + Tích hợp vào main.py
  + Test end-to-end: nói "xong rồi" → auto capture
```

---

## 4. Lưu ý kỹ thuật

- **espeak-ng tiếng Việt** không hoàn hảo (accent thiếu dấu đôi khi) — chấp nhận được cho prototype.
  Nếu muốn giọng tự nhiên hơn: dùng gTTS (cần internet) hoặc Coqui TTS (offline, nặng hơn).

- **Vosk vs Whisper**: Vosk realtime (không lag), Whisper tốt hơn nhưng cần 0.5-2s buffer → kém hơn cho hotword detection. Dùng Vosk cho hotword, Whisper nếu cần STT đầy đủ.

- **Thermal**: espeak-ng chạy ~5ms, không ảnh hưởng nhiệt độ. Vosk chạy realtime ~10-15% CPU, cộng thêm vào ~85% hiện tại → có thể cần set_skip() cho YOLO khi STT đang chạy.

- **Tạo `services/__init__.py`** khi tạo `alert_service.py`:
  ```python
  # services/__init__.py
  from .alert_service import AlertService
  ```
