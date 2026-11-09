# AI Periodic Capture — RPi5 Client Plan

**Scope:** Thay đổi trên Raspberry Pi 5 (`ai-tutor/` project) để chụp ảnh định kỳ
và gửi lên **Tutor Backend Service** (project riêng, xem `AI_SERVICE_BACKEND_PLAN.md`).

> RPi5 **không** gọi trực tiếp LiteLLM/Gemini.
> Toàn bộ logic AI, prompt, provider đều ở Backend Service.
> RPi5 chỉ: detect student present → chụp ảnh → resize → POST → nhận kết quả → hiển thị.

---

## 1. Luồng hoạt động

```
main.py loop (10fps)
    │
    ├─ MediaPipe + YOLO pipeline (giữ nguyên)
    ├─ current_data: {activity, focus_score, homework_visible, ...}
    │
    └─ PeriodicAICaptureService (background thread)
         │  mỗi AI_CAPTURE_INTERVAL giây
         │  kiểm tra: activity != absent/briefly_away?
         │
         ├─ YES → chụp frame hi-res → resize 1024×768 → encode JPEG q=82
         │        POST /api/v1/device/analyze (multipart + metadata)
         │        lưu kết quả → cập nhật StreamModule shared data
         │
         └─ NO  → skip, tiếp tục sleep


StreamModule Flask (thread riêng)
    ├─ GET /ai_capture_status  → trả kết quả mới nhất
    └─ GET /status             → merge kết quả vào response

index.html (browser)
    └─ Poll /ai_capture_status mỗi 3s → hiển thị AI Vision panel
```

---

## 2. Files cần thay đổi

### Tổng quan

| File | Thao tác | Nội dung |
|---|---|---|
| `services/periodic_ai_service.py` | **Tạo mới** | Background thread service |
| `core/constants.py` | Thêm | Group 24: AI Capture constants |
| `core/config.py` | Thêm | Config attributes tương ứng |
| `main.py` | Sửa | Init + lifecycle PeriodicAICaptureService |
| `camera/stream_module.py` | Sửa | Endpoint `/ai_capture_status` + merge `/status` |
| `web/templates/index.html` | Sửa | Panel "AI Vision" + poll JS |

---

## 3. `services/periodic_ai_service.py` (Tạo mới)

### Cấu trúc class

