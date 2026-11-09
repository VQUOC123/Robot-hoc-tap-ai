# detectors/yolo_detector.py
# YOLO detector — chạy inference trong background thread (AsyncWorker pattern).
#
# Thiết kế:
#   - Kế thừa AsyncWorker: submit_frame() non-blocking, get_result() non-blocking.
#   - Triple-model: primary (COCO) + secondary (Object365) + tertiary (OIV7).
#     Cả ba chạy tuần tự trong cùng background thread, kết quả được merge.
#     Performance: ~143ms/inference, window 300ms (YOLO_SKIP_FRAMES=2) → 157ms headroom.
#   - ONNX auto-detect: nếu tồn tại file .onnx bên cạnh .pt → dùng ONNX,
#     fallback về PyTorch .pt. Không cần đổi config.
#   - ThermalManager tự động điều chỉnh skip qua set_skip().
#   - Secondary/tertiary disabled khi MODEL_PATH = "" (graceful degradation).
#
# IMX500 mode (imx500 != None, Dependency Injection):
#   - Primary YOLO chạy trên camera chip (IMX500) thay vì CPU.
#   - feed_imx500_metadata(metadata) → main thread gọi sau mỗi capture_frame()
#     → cập nhật _imx500_boxes (atomic list assignment, GIL safe).
#   - _run_inference() dùng _imx500_boxes thay vì chạy primary CPU model.
#   - Secondary + Tertiary vẫn chạy async CPU như cũ.
#   - Lợi ích: ~40ms CPU tiết kiệm mỗi frame cho primary YOLO.
#
# API (backward compatible với code cũ):
#   detector.submit_frame(frame_bgr, frame_id)    → non-blocking
#   detector.get_result()                          → YoloResult | None
#   detector.feed_imx500_metadata(metadata)        → update primary từ IMX500 (NEW)
#   detector.set_skip(n)                           → thermal management
#   detector.stop()                                → shutdown

import os
import sys
import cv2
import time
import numpy as np
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config      import Config
from utils.async_worker import AsyncWorker
from utils.image_utils  import resize_for_inference


# ── Value Objects ──────────────────────────────────────────────────────────────

@dataclass
class YoloBox:
    """Một bounding box từ YOLO inference. Immutable sau khi tạo."""
    x1: float
    y1: float
    x2: float
    y2: float
    cls_id:   int
    cls_name: str
    score:    float

    @property
    def cx(self) -> float:
        """X trung tâm bbox."""
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        """Y trung tâm bbox."""
        return (self.y1 + self.y2) / 2.0

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    def contains_center(self, other: "YoloBox") -> bool:
        """Kiểm tra center của other có nằm trong bbox này không."""
        return self.x1 <= other.cx <= self.x2 and self.y1 <= other.cy <= self.y2

    def as_tuple(self) -> tuple:
        """(x1, y1, x2, y2) — dùng cho OpenCV."""
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass
class YoloResult:
    """Kết quả 1 lần YOLO inference. Immutable sau khi tạo."""
    boxes:     list          # list[YoloBox]
    frame_id:  int
    timestamp: float

    def persons(self) -> list:
        """Danh sách các YoloBox có cls_id == 0 (person), sorted trái → phải."""
        return sorted(
            [b for b in self.boxes if b.cls_id == 0],
            key=lambda b: b.x1,
        )

    def objects_near(
        self,
        person_bbox: tuple,
        margin_x_ratio: float = 0.2,
        margin_y_ratio: float = 0.3,
    ) -> list:
        """
        Trả về list[YoloBox] là vật thể (không phải person) có center
        nằm trong/gần person bbox, mở rộng margin theo cả 2 chiều.

        margin_x_ratio: mở rộng trái/phải (tỷ lệ theo chiều rộng bbox)
        margin_y_ratio: mở rộng xuống dưới (tỷ lệ theo chiều cao bbox)
                        → cần cho điện thoại đặt trên đùi (bên dưới y2)
        """
        x1, y1, x2, y2 = person_bbox
        mx = (x2 - x1) * margin_x_ratio
        my = (y2 - y1) * margin_y_ratio
        return [
            box for box in self.boxes
            if box.cls_id != 0
            and (x1 - mx) <= box.cx <= (x2 + mx)
            and y1 <= box.cy <= (y2 + my)
        ]

    def is_fresh(self, max_age_frames: int, current_frame: int) -> bool:
        """Kiểm tra result có còn mới không."""
        return (current_frame - self.frame_id) <= max_age_frames


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_onnx_path(model_path: str) -> str:
    """
    Nếu YOLO_PREFER_ONNX=True và tồn tại file .onnx bên cạnh .pt → dùng ONNX.
    ONNX inference ~40ms vs PyTorch ~110ms trên RPi5 (2.75× speedup).
    Fallback tự động về .pt nếu .onnx chưa export.
    """
    if not Config.YOLO_PREFER_ONNX:
        return model_path
    if model_path.endswith(".pt"):
        onnx_path = model_path[:-3] + ".onnx"
        if os.path.exists(onnx_path):
            return onnx_path
    return model_path


