# pose_detector.py
import cv2
import mediapipe as mp
import numpy as np
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config


class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_draw = mp.solutions.drawing_utils

        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,         # 0=nhanh, 1=cân bằng
            smooth_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )

        # Tracking vị trí
        self.person_present     = False
        self.absent_start       = None
        self.absent_duration    = 0
        self.last_seen          = None
        self.absence_log        = []

        # Buffer chống false positive khi nhiều người cùng hàng:
        # chỉ chuyển sang "vắng mặt" sau N frame liên tiếp không detect
        self._absence_buffer_count  = 0
        self._ABSENCE_BUFFER        = Config.ABSENCE_BUFFER_FRAMES
        self._ABSENCE_SHORT         = Config.ABSENCE_SHORT_THRESHOLD
        self._ABSENCE_LONG          = Config.ABSENCE_LONG_THRESHOLD

        # Vùng làm việc (calibrate khi lần đầu ngồi)
        self.workspace_defined  = False
        self.workspace_center   = None

        self.result = {
            "person_present"    : False,
            "sitting"           : False,
            "status"            : "Chưa phát hiện",
            "absent_duration"   : 0,
            "absence_level"     : "present",    # "present" | "briefly_away" | "absent"
            "posture"           : "unknown",
            "shoulder_level"    : 0,
        }

        print("✅ Pose Detector sẵn sàng!")

    def detect(self, frame_rgb, frame_bgr):
        """
        Nhận diện tư thế và vị trí người.
        Returns: frame_bgr đã vẽ overlay
        """
        h, w = frame_rgb.shape[:2]
        current_time = time.time()

        results = self.pose.process(frame_rgb)

        if not results.pose_landmarks:
            # Tăng buffer counter — không ngay lập tức chuyển "vắng mặt"
            self._absence_buffer_count += 1

            if self._absence_buffer_count >= self._ABSENCE_BUFFER:
                # Đã qua buffer → xử lý vắng mặt thực sự
                self._handle_absence(current_time)
                frame_bgr = self._draw_absent(frame_bgr)
            else:
                # Chưa qua buffer: giữ trạng thái cũ
                # (tránh nhấp nháy khi nhiều người cùng hàng)
                cv2.putText(
                    frame_bgr,
                    f"Checking... ({self._absence_buffer_count}/{self._ABSENCE_BUFFER})",
                    (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (255, 165, 0), 1
                )
            return frame_bgr

        # ── Thấy người → reset buffer ────────────────
        self._absence_buffer_count = 0
        landmarks = results.pose_landmarks.landmark
        self._handle_presence(current_time)

        def get_lm(idx):
            lm = landmarks[idx]
            return (int(lm.x * w), int(lm.y * h), lm.visibility)

        l_shoulder  = get_lm(self.mp_pose.PoseLandmark.LEFT_SHOULDER)
        r_shoulder  = get_lm(self.mp_pose.PoseLandmark.RIGHT_SHOULDER)
        l_hip       = get_lm(self.mp_pose.PoseLandmark.LEFT_HIP)
        r_hip       = get_lm(self.mp_pose.PoseLandmark.RIGHT_HIP)
        nose        = get_lm(self.mp_pose.PoseLandmark.NOSE)

        sitting, posture, shoulder_level = self._analyze_posture(
            l_shoulder, r_shoulder, l_hip, r_hip, nose, h, w
        )

        if not self.workspace_defined and sitting:
            mid_x = (l_shoulder[0] + r_shoulder[0]) // 2
            mid_y = (l_shoulder[1] + r_shoulder[1]) // 2
            self.workspace_center = (mid_x, mid_y)
            self.workspace_defined = True
            print(f"📍 Vùng làm việc đã xác định: {self.workspace_center}")

        self.result.update({
            "person_present"    : True,
            "sitting"           : sitting,
            "status"            : self._get_status(sitting, posture),
            "absent_duration"   : 0,
            "absence_level"     : "present",
            "posture"           : posture,
            "shoulder_level"    : shoulder_level,
        })

        self.mp_draw.draw_landmarks(
            frame_bgr,
            results.pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            self.mp_draw.DrawingSpec(
                color=(0, 255, 0), thickness=2, circle_radius=3
            ),
            self.mp_draw.DrawingSpec(
                color=(0, 165, 255), thickness=2
            )
        )
        frame_bgr = self._draw_posture_info(
            frame_bgr, l_shoulder, r_shoulder, posture, sitting
        )
        return frame_bgr

    def _analyze_posture(self, l_shoulder, r_shoulder,
                          l_hip, r_hip, nose, h, w):
        """Phân tích tư thế ngồi/đứng"""
        shoulder_level = (
            (l_shoulder[1] + r_shoulder[1]) / 2
        ) / h

        shoulder_visible = l_shoulder[2] > 0.5 and r_shoulder[2] > 0.5
        hip_visible      = l_hip[2] > 0.5 and r_hip[2] > 0.5

        sitting = False
        posture = "unknown"

        if shoulder_visible and hip_visible:
            shoulder_y  = (l_shoulder[1] + r_shoulder[1]) / 2
            hip_y       = (l_hip[1] + r_hip[1]) / 2
            # Nếu hông gần mép dưới frame (camera gần, chỉ thấy từ ngực trở lên)
            # → người đang ngồi chứ không phải đứng
            if hip_y > h * 0.75:
                sitting = True
                posture = "sitting_close"
            else:
                torso_ratio = (hip_y - shoulder_y) / h
                if torso_ratio < 0.35:
                    sitting = True
                    posture = "sitting"
                else:
                    sitting = False
                    posture = "standing"
        elif shoulder_visible and not hip_visible:
            sitting = True
            posture = "sitting_close"

        if sitting and shoulder_visible:
            shoulder_diff = abs(l_shoulder[1] - r_shoulder[1])
            if shoulder_diff > 30:
                posture = "slouching"
            elif shoulder_level > 0.6:
                posture = "hunching"
            else:
                posture = "sitting_good"

        return sitting, posture, shoulder_level

    def _classify_absence_level(self, duration):
        """
        Phân loại mức độ vắng mặt theo thời gian.

        Trả về một trong 3 mức:
          'briefly_away' — rời chỗ ngắn (< ABSENCE_LONG_THRESHOLD)
          'absent'       — vắng mặt chính thức (>= ABSENCE_LONG_THRESHOLD)
        """
        if duration >= self._ABSENCE_LONG:
            return "absent"
        return "briefly_away"

    def _handle_absence(self, current_time):
        """Xử lý khi xác nhận vắng mặt (sau khi qua buffer)"""
        if self.person_present:
            self.absent_start   = current_time
            self.person_present = False
            print(
                f"\n⚠️  Rời khỏi vị trí: "
                f"{time.strftime('%H:%M:%S')}"
            )

        if self.absent_start:
            self.absent_duration = int(current_time - self.absent_start)

        level  = self._classify_absence_level(self.absent_duration)
        mins   = self.absent_duration // 60
        secs   = self.absent_duration % 60

        if level == "absent":
            status = (
                f"❌ Vắng mặt {mins} phút {secs}s"
                f" (quá {self._ABSENCE_LONG // 60} phút)"
            )
        else:
            # briefly_away — phân biệt ngắn / dài hơn chút
            if self.absent_duration >= self._ABSENCE_SHORT:
                status = f"🚶 Rời chỗ ngắn {mins:02d}:{secs:02d}"
            else:
                status = f"⚠️ Rời khỏi vị trí {secs}s"

        self.result.update({
            "person_present"    : False,
            "sitting"           : False,
            "absent_duration"   : self.absent_duration,
            "absence_level"     : level,
            "status"            : status,
        })

    def _handle_presence(self, current_time):
        """Xử lý khi thấy người quay lại"""
        if not self.person_present:
            if self.absent_start:
                duration = int(current_time - self.absent_start)
                level    = self._classify_absence_level(duration)
                log_entry = {
                    "left_at"     : time.strftime(
                        '%H:%M:%S', time.localtime(self.absent_start)
                    ),
                    "returned_at" : time.strftime('%H:%M:%S'),
                    "duration"    : duration,
                    "level"       : level,
                }
                self.absence_log.append(log_entry)
                mins = duration // 60
                secs = duration % 60
                print(
                    f"\n✅ Quay lại sau {mins} phút {secs}s"
                    f" [{level}]"
                )

            self.person_present  = True
            self.absent_start    = None
            self.absent_duration = 0

        self.last_seen = current_time

    def _get_status(self, sitting, posture):
        status_map = {
            "sitting_good"  : "✅ Ngồi đúng tư thế",
            "sitting_close" : "✅ Đang ngồi làm việc",
            "sitting"       : "✅ Đang ngồi",
            "slouching"     : "⚠️ Ngồi lệch vai",
            "hunching"      : "⚠️ Đang khom lưng",
            "standing"      : "🚶 Đang đứng",
            "unknown"       : "❓ Đang phân tích...",
        }
        return status_map.get(posture, "❓ Không xác định")

    def _draw_absent(self, frame_bgr):
        """Vẽ overlay khi vắng mặt"""
        h, w = frame_bgr.shape[:2]
        level = self.result.get("absence_level", "briefly_away")

        # Màu overlay theo mức độ
        overlay_color = (0, 0, 80) if level == "absent" else (0, 30, 60)
        overlay = frame_bgr.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), overlay_color, -1)
        cv2.addWeighted(overlay, 0.2, frame_bgr, 0.8, 0, frame_bgr)

        if self.absent_duration > 0:
            mins = self.absent_duration // 60
            secs = self.absent_duration % 60

            if level == "absent":
                text  = f"VANG MAT: {mins:02d}:{secs:02d}"
                color = (0, 0, 255)         # Đỏ
            elif self.absent_duration >= self._ABSENCE_SHORT:
                text  = f"ROI CHO NGAN: {mins:02d}:{secs:02d}"
                color = (0, 140, 255)       # Cam
            else:
                text  = f"ROI VI TRI: {secs}s"
                color = (0, 200, 255)       # Vàng

            cv2.putText(
                frame_bgr, text,
                (w // 2 - 170, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1, color, 3
            )
            # Thanh tiến trình vắng mặt
            self._draw_absence_bar(frame_bgr, w, h)

        return frame_bgr

    def _draw_absence_bar(self, frame_bgr, w, h):
        """Vẽ thanh tiến trình thời gian vắng mặt"""
        bar_y  = h // 2 + 50
        bar_w  = w - 100
        bar_x  = 50

        # Nền thanh
        cv2.rectangle(
            frame_bgr,
            (bar_x, bar_y), (bar_x + bar_w, bar_y + 12),
            (50, 50, 50), -1
        )

        # Fill theo % tiến đến ngưỡng LONG
        ratio = min(1.0, self.absent_duration / self._ABSENCE_LONG)
        fill  = int(bar_w * ratio)
        color = (0, 0, 255) if ratio >= 1.0 else (
            (0, 140, 255) if self.absent_duration >= self._ABSENCE_SHORT
            else (0, 200, 255)
        )
        if fill > 0:
            cv2.rectangle(
                frame_bgr,
                (bar_x, bar_y), (bar_x + fill, bar_y + 12),
                color, -1
            )

        # Label ngưỡng SHORT
        short_x = bar_x + int(bar_w * self._ABSENCE_SHORT / self._ABSENCE_LONG)
        cv2.line(
            frame_bgr,
            (short_x, bar_y - 5), (short_x, bar_y + 17),
            (0, 200, 255), 2
        )
        cv2.putText(
            frame_bgr,
            f"{self._ABSENCE_SHORT // 60}p",
            (short_x - 10, bar_y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4, (0, 200, 255), 1
        )
        # Label ngưỡng LONG
        cv2.putText(
            frame_bgr,
            f"{self._ABSENCE_LONG // 60}p",
            (bar_x + bar_w - 20, bar_y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4, (0, 0, 255), 1
        )

    def _draw_posture_info(self, frame_bgr, l_shoulder,
                            r_shoulder, posture, sitting):
        """Vẽ đường nối vai với màu theo tư thế"""
        color_map = {
            "sitting_good"  : (0, 255, 0),
            "sitting_close" : (0, 255, 0),
            "sitting"       : (0, 255, 0),
            "slouching"     : (0, 165, 255),
            "hunching"      : (0, 165, 255),
            "standing"      : (0, 0, 255),
        }
        color = color_map.get(posture, (255, 255, 255))

        if l_shoulder[2] > 0.5 and r_shoulder[2] > 0.5:
            cv2.line(
                frame_bgr,
                (l_shoulder[0], l_shoulder[1]),
                (r_shoulder[0], r_shoulder[1]),
                color, 3
            )
        return frame_bgr

    def get_info(self):
        info = self.result.copy()
        info["absence_count"] = len(self.absence_log)
        info["absence_log"]   = self.absence_log[-5:]
        return info