```python
"""
services/periodic_ai_service.py

Background thread: mỗi AI_CAPTURE_INTERVAL giây,
chụp ảnh → gửi Tutor Backend Service → lưu kết quả.
Thread-safe. Không block main detection loop.
"""

import threading
import time
import cv2
import requests
import logging
from datetime import datetime, timezone
from typing import Optional, Callable
import numpy as np

from core.config import Config

logger = logging.getLogger(__name__)


class PeriodicAICaptureService:

    # ── Shared result dict (đọc bởi Flask thread) ────────────
    # Tất cả writes phải dùng self._lock
    _DEFAULT_RESULT = {
        "enabled"         : False,
        "configured"      : False,   # service_url + token đã set
        "status"          : "idle",  # idle|checking|homework|no_homework|error
        "last_check_time" : "",       # "14:30:25"
        "last_check_ts"   : 0.0,     # unix timestamp
        "doing_hw"        : None,    # bool hoặc None
        "subject"         : None,    # "Toán", "Văn", "Tiếng Anh"...
        "grade"           : None,    # "lớp 8"
        "hw_type"         : None,    # "bài tập", "luận văn"...
        "progress"        : 0,
        "hints"           : None,    # gợi ý từ AI (tiếng Việt)
        "confidence"      : 0.0,
        "calls_total"     : 0,
        "calls_hw_found"  : 0,
        "error"           : None,
    }

    def __init__(
        self,
        get_frame_fn  : Callable[[], Optional[np.ndarray]],
        get_data_fn   : Callable[[], dict],
        service_url   : str,
        service_token : str,
    ):
        """
        Args:
            get_frame_fn:   callback trả BGR ndarray (frame mới nhất, không có overlay)
            get_data_fn:    callback trả current_data dict từ main loop
            service_url:    base URL của Tutor Backend Service
            service_token:  Bearer token để authenticate với service
        """
        self._get_frame    = get_frame_fn
        self._get_data     = get_data_fn
        self._service_url  = service_url.rstrip('/')
        self._service_token = service_token

        self._lock    = threading.Lock()
        self._stop_ev = threading.Event()
        self._thread  : Optional[threading.Thread] = None

        # Config từ constants (có thể override qua .env)
        self._interval     = Config.AI_CAPTURE_INTERVAL      # giây
        self._img_w        = Config.AI_CAPTURE_IMAGE_WIDTH
        self._img_h        = Config.AI_CAPTURE_IMAGE_HEIGHT
        self._img_quality  = Config.AI_CAPTURE_JPEG_QUALITY
        self._cooldown_hw  = Config.AI_CAPTURE_COOLDOWN_HW   # giây sau khi detect HW
        self._cooldown_no  = Config.AI_CAPTURE_COOLDOWN_NO   # giây khi không phải HW

        # Shared result
        self._result = dict(self._DEFAULT_RESULT)
        self._result["enabled"]    = bool(service_url and service_token)
        self._result["configured"] = bool(service_url and service_token)

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self):
        if not self._result["configured"]:
            logger.warning(
                "[PeriodicAI] TUTOR_SERVICE_URL hoặc TUTOR_SERVICE_TOKEN chưa set — service tắt"
            )
            return
        self._thread = threading.Thread(
            target=self._loop,
            name="PeriodicAICapture",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"[PeriodicAI] Started — interval={self._interval}s endpoint={self._service_url}")

    def stop(self):
        self._stop_ev.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[PeriodicAI] Stopped")

    # ── Main loop ─────────────────────────────────────────────

    def _loop(self):
        next_check_at = time.monotonic()  # chạy ngay lần đầu

        while not self._stop_ev.is_set():
            now = time.monotonic()

            if now < next_check_at:
                # Sleep nhỏ để không spin
                time.sleep(min(0.5, next_check_at - now))
                continue

            # ── Kiểm tra student có hiện diện không ──────────
            data = self._get_data()
            if not self._is_student_present(data):
                next_check_at = now + self._interval
                continue

            # ── Capture + gửi ────────────────────────────────
            self._set_status("checking")
            jpeg_bytes = self._capture_frame()

            if jpeg_bytes is None:
                logger.debug("[PeriodicAI] Không có frame — skip")
                next_check_at = now + self._interval
                self._set_status("idle")
                continue

            result = self._call_service(jpeg_bytes, data)

            # ── Lưu kết quả + tính cooldown ──────────────────
            doing_hw = result.get("doing_hw", False)
            cooldown = self._cooldown_hw if doing_hw else self._cooldown_no
            next_check_at = now + cooldown

            with self._lock:
                self._result.update({
                    "status"         : "homework" if doing_hw else "no_homework",
                    "last_check_time": datetime.now().strftime("%H:%M:%S"),
                    "last_check_ts"  : time.time(),
                    "doing_hw"       : doing_hw,
                    "subject"        : result.get("subject"),
                    "grade"          : result.get("grade"),
                    "hw_type"        : result.get("hw_type"),
                    "progress"       : result.get("progress", 0),
                    "hints"          : result.get("hints"),
                    "confidence"     : result.get("confidence", 0.0),
                    "error"          : None,
                    "calls_total"    : self._result["calls_total"] + 1,
                    "calls_hw_found" : (
                        self._result["calls_hw_found"] + (1 if doing_hw else 0)
                    ),
                })

    # ── Helpers ───────────────────────────────────────────────

    def _is_student_present(self, data: dict) -> bool:
        """True nếu học sinh đang ngồi học (không phải absent/briefly_away)."""
        activity = data.get("final_activity", "absent")
        return activity not in ("absent", "briefly_away", "")

    def _capture_frame(self) -> Optional[bytes]:
        """
        Lấy frame BGR mới nhất → resize → encode JPEG.
        Dùng INTER_AREA để giữ sắc nét chữ khi downscale.
        """
        frame = self._get_frame()
        if frame is None or frame.size == 0:
            return None

        try:
            resized = cv2.resize(
                frame,
                (self._img_w, self._img_h),
                interpolation=cv2.INTER_AREA,
            )
            ok, buf = cv2.imencode(
                '.jpg', resized,
                [cv2.IMWRITE_JPEG_QUALITY, self._img_quality],
            )
            return buf.tobytes() if ok else None
        except Exception as e:
            logger.error(f"[PeriodicAI] Lỗi capture frame: {e}")
            return None

    def _call_service(self, jpeg_bytes: bytes, data: dict) -> dict:
        """
        POST multipart/form-data lên Tutor Backend Service.
        Trả dict result hoặc {} nếu lỗi.
        """
        try:
            resp = requests.post(
                f"{self._service_url}/api/v1/device/analyze",
                headers={"Authorization": f"Bearer {self._service_token}"},
                files={"image": ("frame.jpg", jpeg_bytes, "image/jpeg")},
                data={
                    "activity"   : data.get("final_activity", ""),
                    "focus_score": str(data.get("focus_score", 0)),
                    "hw_visible" : str(data.get("homework_visible", False)),
                    "student_id" : data.get("student_id", "default"),
                },
                timeout=35,   # margin trên AI call 30s timeout
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

        except requests.Timeout:
            logger.warning("[PeriodicAI] Timeout gọi service")
            self._set_error("Service timeout (>35s)")
        except requests.ConnectionError:
            logger.warning("[PeriodicAI] Không kết nối được service")
            self._set_error("Không kết nối được service")
        except requests.HTTPError as e:
            logger.warning(f"[PeriodicAI] HTTP {e.response.status_code}")
            self._set_error(f"HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"[PeriodicAI] Lỗi không xác định: {e}")
            self._set_error(str(e))

        return {}

    def _set_status(self, status: str):
        with self._lock:
            self._result["status"] = status

    def _set_error(self, msg: str):
        with self._lock:
            self._result["status"] = "error"
            self._result["error"]  = msg

    # ── Public ────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Thread-safe snapshot của result dict cho Flask endpoint."""
        with self._lock:
            return dict(self._result)
```

