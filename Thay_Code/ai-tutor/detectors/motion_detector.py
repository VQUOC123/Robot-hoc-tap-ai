# motion_detector.py
import cv2
import numpy as np
import time
import os
from dotenv import load_dotenv

load_dotenv()

class MotionDetector:
    def __init__(self):
        self.threshold  = int(
            os.getenv('MOTION_THRESHOLD', 20)
        )
        self.min_area   = int(
            os.getenv('MOTION_MIN_AREA', 500)
        )

        # Frame trước để so sánh
        self.prev_gray  = None

        # Trạng thái hiện tại
        self.status     = "Đang khởi động..."
        self.activity   = "unknown"
        self.motion_level = 0        # 0-100
        self.regions    = []         # Vùng chuyển động

        # Tracking thời gian
        self.last_motion_time   = None
        self.no_motion_start    = None
        self.still_seconds      = 0

        # Lịch sử motion level để phân tích
        self.motion_history     = []
        self.MAX_HISTORY        = 30  # 30 frames

        print("✅ Motion Detector sẵn sàng!")

    def detect(self, frame_rgb):
        """
        Phát hiện chuyển động trong frame
        Returns: frame_bgr đã vẽ overlay
        """
        # Chuyển sang BGR và grayscale
        frame_bgr = cv2.cvtColor(
            frame_rgb, cv2.COLOR_RGB2BGR
        )
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Frame đầu tiên - chưa có gì để so sánh
        if self.prev_gray is None:
            self.prev_gray = gray
            return frame_bgr

        # ── So sánh với frame trước ──────────────────
        frame_delta = cv2.absdiff(self.prev_gray, gray)
        thresh = cv2.threshold(
            frame_delta,
            self.threshold,
            255,
            cv2.THRESH_BINARY
        )[1]

        # Làm dày vùng chuyển động
        thresh = cv2.dilate(thresh, None, iterations=3)

        # Tìm contours (vùng chuyển động)
        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # ── Lọc và phân tích contours ────────────────
        self.regions = []
        total_area   = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue

            # Lấy bounding box
            (x, y, w, h) = cv2.boundingRect(contour)
            self.regions.append({
                "x": x, "y": y,
                "w": w, "h": h,
                "area": area
            })
            total_area += area

        # ── Tính motion level (0-100) ─────────────────
        frame_area    = frame_rgb.shape[0] * frame_rgb.shape[1]
        self.motion_level = min(
            100,
            int((total_area / frame_area) * 1000)
        )

        # Lưu vào history
        self.motion_history.append(self.motion_level)
        if len(self.motion_history) > self.MAX_HISTORY:
            self.motion_history.pop(0)

        # ── Phân tích hoạt động ───────────────────────
        self._analyze_activity()

        # ── Vẽ lên frame ─────────────────────────────
        frame_bgr = self._draw_overlay(
            frame_bgr, thresh
        )

        # Cập nhật frame trước
        self.prev_gray = gray

        return frame_bgr

    def _analyze_activity(self):
        """
        Phân tích và đặt tên hoạt động
        dựa trên motion level và lịch sử
        """
        current_time    = time.time()
        avg_motion      = (
            sum(self.motion_history) /
            len(self.motion_history)
            if self.motion_history else 0
        )
        has_motion      = self.motion_level > 5

        if has_motion:
            self.last_motion_time   = current_time
            self.no_motion_start    = None
            self.still_seconds      = 0
        else:
            if self.no_motion_start is None:
                self.no_motion_start = current_time
            self.still_seconds = int(
                current_time - self.no_motion_start
            )

        # ── Phân loại hoạt động ──────────────────────
        if not has_motion and self.still_seconds > 60:
            self.activity = "absent"
            self.status   = (
                f"❌ Không có người "
                f"({self.still_seconds}s)"
            )

        elif not has_motion and self.still_seconds > 5:
            self.activity = "still"
            self.status   = (
                f"😑 Đứng yên / Ngồi yên "
                f"({self.still_seconds}s)"
            )

        elif self.motion_level > 60:
            self.activity = "high_activity"
            self.status   = "🏃 Chuyển động mạnh / Đứng dậy"

        elif self.motion_level > 30:
            self.activity = "medium_activity"
            self.status   = "✋ Chuyển động vừa / Cử động tay"

        elif self.motion_level > 10:
            self.activity = "low_activity"
            self.status   = "✍️  Đang viết / Gõ phím"

        elif self.motion_level > 5:
            self.activity = "slight_motion"
            self.status   = "📖 Đang đọc / Ít chuyển động"

        else:
            self.activity = "focused"
            self.status   = "🎯 Tập trung / Nhìn màn hình"

    def _draw_overlay(self, frame_bgr, thresh):
        """Vẽ thông tin lên frame"""
        h, w = frame_bgr.shape[:2]

        # ── Vẽ vùng chuyển động ──────────────────────
        color_map = {
            "high_activity"  : (0, 0, 255),    # Đỏ
            "medium_activity": (0, 165, 255),   # Cam
            "low_activity"   : (0, 255, 255),   # Vàng
            "slight_motion"  : (0, 255, 0),     # Xanh lá
            "focused"        : (255, 255, 0),   # Cyan
            "still"          : (200, 200, 200), # Xám
            "absent"         : (128, 128, 128), # Xám đậm
        }
        box_color = color_map.get(
            self.activity, (0, 255, 0)
        )

        for region in self.regions:
            cv2.rectangle(
                frame_bgr,
                (region["x"], region["y"]),
                (region["x"] + region["w"],
                 region["y"] + region["h"]),
                box_color, 2
            )

        # ── Background panel ─────────────────────────
        overlay = frame_bgr.copy()
        cv2.rectangle(
            overlay, (0, 0), (500, 130),
            (0, 0, 0), -1
        )
        cv2.addWeighted(
            overlay, 0.6,
            frame_bgr, 0.4,
            0, frame_bgr
        )

        # ── Text thông tin ───────────────────────────
        # Trạng thái chính
        cv2.putText(
            frame_bgr,
            self.status,
            (10, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85, (255, 255, 255), 2
        )

        # Motion level bar
        bar_w = int((self.motion_level / 100) * 300)
        bar_color = (
            (0, 255, 0)   if self.motion_level < 20
            else (0, 165, 255) if self.motion_level < 50
            else (0, 0, 255)
        )
        cv2.rectangle(
            frame_bgr,
            (10, 50), (310, 70),
            (50, 50, 50), -1
        )
        cv2.rectangle(
            frame_bgr,
            (10, 50), (10 + bar_w, 70),
            bar_color, -1
        )
        cv2.putText(
            frame_bgr,
            f"Motion: {self.motion_level}%",
            (10, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (200, 200, 200), 2
        )

        # Số vùng chuyển động
        cv2.putText(
            frame_bgr,
            f"Vung CD: {len(self.regions)}",
            (200, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (200, 200, 200), 2
        )

        # Thời gian đứng yên
        if self.still_seconds > 0:
            cv2.putText(
                frame_bgr,
                f"Dung yen: {self.still_seconds}s",
                (10, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (100, 200, 255), 2
            )

        # Timestamp góc phải
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(
            frame_bgr, timestamp,
            (w - 120, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8, (200, 200, 200), 2
        )

        return frame_bgr

    def get_info(self):
        """Trả về thông tin hiện tại"""
        return {
            "status"        : self.status,
            "activity"      : self.activity,
            "motion_level"  : self.motion_level,
            "region_count"  : len(self.regions),
            "still_seconds" : self.still_seconds,
            "motion_history": self.motion_history[-10:]
        }