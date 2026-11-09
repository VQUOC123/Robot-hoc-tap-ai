# main.py
import cv2
import time
import threading
import signal
import sys
import traceback

# Import theo cấu trúc mới
from core           import Config
from camera         import CameraModule, StreamModule
from detectors      import (
    HandDetector,
    GazeDetector,
    PoseDetector,
    MultiPersonTracker,
    YoloDetector,
)
from detectors.multi_person_tracker import build_object_context, desk_y_from_yolo
from analyzers      import ActivityAnalyzer
from analyzers.homework_monitor import HomeworkMonitor
from services import AlertService


class AITutorSystem:
    def __init__(self):
        print("\n🚀 Khởi động Hệ Thống Quan Sát")
        print("━" * 40)

        self.config     = Config()

        # ROI settings
        self._roi_enabled   = Config.ROI_ENABLED
        self._roi_x1        = Config.ROI_X1
        self._roi_x2        = Config.ROI_X2
        self._roi_y1        = Config.ROI_Y1
        self._roi_y2        = Config.ROI_Y2

        if self._roi_enabled:
            print(
                f"📐 ROI bật: x[{self._roi_x1:.0%}→{self._roi_x2:.0%}] "
                f"y[{self._roi_y1:.0%}→{self._roi_y2:.0%}]"
            )
            print(
                "   (Loại bỏ học sinh ngồi cạnh, "
                "chỉ phân tích vùng giữa frame)"
            )

        # Chế độ: single-person hoặc multi-person
        self._multi_person = Config.MULTI_PERSON_ENABLED

        # Khởi tạo modules
        self.camera     = CameraModule()
        self.stream     = StreamModule(self)

        if self._multi_person:
            print(f"👥 Chế độ NHIỀU NGƯỜI (tối đa {Config.MAX_PERSONS} người: A-{chr(ord('A') + Config.MAX_PERSONS - 1)})")
            # Truyền IMX500 device + picam2 vào MultiPersonTracker để YoloDetector
            # sử dụng IMX500 chip cho primary YOLO (thay vì CPU) nếu được bật.
            self.multi_tracker  = MultiPersonTracker(
                imx500=self.camera.imx500,
                picam2=self.camera.picam2,
            )
            # Các detectors đơn lẻ không dùng trong multi-person mode
            self.hands = self.gaze = self.pose = self.analyzer = self.yolo = None
        else:
            self.hands      = HandDetector()
            self.gaze       = GazeDetector()
            self.pose       = PoseDetector()
            self.analyzer   = ActivityAnalyzer()
            self.multi_tracker = None
            # YOLO cho single-person mode: IMX500 chip hoặc CPU async thread
            # Cung cấp object context (has_phone, has_book...) cho ActivityAnalyzer
            self.yolo = (
                YoloDetector(imx500=self.camera.imx500, picam2=self.camera.picam2)
                if Config.YOLO_ENABLED else None
            )
            # Dynamic desk plane (single-person mode) — cùng logic với MultiPersonTracker
            _cam = Config.CAMERA_SIDE
            if _cam in ("right", "left"):
                _desk_init = max(0.40, Config.HAND_ZONE_BOTTOM_RATIO - 0.08)
            elif _cam in ("front_right", "front_left"):
                _desk_init = min(0.72, Config.HAND_ZONE_BOTTOM_RATIO + 0.10)
            else:
                _desk_init = Config.HAND_ZONE_BOTTOM_RATIO
            self._desk_y_ema: float = _desk_init

        # Homework monitoring + TTS alerts
        self.homework_monitor = HomeworkMonitor()
        self.alerts = AlertService(
            enabled=Config.TTS_ENABLED,
            phone_delay=Config.TTS_PHONE_ALERT_DELAY,
            distract_delay=Config.TTS_DISTRACT_ALERT_DELAY,
        )

        # State trackers for alert edge-detection
        self._hw_was_requesting   = False
        self._hw_quality_warned   = False

        self.is_running  = True
        self.fps_counter = 0
        self.fps_start   = time.time()
        self.current_fps = 0

        # Throttling: giới hạn detection FPS để tránh CPU 100%
        # Benchmark RPi5: MediaPipe Hands ≈ 77ms/frame (max ~13fps)
        # DETECTION_FPS=10 → sleep ~20ms giữa frames → CPU ~77% thay vì 100%
        self._detect_interval = 1.0 / Config.DETECTION_FPS
        self._last_detect_t   = 0.0

        self.current_data = {
            "final_status"  : "Đang khởi động...",
            "final_activity": "starting",
            "focus_score"   : 0,
            "details"       : {
                "hand": "",
                "gaze": "",
                "pose": ""
            },
            "fps"           : 0,
            "multi_person"  : self._multi_person,
            "persons"       : [],   # Chứa kết quả A/B/C... khi multi_person=True
        }

        print("━" * 40)
        print("✅ Tất cả modules sẵn sàng!\n")

    def _merge_yolo_context(self, pose_info: dict, frame_bgr) -> dict:
        """
        Lấy YOLO result hiện tại, build object context, merge vào pose_info.
        Dùng cho single-person mode (cả standard và ROI) để cung cấp
        has_phone, has_book, has_pen... cho ActivityAnalyzer.

        Trả về pose_info đã được bổ sung object context (không thay đổi gốc
        nếu không có YOLO result).
        """
        yolo_result = self.yolo.get_result()
        if yolo_result is None:
            return pose_info

        h, w = frame_bgr.shape[:2]
        persons = yolo_result.persons()
        if persons:
            # Dùng person bbox đầu tiên (chỉ theo dõi 1 người)
            p_bbox = persons[0].as_tuple()
        else:
            # Không detect được người → dùng toàn frame làm bbox proxy
            p_bbox = (0, 0, w, h)

        # Cập nhật desk_y EMA từ keyboard/mouse YOLO (thích nghi với góc camera)
        raw_desk = desk_y_from_yolo(yolo_result, h)
        if raw_desk is not None:
            self._desk_y_ema = 0.97 * self._desk_y_ema + 0.03 * raw_desk
        self.hands.set_desk_y(self._desk_y_ema)

        obj_ctx = build_object_context(
            p_bbox,
            yolo_result,
            margin_x_ratio=0.2,
            hand_bboxes=None,
        )
        obj_ctx["desk_y_norm"] = self._desk_y_ema  # dynamic desk level

        # Merge: tạo copy để không mutate gốc
        merged = dict(pose_info)
        merged.update(obj_ctx)
        return merged

    def _apply_roi(self, frame_rgb, frame_bgr):
        """
        Crop frame theo ROI để tập trung vào học sinh chính.
        Giúp loại bỏ học sinh ngồi cạnh trong hàng dài.
        Returns: (frame_rgb_roi, frame_bgr_roi, roi_rect)
        roi_rect = (x1, y1, x2, y2) trong tọa độ frame gốc
        """
        h, w = frame_rgb.shape[:2]
        x1 = int(w * self._roi_x1)
        x2 = int(w * self._roi_x2)
        y1 = int(h * self._roi_y1)
        y2 = int(h * self._roi_y2)

        # Đảm bảo ROI hợp lệ
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        roi_rgb = frame_rgb[y1:y2, x1:x2]
        roi_bgr = frame_bgr[y1:y2, x1:x2]

        return roi_rgb, roi_bgr, (x1, y1, x2, y2)

    def _draw_roi_border(self, frame_bgr, roi_rect):
        """Vẽ viền ROI lên frame để dễ quan sát vùng đang phân tích"""
        x1, y1, x2, y2 = roi_rect
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(
            frame_bgr,
            "VUNG PHAN TICH",
            (x1 + 5, y1 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55, (0, 255, 255), 2
        )
        # Làm mờ vùng ngoài ROI để dễ nhận biết
        overlay = frame_bgr.copy()
        # Vùng trái
        if x1 > 0:
            cv2.rectangle(overlay, (0, 0), (x1, frame_bgr.shape[0]),
                          (0, 0, 0), -1)
        # Vùng phải
        if x2 < frame_bgr.shape[1]:
            cv2.rectangle(overlay, (x2, 0),
                          (frame_bgr.shape[1], frame_bgr.shape[0]),
                          (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, frame_bgr, 0.6, 0, frame_bgr)
        # Vẽ lại border sau khi blend
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 255, 255), 2)

    def _camera_loop(self):
        print("👁️ Bắt đầu quan sát...")
        print(f"   Detection FPS cap: {Config.DETECTION_FPS}fps "
              f"(interval {1000/Config.DETECTION_FPS:.0f}ms)")

        while self.is_running:
            try:
                loop_start = time.time()

                # Throttle: ngủ nếu chưa đến thời điểm detect tiếp theo
                # → tránh spin 100% CPU khi MediaPipe chạy dưới target FPS
                wait = self._detect_interval - (loop_start - self._last_detect_t)
                if wait > 0:
                    time.sleep(wait)
                self._last_detect_t = time.time()

                frame_rgb = self.camera.capture_frame()
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

                # Feed IMX500 primary YOLO results từ camera metadata (non-blocking).
                # Phải gọi TRƯỚC process()/submit_frame() để background thread
                # có boxes mới nhất khi _run_inference() chạy lần tiếp theo.
                if Config.CAMERA_IMX500_ENABLED:
                    metadata = self.camera.last_metadata
                    if self._multi_person and self.multi_tracker:
                        self.multi_tracker.feed_imx500_metadata(metadata)
                    elif not self._multi_person and self.yolo:
                        self.yolo.feed_imx500_metadata(metadata)

                # Lưu raw frame (trước overlay) để dùng cho tính năng capture
                self.stream.store_raw_frame(frame_bgr.copy())

                if self._multi_person:
                    # ── Chế độ nhiều người: MultiPersonTracker xử lý tất cả ──
                    frame_bgr, persons = self.multi_tracker.process(
                        frame_rgb, frame_bgr
                    )

                    # Tổng hợp status cho terminal log (người đầu tiên = A)
                    if persons:
                        primary = persons[0]
                        log_status  = primary.get("final_status", "")
                        log_focus   = primary.get("focus_score", 0)
                    else:
                        log_status  = "Chưa phát hiện ai"
                        log_focus   = 0

                    # Cập nhật current_data
                    analysis = {
                        "final_status"  : log_status,
                        "final_activity": persons[0].get("final_activity", "starting") if persons else "starting",
                        "focus_score"   : log_focus,
                        "details"       : persons[0].get("details", {}) if persons else {},
                        "persons"       : persons,
                        "multi_person"  : True,
                    }

                elif self._roi_enabled:
                    # ── Chế độ ROI: chỉ phân tích vùng học sinh chính ──
                    roi_rgb, roi_bgr, roi_rect = self._apply_roi(
                        frame_rgb, frame_bgr
                    )

                    # Submit frame cho YOLO background thread (secondary+tertiary)
                    if self.yolo:
                        self.yolo.submit_frame(frame_bgr, self.fps_counter)

                    roi_bgr = self.hands.detect(roi_rgb, roi_bgr)
                    roi_bgr = self.gaze.detect(roi_rgb, roi_bgr)
                    roi_bgr = self.pose.detect(roi_rgb, roi_bgr)

                    # Ghi kết quả ROI ngược lại vào frame đầy đủ
                    x1, y1, x2, y2 = roi_rect
                    frame_bgr[y1:y2, x1:x2] = roi_bgr
                    self._draw_roi_border(frame_bgr, roi_rect)

                    pose_info = self.pose.get_info()
                    if self.yolo:
                        pose_info = self._merge_yolo_context(
                            pose_info, frame_bgr
                        )
                    analysis = self.analyzer.analyze(
                        self.hands.get_info(),
                        self.gaze.get_info(),
                        pose_info,
                    )
                    analysis["multi_person"] = False
                    analysis["persons"]      = []

                else:
                    # ── Chế độ thường: phân tích toàn bộ frame ──
                    # Submit frame cho YOLO background thread (secondary+tertiary)
                    if self.yolo:
                        self.yolo.submit_frame(frame_bgr, self.fps_counter)

                    frame_bgr = self.hands.detect(frame_rgb, frame_bgr)
                    frame_bgr = self.gaze.detect(frame_rgb, frame_bgr)
                    frame_bgr = self.pose.detect(frame_rgb, frame_bgr)

                    pose_info = self.pose.get_info()
                    if self.yolo:
                        pose_info = self._merge_yolo_context(
                            pose_info, frame_bgr
                        )
                    analysis = self.analyzer.analyze(
                        self.hands.get_info(),
                        self.gaze.get_info(),
                        pose_info,
                    )
                    analysis["multi_person"] = False
                    analysis["persons"]      = []

                # Tính FPS
                self.fps_counter += 1
                if time.time() - self.fps_start >= 1.0:
                    self.current_fps = self.fps_counter
                    self.fps_counter = 0
                    self.fps_start   = time.time()

                # ── Homework monitoring ─────────────────────────
                if self._multi_person and persons:
                    _hw_activity = persons[0].get("final_activity", "present")
                    _hw_visible  = persons[0].get("homework_visible", False)
                else:
                    _hw_activity = analysis.get("final_activity", "present")
                    _hw_visible  = analysis.get("homework_visible", False)

                hw_status = self.homework_monitor.update(
                    _hw_activity, _hw_visible, frame_bgr
                )

                # ── TTS Alerts ──────────────────────────────────────
                hw_state = hw_status.get("state", "")

                # Edge: vừa vào REQUESTING → nhắc học sinh giơ bài
                if hw_state == "requesting" and not self._hw_was_requesting:
                    self.alerts.prompt_homework()
                self._hw_was_requesting = (hw_state == "requesting")

                # Edge: quality fail xuất hiện lần đầu → nhắc giơ rõ hơn
                quality_warn = hw_status.get("quality_warn", "")
                if quality_warn and not self._hw_quality_warned:
                    self.alerts.alert_quality_fail()
                self._hw_quality_warned = bool(quality_warn)

                # Sustained activity alerts (debounced inside AlertService)
                _activity = (
                    persons[0].get("final_activity", "") if (self._multi_person and persons)
                    else analysis.get("final_activity", "")
                )
                if _activity == "using_phone":
                    self.alerts.alert_phone()
                elif _activity == "distracted":
                    self.alerts.alert_distracted()
                elif _activity == "sleeping":
                    self.alerts.alert_sleeping()

                # Cập nhật data
                self.current_data.update({
                    **analysis,
                    "fps"        : self.current_fps,
                    "homework"   : hw_status,
                    "last_alert" : self.alerts.get_last_alert(),
                })

                # Cập nhật stream
                self.stream.update_frame(frame_bgr)

                # Log terminal
                if self._multi_person and persons:
                    n = len(persons)
                    summary = " | ".join(
                        f"{p['label']}:{p.get('final_activity','?')}[{p.get('focus_score',0)}]"
                        for p in persons
                    )
                    print(
                        f"\r⏱ {time.strftime('%H:%M:%S')}"
                        f" | 👥 {n} người: {summary}"
                        f" | FPS: {self.current_fps}",
                        end="", flush=True
                    )
                else:
                    print(
                        f"\r⏱ {time.strftime('%H:%M:%S')}"
                        f" | {analysis['final_status']}"
                        f" | Focus: {analysis['focus_score']}%"
                        f" | FPS: {self.current_fps}",
                        end="", flush=True
                    )

            except Exception as e:
                print(f"\n❌ Lỗi: {e}")
                traceback.print_exc()
                # Đảm bảo stream luôn có frame (dùng raw frame nếu processing crash)
                try:
                    self.stream.update_frame(frame_bgr)
                except Exception:
                    pass
                time.sleep(0.5)

    def run(self):
        threads = [
            threading.Thread(
                target=self._camera_loop,
                daemon=True
            ),
            threading.Thread(
                target=self.stream.run,
                daemon=True
            )
        ]

        for t in threads:
            t.start()

        print("💡 Nhấn Ctrl+C để tắt\n")

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("\n\n🛑 Đang tắt...")
        self.is_running = False
        if self.multi_tracker and hasattr(self.multi_tracker, 'stop'):
            self.multi_tracker.stop()
        # Dừng YOLO background thread trong single-person mode
        if getattr(self, 'yolo', None) is not None:
            self.yolo.stop()
        self.camera.close()
        print("✅ Đã tắt!")
        sys.exit(0)


if __name__ == "__main__":
    signal.signal(
        signal.SIGINT,
        lambda s, f: sys.exit(0)
    )
    system = AITutorSystem()
    system.run()
