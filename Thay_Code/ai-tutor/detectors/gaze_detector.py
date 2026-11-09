# gaze_detector.py
import cv2
import mediapipe as mp
import numpy as np
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config


class GazeDetector:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_draw      = mp.solutions.drawing_utils

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.4,
            min_tracking_confidence=0.35
        )

        # Ngưỡng góc đầu từ Config (điều chỉnh được qua .env hoặc constants.py)
        self._PITCH_UP      = Config.GAZE_PITCH_UP
        self._PITCH_DOWN    = Config.GAZE_PITCH_DOWN
        self._YAW_THRESH    = Config.GAZE_YAW_THRESHOLD
        self._ROLL_THRESH   = Config.GAZE_ROLL_THRESHOLD
        self._YAW_OFFSET    = Config.CAMERA_YAW_OFFSET  # Hiệu chỉnh camera nghiêng

        self.result = {
            "face_detected"         : False,
            "gaze_direction"        : "unknown",
            "status"                : "Không thấy mặt",
            "pitch"                 : 0,
            "yaw"                   : 0,
            "roll"                  : 0,
            "distraction_seconds"   : 0,    # Giây liên tiếp nhìn sang hướng khác
        }

        self.gaze_history   = []
        self.MAX_HISTORY    = 20

        # Tracking thời gian mất tập trung liên tiếp
        self._distraction_start = None
        self._DISTRACTION_GAZES = {"looking_left", "looking_right", "looking_up"}

        print("✅ Gaze Detector sẵn sàng!")

    def detect(self, frame_rgb, frame_bgr):
        """
        Nhận diện hướng nhìn qua góc đầu.
        Returns: frame_bgr đã vẽ overlay
        """
        h, w = frame_rgb.shape[:2]
        current_time = time.time()

        results = self.face_mesh.process(frame_rgb)

        if not results.multi_face_landmarks:
            self.result.update({
                "face_detected"         : False,
                "gaze_direction"        : "absent",
                "status"                : "❌ Không thấy mặt",
                "pitch": 0, "yaw": 0, "roll": 0,
                "distraction_seconds"   : 0,
            })
            self._distraction_start = None
            return frame_bgr

        face_landmarks = results.multi_face_landmarks[0]

        def get_point(idx):
            lm = face_landmarks.landmark[idx]
            return np.array([lm.x * w, lm.y * h, lm.z])

        # Các điểm key trên khuôn mặt
        chin        = get_point(152)
        forehead    = get_point(10)
        left_ear    = get_point(234)
        right_ear   = get_point(454)
        left_eye    = get_point(33)
        right_eye   = get_point(263)

        # ── Tính góc đầu ──────────────────────────────
        # Pitch: cúi/ngửa đầu (âm = cúi, dương = ngửa)
        face_vertical = chin - forehead
        pitch = np.degrees(np.arctan2(
            face_vertical[2], face_vertical[1]
        ))

        # Yaw: quay trái/phải (dương = quay trái, âm = quay phải)
        face_horizontal = right_ear - left_ear
        yaw = np.degrees(np.arctan2(
            face_horizontal[2], face_horizontal[0]
        ))

        # Roll: nghiêng đầu
        eye_line = right_eye - left_eye
        roll = np.degrees(np.arctan2(
            eye_line[1], eye_line[0]
        ))

        # Áp dụng offset camera (hiệu chỉnh camera đặt nghiêng/bên cạnh)
        adjusted_yaw = yaw - self._YAW_OFFSET

        direction, status = self._classify_gaze(pitch, adjusted_yaw, roll)
        distraction_seconds = self._track_distraction(direction, current_time)

        self.gaze_history.append(direction)
        if len(self.gaze_history) > self.MAX_HISTORY:
            self.gaze_history.pop(0)

        self.result.update({
            "face_detected"         : True,
            "gaze_direction"        : direction,
            "status"                : status,
            "pitch"                 : round(pitch, 1),
            "yaw"                   : round(adjusted_yaw, 1),
            "roll"                  : round(roll, 1),
            "distraction_seconds"   : distraction_seconds,
        })

        frame_bgr = self._draw_gaze(
            frame_bgr, face_landmarks, w, h,
            direction, pitch, adjusted_yaw, roll, distraction_seconds
        )
        return frame_bgr

    def _classify_gaze(self, pitch, yaw, roll):
        """
        Phân loại hướng nhìn từ góc đầu.
        Các ngưỡng đọc từ Config (→ constants.py → .env override).
        """
        if pitch > self._PITCH_UP:
            return "looking_up",     "⬆️  Nhìn lên / Mơ màng"

        if pitch < self._PITCH_DOWN:
            return "looking_down",   "📚 Nhìn xuống sách/vở/điện thoại"

        if yaw > self._YAW_THRESH:
            return "looking_left",   "👈 Nhìn sang trái"

        if yaw < -self._YAW_THRESH:
            return "looking_right",  "👉 Nhìn sang phải"

        if abs(roll) > self._ROLL_THRESH:
            return "head_tilt",      "😴 Nghiêng đầu / Có thể buồn ngủ"

        return "looking_screen",     "🖥️  Đang nhìn màn hình"

    def _track_distraction(self, direction, current_time):
        """
        Theo dõi thời gian liên tiếp nhìn sang hướng gây mất tập trung.
        Reset về 0 ngay khi quay lại nhìn màn hình / nhìn xuống.
        """
        if direction in self._DISTRACTION_GAZES:
            if self._distraction_start is None:
                self._distraction_start = current_time
            return int(current_time - self._distraction_start)
        else:
            self._distraction_start = None
            return 0

    def _draw_gaze(self, frame_bgr, face_landmarks,
                   w, h, direction, pitch, yaw, roll,
                   distraction_seconds):
        """Vẽ thông tin hướng nhìn lên frame"""
        color_map = {
            "looking_screen": (0, 255, 0),
            "looking_down"  : (0, 255, 255),
            "looking_up"    : (0, 165, 255),
            "looking_left"  : (0, 0, 255),
            "looking_right" : (0, 0, 255),
            "head_tilt"     : (128, 0, 255),
        }
        color = color_map.get(direction, (255, 255, 255))

        nose = face_landmarks.landmark[1]
        nx   = int(nose.x * w)
        ny   = int(nose.y * h)

        # Mũi tên hướng nhìn
        arrow_len = 60
        arrow_x = int(nx + arrow_len * np.sin(np.radians(yaw)))
        arrow_y = int(ny + arrow_len * np.sin(np.radians(pitch)))
        cv2.arrowedLine(
            frame_bgr, (nx, ny), (arrow_x, arrow_y),
            color, 3, tipLength=0.3
        )
        cv2.circle(frame_bgr, (nx, ny), 5, color, -1)

        # Thông tin góc
        cv2.putText(
            frame_bgr,
            f"P:{pitch:.0f} Y:{yaw:.0f} R:{roll:.0f}",
            (nx - 60, ny - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, color, 1
        )

        # Hiển thị thời gian mất tập trung nếu đáng kể
        if distraction_seconds >= 2:
            cv2.putText(
                frame_bgr,
                f"Mat tap trung: {distraction_seconds}s",
                (nx - 80, ny - 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 0, 255), 2
            )

        return frame_bgr

    def get_dominant_gaze(self):
        """Hướng nhìn phổ biến nhất trong lịch sử"""
        if not self.gaze_history:
            return "unknown"
        return max(set(self.gaze_history), key=self.gaze_history.count)

    def get_info(self):
        return self.result