---

## 4. `core/constants.py` — Thêm Nhóm 24

```python
# ───────────────────────────────────────────────────────────────────
#  NHÓM 24: AI CHỤP ẢNH ĐỊNH KỲ (PERIODIC AI CAPTURE)
# ───────────────────────────────────────────────────────────────────

# Bật/tắt toàn bộ tính năng (cần TUTOR_SERVICE_URL + TUTOR_SERVICE_TOKEN)
AI_CAPTURE_ENABLED       = True

# Khoảng cách giữa các lần check (giây)
# Cooldown thực tế phụ thuộc vào kết quả:
#   - Detect được bài tập → AI_CAPTURE_COOLDOWN_HW (không cần check liền)
#   - Không phải bài tập  → AI_CAPTURE_COOLDOWN_NO
AI_CAPTURE_INTERVAL      = 10    # giây (dùng làm cooldown_no mặc định)
AI_CAPTURE_COOLDOWN_HW   = 30   # giây sau khi detect được homework
AI_CAPTURE_COOLDOWN_NO   = 10   # giây khi không phải homework

# Kích thước ảnh gửi lên service
# 1024×768 JPEG q=82 ≈ 130-180KB — đủ để AI đọc chữ trên vở,
# không quá lớn gây timeout. Dùng INTER_AREA để giữ sắc nét khi downscale.
AI_CAPTURE_IMAGE_WIDTH   = 1024
AI_CAPTURE_IMAGE_HEIGHT  = 768
AI_CAPTURE_JPEG_QUALITY  = 82    # 0-100 (80-85 là sweet spot cho text)
```

---

## 5. `core/config.py` — Thêm attributes