# ── YoloDetector ───────────────────────────────────────────────────────────────

class YoloDetector(AsyncWorker):
    """
    Dual-model YOLO detector với background thread inference.

    Primary model   (COCO 80 lớp):  person, phone, mouse, keyboard, bottle, cup,
                                    book, laptop, monitor.
    Secondary model (Object365):    pen (idx 51), notepaper (idx 233).
    Tertiary model  (OIV7 601 lớp): Pen (idx 376) — class riêng, chính xác hơn Object365;
                                    Book (idx 54) — bổ sung signal notebook detection.
    cls_name "pen"/"book" từ tertiary tự merge với secondary/primary qua multi_person_tracker.

    Cả hai chạy tuần tự trong cùng background thread, kết quả được merge.
    ONNX được ưu tiên nếu tồn tại (xem _resolve_onnx_path).

    Usage:
        detector = YoloDetector()
        # Trong camera loop:
        detector.submit_frame(frame_bgr, frame_id)   # non-blocking
        result = detector.get_result()               # non-blocking
        if result:
            persons = result.persons()
        # Khi tắt:
        detector.stop()
    """

    # COCO class indices (primary model)
    _COCO_CLASS_NAMES: dict[int, str] = {
        0 : "person",
        39: "bottle",
        41: "cup",
        62: "monitor",
        63: "laptop",
        64: "mouse",
        66: "keyboard",
        67: "phone",
        73: "book",
    }

    # Object365 class indices (secondary model — pen/notepaper only)
    _OBJ365_CLASS_NAMES: dict[int, str] = {
        51 : "pen",
        233: "notepaper",
    }

    # Open Images V7 class indices (tertiary model — higher-quality pen + book)
    # cls_name "pen"/"book" tự merge với secondary/primary qua multi_person_tracker
    _OIV7_CLASS_NAMES: dict[int, str] = {
        376: "pen",   # Pen — class riêng (không merge pencil), ~9M annotations
        54 : "book",  # Book — bổ sung signal notebook cho has_book
    }

    def __init__(self, imx500=None, picam2=None) -> None:
        """
        imx500: picamera2 IMX500 device object (None → dùng CPU primary YOLO).
        picam2: Picamera2 instance — cần cho convert_inference_coords() (IMX500 mode).
        """
        self._imx500_device  = imx500   # IMX500 device (None → CPU primary)
        self._picam2         = picam2   # Picamera2 (cần cho coord conversion)
        self._imx500_boxes   = []       # Primary boxes từ IMX500, GIL-safe assignment
        self._model           = None    # primary (COCO) — bỏ qua khi IMX500 active
        self._model_secondary = None    # secondary (Object365)
        self._model_tertiary  = None    # tertiary (OIV7 — better pen)
        self._skip_count      = Config.YOLO_SKIP_FRAMES
        mode = "IMX500+CPU(secondary/tertiary)" if imx500 else "CPU"
        print(f"🔄 YoloDetector khởi động ({mode}, background thread)...")
        super().__init__()              # starts background thread → _load_model()

    # ── Public API (backward compatible) ─────────────────────────────

    def submit_frame(self, frame_bgr: np.ndarray, frame_id: int) -> bool:
        """
        Gửi frame mới. Non-blocking (wrapper cho AsyncWorker.submit).
        frame_id được truyền qua meta để lưu vào YoloResult.
        """
        return self.submit(frame_bgr, meta=frame_id)

    # get_result()   → inherited, returns YoloResult | None
    # set_skip(n)    → inherited
    # stop()         → inherited
    # model_ready    → inherited property

    # ── AsyncWorker Implementation ────────────────────────────────────

    def _load_model(self) -> None:
        """Load YOLO models và warmup. Chạy trong background thread.
        IMX500 mode: bỏ qua primary CPU model (IMX500 chip xử lý thay).
        """
        from ultralytics import YOLO

        dummy = np.zeros(
            (Config.YOLO_INPUT_SIZE, Config.YOLO_INPUT_SIZE, 3), dtype=np.uint8
        )

        # ── Primary model ────────────────────────────────────────────
        if self._imx500_device is not None:
            # IMX500 chip xử lý primary YOLO — không cần load CPU model
            print("📦 YOLO primary: IMX500 chip — bỏ qua CPU model (~40ms tiết kiệm/frame)")
        else:
            primary_path = _resolve_onnx_path(Config.YOLO_MODEL_PATH)
            print(f"📦 YOLO primary: {primary_path}...")
            self._model = YOLO(primary_path, verbose=False)
            self._model(
                dummy,
                imgsz=Config.YOLO_INPUT_SIZE,
                verbose=False,
                classes=Config.YOLO_TARGET_CLASSES,
            )
            fmt = "ONNX" if primary_path.endswith(".onnx") else "PyTorch"
            print(f"   ✓ Primary ({fmt}): {os.path.basename(primary_path)}")

        # ── Secondary model ──────────────────────────────────────────
        sec_pt = Config.YOLO_SECONDARY_MODEL_PATH
        if sec_pt:
            sec_path = _resolve_onnx_path(sec_pt)
            print(f"📦 YOLO secondary: {sec_path}...")
            self._model_secondary = YOLO(sec_path, verbose=False)
            self._model_secondary(
                dummy,
                imgsz=Config.YOLO_INPUT_SIZE,
                verbose=False,
                classes=Config.YOLO_SECONDARY_CLASSES,
            )
            fmt = "ONNX" if sec_path.endswith(".onnx") else "PyTorch"
            print(f"   ✓ Secondary ({fmt}): {os.path.basename(sec_path)}")

        # ── Tertiary model (OIV7 — better pen + book) ────────────────
        ter_pt = Config.YOLO_TERTIARY_MODEL_PATH
        if ter_pt:
            ter_path = _resolve_onnx_path(ter_pt)
            print(f"📦 YOLO tertiary: {ter_path}...")
            self._model_tertiary = YOLO(ter_path, verbose=False)
            # Warmup dùng YOLO_TERTIARY_INPUT_SIZE (416) thay vì 320
            dummy_ter = np.zeros(
                (Config.YOLO_TERTIARY_INPUT_SIZE, Config.YOLO_TERTIARY_INPUT_SIZE, 3),
                dtype=np.uint8,
            )
            self._model_tertiary(
                dummy_ter,
                imgsz=Config.YOLO_TERTIARY_INPUT_SIZE,
                verbose=False,
                classes=Config.YOLO_TERTIARY_CLASSES,
            )
            fmt = "ONNX" if ter_path.endswith(".onnx") else "PyTorch"
            print(f"   ✓ Tertiary ({fmt}): {os.path.basename(ter_path)}")

    def _run_inference(self, frame: np.ndarray, meta: int | None = None) -> YoloResult:
        """
        Chạy primary + secondary YOLO trên frame đã downscale, merge kết quả.
        meta = frame_id (int) từ submit_frame().

        IMX500 mode: dùng _imx500_boxes (cập nhật từ main thread) thay vì CPU primary.
                     _imx500_boxes đã là list Python → copy atomic dưới GIL, thread-safe.
        CPU mode: chạy primary model như cũ.
        """
        frame_id = meta if meta is not None else -1

        # Primary: IMX500 chip (camera) hoặc CPU
        if self._imx500_device is not None:
            # Atomic list copy — GIL đảm bảo không race với main thread ghi _imx500_boxes
            boxes = list(self._imx500_boxes)
        else:
            small, scale = resize_for_inference(frame, Config.YOLO_INPUT_SIZE)
            boxes = self._run_single(
                self._model, small, scale,
                Config.YOLO_TARGET_CLASSES, self._COCO_CLASS_NAMES,
            )

        # Secondary model (Object365 — pen/notepaper) — luôn chạy CPU
        # Dùng YOLO_SECONDARY_CONFIDENCE (0.20) thay vì YOLO_CONFIDENCE (0.35)
        # vì bút là vật nhỏ → confidence thấp hơn ngưỡng chung.
        if self._model_secondary is not None:
            # Cần resize frame cho secondary (có thể chưa resize nếu IMX500 mode)
            small_sec, scale_sec = resize_for_inference(frame, Config.YOLO_INPUT_SIZE)
            boxes += self._run_single(
                self._model_secondary, small_sec, scale_sec,
                Config.YOLO_SECONDARY_CLASSES, self._OBJ365_CLASS_NAMES,
                conf=Config.YOLO_SECONDARY_CONFIDENCE,
            )

        # Tertiary model (OIV7 — pen class riêng + book bổ sung) — luôn chạy CPU
        # Dùng input size lớn hơn (416 vs 320) để detect bút mỏng (~3-4px thay vì 2px).
        # Confidence thấp hơn (0.25 vs 0.35) vì bút nhỏ → model ít confident hơn.
        # cls_name "pen"/"book" tự merge với secondary/primary trong multi_person_tracker.
        if self._model_tertiary is not None:
            small_ter, scale_ter = resize_for_inference(frame, Config.YOLO_TERTIARY_INPUT_SIZE)
            boxes += self._run_single(
                self._model_tertiary, small_ter, scale_ter,
                Config.YOLO_TERTIARY_CLASSES, self._OIV7_CLASS_NAMES,
                conf=Config.YOLO_TERTIARY_CONFIDENCE,
            )

        return YoloResult(boxes=boxes, frame_id=frame_id, timestamp=time.time())

    # ── Internal Helpers ──────────────────────────────────────────────

    def _run_single(
        self,
        model,
        small:    np.ndarray,
        scale:    float,
        classes:  list,
        name_map: dict,
        conf:     float | None = None,
    ) -> list:
        """
        Chạy inference trên 1 model, trả về list[YoloBox] đã scale về tọa độ gốc.
        conf: override confidence threshold (None = dùng Config.YOLO_CONFIDENCE).
        """
        _conf = conf if conf is not None else Config.YOLO_CONFIDENCE
        # imgsz phải khớp với kích thước của small frame
        _imgsz = max(small.shape[:2])
        raw = model(
            small,
            imgsz=_imgsz,
            conf=_conf,
            iou=Config.YOLO_NMS_IOU,
            classes=classes,
            verbose=False,
        )
        boxes = []
        if raw and raw[0].boxes is not None:
            for det in raw[0].boxes:
                x1, y1, x2, y2 = det.xyxy[0].tolist()
                cls_id = int(det.cls[0])
                score  = float(det.conf[0])
                boxes.append(YoloBox(
                    x1       = x1 / scale,
                    y1       = y1 / scale,
                    x2       = x2 / scale,
                    y2       = y2 / scale,
                    cls_id   = cls_id,
                    cls_name = name_map.get(cls_id, f"cls{cls_id}"),
                    score    = score,
                ))
        return boxes

    # ── IMX500 Backend ────────────────────────────────────────────────

    def feed_imx500_metadata(self, metadata: dict) -> None:
        """
        Cập nhật primary YOLO boxes từ IMX500 camera metadata.
        Gọi từ main thread ngay sau capture_frame(), trước submit_frame().

        Thread-safe: Python GIL đảm bảo list assignment là atomic —
        background thread đọc _imx500_boxes không bị partial update.
        """
        if self._imx500_device is None or not self.model_ready or metadata is None:
            return
        self._imx500_boxes = self._postprocess_imx500(metadata)

    def _postprocess_imx500(self, metadata: dict) -> list:
        """
        Convert IMX500 inference output → list[YoloBox] trong lores pixel coords.

        YOLO26n được export với nms=True (bắt buộc cho IMX format) → 4 output tensors:
          Tensor0: boxes  (max_det, 4)  — post-NMS, inference space coords
          Tensor1: classes (max_det,)   — class indices (int)
          Tensor2: scores  (max_det,)   — confidence [0,1]
          Tensor3: num_dets (1,)        — số detection hợp lệ

        postprocess_yolov8_detection() chỉ xử lý model KHÔNG có NMS (2 tensors raw).
        Ta decode trực tiếp 4 tensors này thay vì dùng hàm đó.
        """
        outputs = self._imx500_device.get_outputs(metadata, add_batch=True)
        if outputs is None or len(outputs) == 0:
            return []

        # Model không có NMS built-in (2 tensors raw) → dùng picamera2 postprocess
        if len(outputs) == 2:
            try:
                from picamera2.devices.imx500.postprocess_yolov8 import (
                    postprocess_yolov8_detection,
                )
                boxes, scores, classes = postprocess_yolov8_detection(
                    outputs,
                    conf=Config.YOLO_IMX500_CONF,
                    iou_thres=Config.YOLO_IMX500_IOU,
                    max_out_dets=Config.YOLO_IMX500_MAX_DETS,
                )
            except Exception:
                return []
            return self._boxes_to_yolobox(boxes, scores, classes, metadata)

        # Model có NMS built-in (4 tensors) — YOLO26n / YOLOv8n IMX export
        # Thứ tự THỰC TẾ từ get_outputs (verified by inspection):
        #   [0] boxes  (1,300,4): pixel coords trong inference space (0..imgsz)
        #   [1] scores (1,300):   confidence [0,1]
        #   [2] classes(1,300):   class indices (0..79 for COCO)
        #   [3] num_dets(1,1):    số detection hợp lệ
        if len(outputs) == 4:
            boxes_t, scores_t, cls_t, num_t = outputs   # scores & cls đúng vị trí
            try:
                num_dets = int(round(float(np.ravel(num_t)[0])))
            except Exception:
                return []
            if num_dets <= 0:
                return []
            boxes   = np.array(boxes_t).reshape(-1, 4)[:num_dets]
            scores  = np.ravel(scores_t)[:num_dets]
            classes = np.ravel(cls_t)[:num_dets]
            return self._boxes_to_yolobox(boxes, scores, classes, metadata)

        return []

    def _boxes_to_yolobox(self, boxes, scores, classes, metadata) -> list:
        """Convert arrays of boxes/scores/classes → list[YoloBox] với coord conversion.

        IMX500 NMS model output: boxes trong inference pixel space (0..imgsz).
        convert_inference_coords() cần: (y0, x0, y1, x1) normalized [0,1].
        → Normalize /imgsz rồi reorder trước khi gọi.
        """
        imgsz = float(Config.YOLO_IMX500_INPUT_SIZE)   # 320
        result = []
        for box, score, cls_id in zip(boxes, scores, classes):
            if float(score) < Config.YOLO_IMX500_CONF:
                continue
            cls_id = int(round(float(cls_id)))
            if cls_id not in self._COCO_CLASS_NAMES:
                continue
            if self._picam2 is not None:
                try:
                    # box = [x1_px, y1_px, x2_px, y2_px] in inference space
                    # convert_inference_coords expects (y0, x0, y1, x1) normalized [0,1]
                    x1_px, y1_px, x2_px, y2_px = box
                    norm = (y1_px / imgsz, x1_px / imgsz,
                            y2_px / imgsz, x2_px / imgsz)
                    # Returns Rectangle as (x, y, w, h) — NOT (x1, y1, x2, y2)
                    rx, ry, rw, rh = self._imx500_device.convert_inference_coords(
                        norm, metadata, self._picam2, stream='lores'
                    )
                    x1, y1 = float(rx), float(ry)
                    x2, y2 = float(rx + rw), float(ry + rh)
                except Exception:
                    continue
            else:
                x1 = float(box[0]) / imgsz * Config.CAMERA_WIDTH
                y1 = float(box[1]) / imgsz * Config.CAMERA_HEIGHT
                x2 = float(box[2]) / imgsz * Config.CAMERA_WIDTH
                y2 = float(box[3]) / imgsz * Config.CAMERA_HEIGHT
            result.append(YoloBox(
                x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
                cls_id=cls_id, cls_name=self._COCO_CLASS_NAMES[cls_id],
                score=float(score),
            ))
        return result
