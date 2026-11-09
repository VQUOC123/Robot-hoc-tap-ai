# camera_module.py
#
# Hỗ trợ cả IMX219 (Camera v2.1, 8MP) và IMX500 (Raspberry Pi AI Camera, 12.3MP).
#
# Dual-stream architecture (giữ nguyên cho cả hai camera):
#   lores  (CAMERA_WIDTH × CAMERA_HEIGHT, BGR888) → detection + MJPEG stream
#   main   (SNAPSHOT_WIDTH × SNAPSHOT_HEIGHT, RGB888) → hi-res snapshot cho AI
#
# IMX219 mode (CAMERA_IMX500_ENABLED=False, mặc định):
#   - Picamera2() không args, capture_array("lores") như cũ
#   - Max snapshot: 3280×2464 (8MP)
#
# IMX500 mode (CAMERA_IMX500_ENABLED=True):
#   - IMX500 device init trước Picamera2 (firmware upload lên camera chip ~3-5s)
#   - Picamera2(imx500.camera_num) — dùng đúng camera number của IMX500
#   - capture_request() thay capture_array() → lấy cả metadata chứa YOLO inference output
#   - last_metadata: dict chứa CnnOutputTensor0... (IMX500 inference results)
#   - YoloDetector.feed_imx500_metadata(last_metadata) → extract primary YOLO boxes
#   - Max snapshot: 4056×3040 (12.3MP)

import cv2
import numpy as np
from picamera2 import Picamera2
import time
import os
from dotenv import load_dotenv

load_dotenv()


class CameraModule:
    def __init__(self):
        from core.config import Config
        self.width           = Config.CAMERA_WIDTH
        self.height          = Config.CAMERA_HEIGHT
        self.snapshot_width  = Config.SNAPSHOT_WIDTH
        self.snapshot_height = Config.SNAPSHOT_HEIGHT
        self._imx500         = None   # IMX500 device object (None nếu dùng IMX219)
        self._last_metadata  = None   # Camera metadata từ capture_request() (IMX500 only)

        if Config.CAMERA_IMX500_ENABLED:
            self._init_imx500()
        else:
            self.picam2 = Picamera2()

        self._setup_camera()
        cam_model = "IMX500 (AI Camera 12.3MP)" if self._imx500 else "IMX219 (Camera v2.1)"
        print(f"✅ Camera sẵn sàng! [{cam_model}]")
        print(f"   Stream/detect : {self.width}×{self.height}")
        print(f"   Snapshot (AI) : {self.snapshot_width}×{self.snapshot_height}")

    # ── IMX500 Init ────────────────────────────────────────────────────────────

    def _init_imx500(self) -> None:
        """
        Khởi tạo Raspberry Pi AI Camera (Sony IMX500).
        PHẢI gọi trước Picamera2 — IMX500 cần upload firmware lên camera chip trước.
        Dùng imx500.camera_num để Picamera2 chọn đúng camera.
        """
        from core.config import Config
        from picamera2.devices.imx500 import IMX500
        model_path = Config.YOLO_IMX500_MODEL_PATH
        print("🤖 IMX500 AI Camera khởi động...")
        print(f"   Model: {model_path}")
        print("   (Đang upload neural network firmware lên camera chip, ~3-5 giây...)")
        self._imx500 = IMX500(model_path)
        self.picam2  = Picamera2(self._imx500.camera_num)
        print(f"   ✓ IMX500 sẵn sàng (camera #{self._imx500.camera_num})")

    # ── Camera Setup ───────────────────────────────────────────────────────────

    def _setup_camera(self):
        # Preview config: lores cho detection/stream, main cho snapshot hi-res
        # Hoạt động với cả IMX219 và IMX500 — dual-stream không đổi
        config = self.picam2.create_preview_configuration(
            main={
                "size"  : (self.snapshot_width, self.snapshot_height),
                "format": "RGB888",
            },
            lores={
                "size"  : (self.width, self.height),
                "format": "BGR888",
            },
            buffer_count=2,
        )
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(2)

        awb_mode = os.getenv('CAMERA_AWB_MODE', 'manual').lower()
        if awb_mode == 'auto':
            pass
        else:
            red_gain  = float(os.getenv('CAMERA_RED_GAIN',  '2.4'))
            blue_gain = float(os.getenv('CAMERA_BLUE_GAIN', '1.8'))
            self.picam2.set_controls({
                "AwbEnable"   : False,
                "ColourGains" : (red_gain, blue_gain),
            })
            print(f"🎨 AWB manual: red={red_gain}, blue={blue_gain}")

    # ── Frame Capture ──────────────────────────────────────────────────────────

    def capture_frame(self) -> np.ndarray:
        """
        Capture 1 frame từ lores stream (thấp độ phân giải, nhanh).
        Trả về numpy array RGB (CAMERA_WIDTH × CAMERA_HEIGHT).
        Dùng cho detection (MediaPipe, YOLO) và MJPEG stream.

        IMX500 mode: dùng capture_request() để lấy cả metadata chứa YOLO inference output.
                     last_metadata được cập nhật sau mỗi lần capture.
        IMX219 mode: capture_array() như cũ, last_metadata = None.
        """
        if self._imx500 is not None:
            req = self.picam2.capture_request()
            bgr = req.make_array("lores")
            self._last_metadata = req.get_metadata()
            req.release()
        else:
            bgr = self.picam2.capture_array("lores")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def capture_snapshot(self) -> np.ndarray | None:
        """
        Chụp ảnh hi-res từ main stream (SNAPSHOT_WIDTH × SNAPSHOT_HEIGHT).
        Trả về numpy array BGR.
        Dùng cho /capture endpoint — gửi AI kiểm tra bài tập.

        Lưu ý: main stream chạy song song với lores, không cần switch mode.
        Detection tiếp tục bình thường trong khi chụp.
        """
        try:
            rgb = self.picam2.capture_array("main")
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"⚠️  Snapshot thất bại: {e}")
            return None

    # ── Utilities ──────────────────────────────────────────────────────────────

    def to_jpeg(self, frame_bgr, quality=75):
        """Chuyển frame BGR thành JPEG bytes"""
        ret, buffer = cv2.imencode(
            '.jpg', frame_bgr,
            [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        return buffer.tobytes() if ret else None

    def close(self):
        self.picam2.stop()
        print("Camera đã tắt")

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def imx500(self):
        """IMX500 device object — dùng để init YoloDetector với IMX500 backend.
        Trả về None nếu không dùng IMX500 (Camera v2.1 mode)."""
        return self._imx500

    @property
    def last_metadata(self) -> dict | None:
        """Metadata từ capture_request() cuối cùng.
        Chứa IMX500 inference output (CnnOutputTensor0...) — dùng để extract YOLO boxes.
        Trả về None nếu IMX500 chưa chạy hoặc đang dùng IMX219."""
        return self._last_metadata