```python
# Nhóm 24: AI Periodic Capture
AI_CAPTURE_ENABLED       = _bool("AI_CAPTURE_ENABLED", c.AI_CAPTURE_ENABLED)
AI_CAPTURE_INTERVAL      = int(os.getenv("AI_CAPTURE_INTERVAL",     c.AI_CAPTURE_INTERVAL))
AI_CAPTURE_COOLDOWN_HW   = int(os.getenv("AI_CAPTURE_COOLDOWN_HW",  c.AI_CAPTURE_COOLDOWN_HW))
AI_CAPTURE_COOLDOWN_NO   = int(os.getenv("AI_CAPTURE_COOLDOWN_NO",  c.AI_CAPTURE_COOLDOWN_NO))
AI_CAPTURE_IMAGE_WIDTH   = int(os.getenv("AI_CAPTURE_IMAGE_WIDTH",  c.AI_CAPTURE_IMAGE_WIDTH))
AI_CAPTURE_IMAGE_HEIGHT  = int(os.getenv("AI_CAPTURE_IMAGE_HEIGHT", c.AI_CAPTURE_IMAGE_HEIGHT))
AI_CAPTURE_JPEG_QUALITY  = int(os.getenv("AI_CAPTURE_JPEG_QUALITY", c.AI_CAPTURE_JPEG_QUALITY))
```

---

## 6. `main.py` — Init + lifecycle

```python
# Import thêm (cùng với các import khác)
from services.periodic_ai_service import PeriodicAICaptureService

# Trong AITutorSystem.__init__, sau khi init HomeworkMonitor:
self.periodic_ai = PeriodicAICaptureService(
    get_frame_fn   = lambda: self.current_frame,   # BGR ndarray, không có overlay
    get_data_fn    = lambda: self.current_data,    # dict activity + focus_score...
    service_url    = os.getenv("TUTOR_SERVICE_URL", ""),
    service_token  = os.getenv("TUTOR_SERVICE_TOKEN", ""),
)

# Trong AITutorSystem.start() hoặc __init__ sau setup:
if cfg.AI_CAPTURE_ENABLED:
    self.periodic_ai.start()

# Trong AITutorSystem.stop() / cleanup:
self.periodic_ai.stop()

# Truyền service reference vào StreamModule để serve endpoint:
self.stream_module.set_periodic_ai_service(self.periodic_ai)
```

**Lưu ý:** `self.current_frame` cần là frame BGR gốc **không có overlay** (annotations).
StreamModule đã dùng `self._raw_frame` cho HomeworkMonitor — dùng cùng reference này.

---

## 7. `camera/stream_module.py` — Endpoint mới

```python
# Thêm method vào StreamModule class:

def set_periodic_ai_service(self, service):
    """Nhận reference từ main.py sau khi init."""
    self._periodic_ai = service

# Thêm route trong _setup_routes():

@self.app.route('/ai_capture_status')
def ai_capture_status():
    """Trả kết quả AI capture mới nhất — poll bởi index.html mỗi 3s."""
    if not hasattr(self, '_periodic_ai') or self._periodic_ai is None:
        return jsonify({"enabled": False, "configured": False})
    return jsonify(self._periodic_ai.get_status())

# Merge vào GET /status (thêm field "periodic_ai"):
@self.app.route('/status')
def status():
    data = self._build_status_response()   # existing logic

    # Merge periodic AI result
    if hasattr(self, '_periodic_ai') and self._periodic_ai:
        data["periodic_ai"] = self._periodic_ai.get_status()

    return jsonify(data)
```

---

## 8. `web/templates/index.html` — Panel AI Vision

### HTML (thêm vào sidebar, dưới Homework panel)

