# camera/stream_module.py
import cv2
import threading
import time
import os
import socket
import logging
import base64
from flask import (
    Flask,
    Response,
    jsonify,
    request
)
from core.config import Config

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


class StreamModule:

    def __init__(self, system):
        self.system     = system
        self.config     = Config()
        self.app        = Flask(__name__)
        self._frame     = self._make_placeholder_frame()
        self._lock      = threading.Lock()
        self.start_time = time.time()

        # Raw frame (trước khi vẽ overlay) — dùng cho capture
        self._raw_frame_bgr  = None
        self._raw_frame_lock = threading.Lock()

        # Lazy-loaded AI module cho tính năng đọc nội dung
        self._ai = None

        self._setup_routes()
        print("✅ Stream Module sẵn sàng!")

    @staticmethod
    def _make_placeholder_frame() -> bytes:
        """Tạo JPEG frame tối để stream không bị None khi khởi động."""
        import numpy as np
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(frame, "Dang khoi dong camera...",
                    (380, 360), cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, (80, 80, 80), 2)
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return buf.tobytes()

    # ── Raw Frame Storage ─────────────────────────────

    def store_raw_frame(self, frame_bgr):
        """Lưu frame gốc (trước overlay) để dùng cho capture."""
        with self._raw_frame_lock:
            self._raw_frame_bgr = frame_bgr

    def _get_ai(self):
        """Lazy-load AI module khi cần."""
        if self._ai is None:
            try:
                from ai.ai_module import AIModule
                self._ai = AIModule()
            except Exception as e:
                print(f"⚠️  Không tải được AI module: {e}")
                self._ai = False   # Đánh dấu đã thử, không thử lại
        return self._ai if self._ai else None

    # ── Frame Update ─────────────────────────────────

    def update_frame(self, frame_bgr):
        try:
            ret, buf = cv2.imencode(
                '.jpg', frame_bgr,
                [cv2.IMWRITE_JPEG_QUALITY, 75]
            )
            if ret:
                with self._lock:
                    self._frame = buf.tobytes()
        except Exception as e:
            print(f"❌ update_frame: {e}")

    # ── Stream Generator ─────────────────────────────

    def _gen(self):
        """
        MJPEG generator — giới hạn FPS theo STREAM_FPS (mặc định 20fps).
        Giảm encode JPEG liên tục, nhẹ tải Flask + network.
        """
        stream_interval = 1.0 / Config.STREAM_FPS
        while True:
            t0 = time.time()

            with self._lock:
                frame = self._frame

            if frame is None:
                time.sleep(0.05)
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n'
                b'Content-Length: ' +
                str(len(frame)).encode() +
                b'\r\n\r\n' +
                frame +
                b'\r\n'
            )

            # Ngủ phần thời gian còn lại trong khoảng stream_interval
            elapsed = time.time() - t0
            sleep_t = stream_interval - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)

    # ── Routes ───────────────────────────────────────

    def _setup_routes(self):

        @self.app.route('/')
        def index():
            return self._html()

        @self.app.route('/video_feed')
        def video_feed():
            """
            MJPEG stream endpoint
            Headers quan trọng để browser
            không đóng connection
            """
            resp = Response(
                self._gen(),
                mimetype=(
                    'multipart/x-mixed-replace; '
                    'boundary=frame'
                )
            )
            # Ngăn browser cache và đóng connection
            resp.headers['Cache-Control'] = (
                'no-cache, no-store, '
                'must-revalidate'
            )
            resp.headers['Pragma']     = 'no-cache'
            resp.headers['Expires']    = '0'
            resp.headers['Connection'] = 'keep-alive'
            resp.headers['X-Accel-Buffering'] = 'no'
            return resp

        @self.app.route('/status')
        def status():
            try:
                data = self.system.current_data.copy()
                data['uptime'] = int(
                    time.time() - self.start_time
                )
                return jsonify(data)
            except Exception as e:
                return jsonify({
                    "error"         : str(e),
                    "final_status"  : "Khởi động...",
                    "final_activity": "starting",
                    "focus_score"   : 0,
                    "details"       : {},
                    "fps"           : 0,
                    "uptime"        : 0
                })

        @self.app.route('/chat', methods=['POST'])
        def chat():
            body = request.get_json() or {}
            msg  = body.get('message', '').strip()

            if not msg:
                return jsonify(
                    {"error": "No message"}
                ), 400

            if (hasattr(self.system, 'ai') and
                    self.system.ai and
                    self.system.ai.enabled):
                resp = self.system.ai.chat(msg)
                if (hasattr(self.system, 'tts') and
                        self.system.tts):
                    self.system.tts.speak_for_ai(
                        resp
                    )
            else:
                resp = (
                    "AI chưa kích hoạt. "
                    "Thêm API key vào .env nhé!"
                )
            return jsonify({"response": resp})

        @self.app.route('/stats')
        def stats():
            try:
                s = self.system.analyzer.get_stats()
            except Exception:
                s = {}
            s['uptime'] = int(
                time.time() - self.start_time
            )
            return jsonify(s)

        @self.app.route('/absence_log')
        def absence_log():
            try:
                info = self.system.pose.get_info()
                lg   = info.get('absence_log', [])
            except Exception:
                lg = []
            return jsonify({"log": lg})

        @self.app.route('/capture')
        def capture():
            """
            Chụp ảnh hi-res từ main stream (SNAPSHOT_WIDTH × SNAPSHOT_HEIGHT).
            Detection + MJPEG stream tiếp tục bình thường trong khi chụp.
            Trả về: base64 JPEG + kích thước ảnh.
            """
            # Ưu tiên hi-res từ camera nếu có
            frame = None
            if hasattr(self.system, 'camera') and self.system.camera:
                frame = self.system.camera.capture_snapshot()

            # Fallback về raw frame (720p) nếu camera không có snapshot method
            if frame is None:
                with self._raw_frame_lock:
                    frame = self._raw_frame_bgr

            if frame is None:
                return jsonify({"error": "Camera chưa sẵn sàng"}), 503

            h, w = frame.shape[:2]
            ret, buf = cv2.imencode(
                '.jpg', frame,
                [cv2.IMWRITE_JPEG_QUALITY, 92]  # 92 = cân bằng rõ/nhỏ cho AI
            )
            if not ret:
                return jsonify({"error": "Không encode được ảnh"}), 500

            img_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
            return jsonify({
                "image"     : img_b64,
                "width"     : w,
                "height"    : h,
                "timestamp" : time.strftime('%H:%M:%S'),
                "hires"     : (w > 1280),   # flag để client biết có hi-res không
            })

        @self.app.route('/homework_status')
        def homework_status():
            """
            Trả về trạng thái HomeworkMonitor hiện tại.
            UI poll endpoint này mỗi 1s để cập nhật panel.
            """
            try:
                hw = getattr(self.system, 'homework_monitor', None)
                if hw is None:
                    return jsonify({"state": "disabled"})
                return jsonify(hw._build_status(time.time()))
            except Exception as e:
                return jsonify({"state": "error", "message": str(e)})

        @self.app.route('/homework_capture', methods=['POST'])
        def homework_capture():
            """
            User bấm "Chụp hình" trong REQUESTING state.
            Lấy raw frame hiện tại → giao cho HomeworkMonitor encode + lưu.
            """
            hw = getattr(self.system, 'homework_monitor', None)
            if hw is None:
                return jsonify({"error": "HomeworkMonitor chưa khởi động"}), 503

            with self._raw_frame_lock:
                frame = self._raw_frame_bgr

            if frame is None:
                return jsonify({"error": "Camera chưa sẵn sàng"}), 503

            ok = hw.do_capture(frame)
            if ok:
                return jsonify({"ok": True})
            return jsonify({"error": "Không ở trạng thái REQUESTING"}), 400

        @self.app.route('/homework_analyze', methods=['POST'])
        def homework_analyze():
            """
            User bấm "Phân tích AI" → lấy ảnh từ HomeworkMonitor
            → gửi AI → trả về kết quả.
            """
            hw = getattr(self.system, 'homework_monitor', None)
            if hw is None:
                return jsonify({"error": "HomeworkMonitor chưa khởi động"}), 503

            image_b64 = hw.trigger_analyze()
            if image_b64 is None:
                return jsonify({"error": "Chưa có ảnh bài tập để phân tích"}), 400

            ai = self._get_ai()
            if ai is None:
                return jsonify({
                    "error": (
                        "AI chưa kích hoạt. Thêm API key vào .env:\n"
                        "  CLAUDE_API_KEY=... hoặc OPENAI_API_KEY=..."
                    )
                })

            try:
                result = ai.analyze_homework(image_b64)
                hw.set_analysis(result)
                return jsonify({"result": result, "provider": ai.provider or "none"})
            except Exception as e:
                return jsonify({"error": f"Lỗi phân tích: {e}"}), 500

        @self.app.route('/api/display', methods=['POST'])
        def api_display():
            """
            Bật/tắt các lớp hiển thị trên video stream.
            Body JSON: {"show_yolo_boxes": true/false}
            """
            body    = request.get_json() or {}
            tracker = getattr(self.system, 'multi_tracker', None)
            if tracker is None:
                return jsonify({"error": "Tracker chưa khởi động"}), 503
            if 'show_yolo_boxes' in body:
                tracker.show_yolo_boxes = bool(body['show_yolo_boxes'])
            return jsonify({"show_yolo_boxes": tracker.show_yolo_boxes})

        @self.app.route('/read_content', methods=['POST'])
        def read_content():
            """
            Gửi ảnh đến AI để đọc nội dung (OCR màn hình/sách/vở).
            Body JSON: {"image": "<base64 jpeg>"}
            Trả về: {"text": "<nội dung đọc được>"}
            """
            body      = request.get_json() or {}
            img_b64   = body.get('image', '').strip()

            if not img_b64:
                return jsonify({"error": "Thiếu image"}), 400

            ai = self._get_ai()
            if ai is None:
                return jsonify({
                    "text": (
                        "⚠️ AI chưa được kích hoạt.\n"
                        "Thêm API key vào .env:\n"
                        "  CLAUDE_API_KEY=...\n"
                        "  hoặc OPENAI_API_KEY=...\n"
                        "  hoặc GEMINI_API_KEY=..."
                    )
                })

            text = ai.read_content(img_b64)
            return jsonify({"text": text, "provider": ai.provider or "none"})

    # ── HTML ─────────────────────────────────────────

    def _html(self):
        """Load từ file template"""
        tpl = os.path.join(
            self.config.BASE_DIR,
            'web', 'templates', 'index.html'
        )
        print(f"Loading template: {tpl}")
        print(f"File exists: {os.path.exists(tpl)}")

        if os.path.exists(tpl):
            with open(tpl, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"Template size: {len(content)} bytes")
            return content

        print("❌ Template không tìm thấy!")
        return "<h1>Template missing</h1>"

    # ── Run ──────────────────────────────────────────

    def run(self):
        ip   = self._get_ip()
        port = self.config.STREAM_PORT

        print(f"\n🌐 Mở browser:")
        print(f"   http://{ip}:{port}\n")

        self.app.run(
            host=self.config.STREAM_HOST,
            port=port,
            debug=False,
            threaded=True,
            use_reloader=False
        )

    def _get_ip(self):
        try:
            s = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM
            )
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '192.168.2.82'