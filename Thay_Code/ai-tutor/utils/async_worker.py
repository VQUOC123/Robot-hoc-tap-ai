# utils/async_worker.py
# AsyncWorker — Base class cho background inference workers.
#
# Pattern: Latest-frame-wins (không queue).
#   - Main thread gọi submit() — non-blocking, luôn trả về ngay.
#   - Background thread nhận frame mới nhất, chạy inference, lưu result.
#   - Nếu worker đang bận khi submit() được gọi → frame cũ bị drop,
#     frame mới được lưu chờ xử lý tiếp.
#   - Main thread gọi get_result() — non-blocking, đọc cache gần nhất.
#
# Lý do dùng latest-frame-wins thay vì queue:
#   - Inference chậm hơn camera FPS → queue tích lũy → lag ngày càng tăng
#   - Với giám sát realtime: frame cũ 200ms không có giá trị bằng frame mới
#   - YOLO, MediaPipe đều phù hợp với pattern này
#
# Thread safety:
#   _frame_lock  : bảo vệ _pending_frame + _pending_meta (write main, read worker)
#   _result_lock : bảo vệ _cached_result (write worker, read main)
#   Hai lock KHÔNG bao giờ held đồng thời → không deadlock
#
# Cách sử dụng:
#   class MyDetector(AsyncWorker):
#       def _load_model(self):
#           self._model = load_something()
#
#       def _run_inference(self, frame, meta=None):
#           return self._model.predict(frame)
#
#   detector = MyDetector()       # start background thread
#   detector.submit(frame)        # non-blocking
#   result = detector.get_result()  # non-blocking, may be None initially
#   detector.stop()               # graceful shutdown

import threading
from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class AsyncWorker(ABC):
    """
    Abstract base class cho background inference workers.
    Subclass chỉ cần implement _load_model() và _run_inference().
    """

    def __init__(self) -> None:
        # ── Thread synchronization ────────────────────────────────────
        self._frame_lock  = threading.Lock()
        self._result_lock = threading.Lock()
        self._frame_event = threading.Event()   # báo hiệu có frame mới
        self._stop_event  = threading.Event()   # báo hiệu tắt

        # ── Shared state ──────────────────────────────────────────────
        self._pending_frame: np.ndarray | None = None
        self._pending_meta:  Any               = None
        self._cached_result: Any               = None

        # ── Status ────────────────────────────────────────────────────
        self._model_ready = False
        self._load_error  = False

        # ── Thermal skip (cho YOLO — tương tự cách cũ) ───────────────
        self._skip_count:     int = 0
        self._skip_remaining: int = 0

        # ── Start background thread ───────────────────────────────────
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.__class__.__name__}-worker",
        )
        self._thread.start()

    # ── Public API ────────────────────────────────────────────────────

    def submit(self, frame: np.ndarray, meta: Any = None) -> bool:
        """
        Gửi frame mới cho worker. Non-blocking.

        Args:
            frame : BGR ndarray — được copy trước khi gửi (thread-safe).
            meta  : Metadata tuỳ ý (ví dụ: frame_id cho YOLO).

        Returns:
            True  nếu frame được nhận.
            False nếu worker chưa sẵn sàng, có lỗi, hoặc đang bận xử lý
                  (frame_event đang set — sẽ được nhận lần submit tiếp theo).
        """
        if self._load_error or not self._model_ready:
            return False
        # Nếu event đang set → worker chưa xử lý frame trước
        # Không drop, ghi đè frame cũ với frame mới (latest-wins)
        with self._frame_lock:
            self._pending_frame = frame.copy()
            self._pending_meta  = meta
        self._frame_event.set()
        return True

    def get_result(self) -> Any:
        """
        Đọc kết quả cache gần nhất. Non-blocking, luôn trả về ngay.
        Trả về None nếu chưa có kết quả (model đang load hoặc chưa xử lý frame nào).
        """
        with self._result_lock:
            return self._cached_result

    def set_skip(self, skip: int) -> None:
        """
        Điều chỉnh số frame skip giữa 2 lần inference.
        Dùng cho thermal management: ThermalManager gọi khi nhiệt độ cao.
        """
        self._skip_count = max(0, skip)

    def stop(self) -> None:
        """Dừng background thread. Gọi khi tắt hệ thống."""
        self._stop_event.set()
        self._frame_event.set()   # unblock nếu đang wait
        self._thread.join(timeout=3.0)

    @property
    def model_ready(self) -> bool:
        """True sau khi _load_model() hoàn thành."""
        return self._model_ready

    @property
    def has_error(self) -> bool:
        """True nếu _load_model() thất bại."""
        return self._load_error

    # ── Abstract Methods ──────────────────────────────────────────────

    @abstractmethod
    def _load_model(self) -> None:
        """
        Khởi tạo model trong background thread.
        Gọi 1 lần khi worker bắt đầu. Raise exception nếu thất bại.
        """
        ...

    @abstractmethod
    def _run_inference(self, frame: np.ndarray, meta: Any = None) -> Any:
        """
        Chạy inference trên frame. Return kết quả (bất kỳ type).
        Chạy trong background thread — thread-safe với _load_model().
        """
        ...

    # ── Internal Worker Loop ──────────────────────────────────────────

    def _worker_loop(self) -> None:
        """Vòng lặp chính của background thread."""
        try:
            self._load_model()
            self._model_ready = True
        except Exception as e:
            print(f"❌ {self.__class__.__name__} load thất bại: {e}")
            self._load_error = True
            return

        print(f"✅ {self.__class__.__name__} sẵn sàng (background thread)")

        while not self._stop_event.is_set():
            # Chờ frame mới (timeout để check stop_event định kỳ)
            self._frame_event.wait(timeout=2.0)

            if self._stop_event.is_set():
                break
            if not self._frame_event.is_set():
                continue   # timeout, không có frame mới

            # Lấy frame
            with self._frame_lock:
                frame = self._pending_frame
                meta  = self._pending_meta
                self._pending_frame = None
                self._pending_meta  = None
            self._frame_event.clear()

            if frame is None:
                continue

            # Thermal skip
            if self._skip_remaining > 0:
                self._skip_remaining -= 1
                continue
            self._skip_remaining = self._skip_count

            # Chạy inference
            try:
                result = self._run_inference(frame, meta)
                with self._result_lock:
                    self._cached_result = result
            except Exception as e:
                print(f"⚠️  {self.__class__.__name__} inference error: {e}")