```html
<!-- AI Vision Panel -->
<div id="ai-vision-panel" class="panel" style="display:none">
  <div class="panel-header">
    <span>🤖 AI Vision</span>
    <span id="ai-vision-time" class="text-muted small"></span>
  </div>
  <div id="ai-vision-body" class="panel-body">
    <div id="ai-vision-idle"    class="ai-state">⏳ Chờ học sinh...</div>
    <div id="ai-vision-check"   class="ai-state ai-pulse" style="display:none">🔍 Đang phân tích...</div>
    <div id="ai-vision-nohw"    class="ai-state text-muted" style="display:none">— Không phải bài tập</div>
    <div id="ai-vision-error"   class="ai-state text-danger" style="display:none"></div>
    <div id="ai-vision-result"  style="display:none">
      <div class="ai-subject">
        <span id="ai-subject-icon">📚</span>
        <strong id="ai-subject-text"></strong>
        <span id="ai-grade-text" class="badge"></span>
      </div>
      <div id="ai-hwtype-text" class="text-muted small"></div>
      <div class="ai-progress-bar">
        <div id="ai-progress-fill" class="progress-fill"></div>
      </div>
      <div id="ai-hints" class="ai-hint-box">
        <span class="hint-icon">💡</span>
        <span id="ai-hints-text"></span>
      </div>
    </div>
  </div>
</div>
```

### CSS (thêm vào `<style>`)

```css
.ai-state { padding: 8px 0; font-size: 13px; }
.ai-pulse  { animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.4 } }

.ai-subject {
  display: flex; align-items: center; gap: 6px;
  font-size: 15px; margin-bottom: 4px;
}
.ai-subject .badge {
  background: var(--accent-cyan); color: #000;
  padding: 1px 6px; border-radius: 10px; font-size: 11px;
}
.ai-progress-bar {
  height: 4px; background: #333; border-radius: 2px;
  margin: 6px 0;
}
.progress-fill {
  height: 100%; background: var(--accent-cyan);
  border-radius: 2px; transition: width 0.5s ease;
}
.ai-hint-box {
  background: rgba(0,212,170,0.08); border-left: 2px solid var(--accent-cyan);
  padding: 6px 10px; border-radius: 4px; font-size: 13px;
  display: flex; gap: 6px; margin-top: 6px;
}
```

### JavaScript (thêm vào polling section)

```javascript
// Poll AI capture status mỗi 3 giây
let aiPollTimer = null;

function startAIPoll() {
    if (aiPollTimer) clearInterval(aiPollTimer);
    aiPollTimer = setInterval(fetchAIStatus, 3000);
    fetchAIStatus();  // gọi ngay lần đầu
}

async function fetchAIStatus() {
    try {
        const r = await fetch('/ai_capture_status');
        if (!r.ok) return;
        const d = await r.json();
        renderAIPanel(d);
    } catch (_) {}
}

function renderAIPanel(d) {
    const panel = document.getElementById('ai-vision-panel');
    if (!d.configured) { panel.style.display = 'none'; return; }
    panel.style.display = 'block';

    // Thời gian check cuối
    const timeEl = document.getElementById('ai-vision-time');
    timeEl.textContent = d.last_check_time ? `● ${d.last_check_time}` : '';

    // Ẩn tất cả states
    ['idle','check','nohw','error','result'].forEach(s =>
        document.getElementById(`ai-vision-${s}`).style.display = 'none'
    );

    switch(d.status) {
        case 'idle':
            document.getElementById('ai-vision-idle').style.display = 'block'; break;

        case 'checking':
            document.getElementById('ai-vision-check').style.display = 'block'; break;

        case 'no_homework':
            document.getElementById('ai-vision-nohw').style.display = 'block'; break;

        case 'error':
            const errEl = document.getElementById('ai-vision-error');
            errEl.style.display = 'block';
            errEl.textContent = `⚠️ ${d.error || 'Lỗi không xác định'}`;
            break;

        case 'homework':
            document.getElementById('ai-vision-result').style.display = 'block';
            // Subject + grade
            const subjectMap = {
                'Toán':'📐','Văn':'📖','Tiếng Anh':'🔤',
                'Lý':'⚡','Hóa':'🧪','Sinh':'🌱',
                'Sử':'🏛️','Địa':'🌍','Tin':'💻',
            };
            const icon = subjectMap[d.subject] || '📚';
            document.getElementById('ai-subject-icon').textContent = icon;
            document.getElementById('ai-subject-text').textContent = d.subject || '—';
            document.getElementById('ai-grade-text').textContent = d.grade ? `Lớp ${d.grade}` : '';
            document.getElementById('ai-hwtype-text').textContent = d.hw_type || '';
            // Progress bar
            document.getElementById('ai-progress-fill').style.width = `${d.progress || 0}%`;
            // Hints
            const hintsEl = document.getElementById('ai-hints');
            const hintsText = document.getElementById('ai-hints-text');
            if (d.hints) {
                hintsEl.style.display = 'flex';
                hintsText.textContent = d.hints;
            } else {
                hintsEl.style.display = 'none';
            }
            break;
    }
}

// Khởi động poll khi page load
document.addEventListener('DOMContentLoaded', startAIPoll);
```

---

## 9. `.env` — Thêm variables

```bash
# ── Tutor Backend Service ──────────────────────────────────
TUTOR_SERVICE_URL=http://<server-ip>:8080     # local hoặc https://api.tutor.domain.com
TUTOR_SERVICE_TOKEN=<bearer-token-từ-admin>

# ── Tuning (optional — có default trong constants.py) ──────
AI_CAPTURE_ENABLED=true
AI_CAPTURE_INTERVAL=10
AI_CAPTURE_COOLDOWN_HW=30
AI_CAPTURE_COOLDOWN_NO=10
AI_CAPTURE_IMAGE_WIDTH=1024
AI_CAPTURE_IMAGE_HEIGHT=768
AI_CAPTURE_JPEG_QUALITY=82
```

---

## 10. Ảnh gửi lên service

### Lý do chọn 1024×768 JPEG quality 82

```
Camera main stream: 2560×1920 (5MP)
    ↓ cv2.resize INTER_AREA
1024×768 (0.8MP)
    ↓ cv2.imencode JPEG q=82
~130-180KB
    ↓ multipart/form-data (không base64 — tiết kiệm 33% bandwidth)
Tutor Backend Service
```

| Kích thước | File ~KB | Đọc chữ trên vở | Ghi chú |
|---|---|---|---|
| 640×480, q=85 | ~60KB | ❌ Mất chữ nhỏ | Quá nhỏ |
| **1024×768, q=82** | **~150KB** | **✅ OK** | **Khuyến nghị** |
| 1280×960, q=80 | ~250KB | ✅ Tốt hơn | Chậm hơn chút |

`INTER_AREA` tốt hơn `INTER_LINEAR` khi downscale — giảm aliasing, chữ rõ hơn.

---

## 11. Thứ tự implement

```
[ ] Bước 1: Thêm constants Group 24 vào core/constants.py
[ ] Bước 2: Thêm Config attributes vào core/config.py
[ ] Bước 3: Tạo services/periodic_ai_service.py
            - Test độc lập: python -c "from services.periodic_ai_service import ..."
[ ] Bước 4: Sửa main.py — init + start + stop lifecycle
[ ] Bước 5: Sửa stream_module.py
            - set_periodic_ai_service()
            - GET /ai_capture_status
            - Merge vào GET /status
[ ] Bước 6: Sửa index.html — panel HTML + CSS + JS poll
[ ] Bước 7: Thêm TUTOR_SERVICE_URL + TUTOR_SERVICE_TOKEN vào .env
[ ] Bước 8: Test end-to-end với backend service đang chạy
            - curl -X POST http://localhost:8080/api/v1/device/analyze ...
            - Kiểm tra panel trên dashboard
```

### Test nhanh service độc lập

```python
# test_periodic_ai.py (chạy local trên RPi để debug)
import cv2
import numpy as np
from services.periodic_ai_service import PeriodicAICaptureService

# Mock frame: ảnh test thật
test_frame = cv2.imread("test_homework.jpg")

service = PeriodicAICaptureService(
    get_frame_fn   = lambda: test_frame,
    get_data_fn    = lambda: {"final_activity": "writing_notes", "focus_score": 80},
    service_url    = "http://localhost:8080",
    service_token  = "test-token",
)

# Test capture
jpeg = service._capture_frame()
print(f"JPEG size: {len(jpeg)/1024:.1f} KB")

# Test call service (cần backend đang chạy)
result = service._call_service(jpeg, {"final_activity": "writing_notes"})
print(f"Result: {result}")
```
