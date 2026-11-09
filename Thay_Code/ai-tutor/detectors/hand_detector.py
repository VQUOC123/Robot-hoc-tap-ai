# detectors/hand_detector.py
# HandDetector — MediaPipe Hands chạy trong background thread (AsyncWorker).
#
# Thiết kế:
#   - Kế thừa AsyncWorker: MediaPipe inference (~77ms) không block main loop.
#   - detect() là thin wrapper: submit frame + draw overlay từ cached result.
#   - Drawing (bbox, zone lines, phone score) chạy trong main thread (~1ms).
#   - Resize frame xuống HAND_INFERENCE_SIZE trước khi feed MediaPipe → nhanh hơn.
#   - MediaPipe Hands được khởi tạo trong background thread (thread-safety).
#
# API (backward compatible với code cũ):
#   detect(frame_rgb, frame_bgr) → frame_bgr với overlay
#   get_info()                   → dict (result cache)

import os
import sys
import cv2
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config        import Config
from utils.async_worker import AsyncWorker
from utils.image_utils  import resize_for_inference


# ── Default result khi chưa có data ───────────────────────────────────────────

def _default_result() -> dict:
    return {
        "hand_count"  : 0,
        "activity"    : "no_hands",
        "status"      : "Không thấy tay",
        "speed"       : 0.0,
        "positions"   : [],
        "hand_bboxes" : [],
        "zone"        : "none",
        "phone_score" : 0,
        "pen_grip"    : False,
        "timestamp"   : 0.0,
    }


# ── HandDetector ───────────────────────────────────────────────────────────────

class HandDetector(AsyncWorker):
    """
    MediaPipe Hands detector chạy inference trong background thread.

    detect() vẫn là entry point cho backward compatibility:
      1. submit(frame_bgr) → background thread nhận frame
      2. get_result() → lấy cached result (1-2 frame lag — không đáng kể)
      3. _draw_overlay() → vẽ bbox + zone lines lên frame_bgr (main thread, ~1ms)

    Usage (giống HandDetector cũ):
        hand_bgr = hands.detect(frame_rgb, frame_bgr)
        info = hands.get_info()
    """

    # Kích thước resize trước khi feed MediaPipe Hands
    # 480×360 thay vì 1280×720 → nhanh hơn ~3× cho MediaPipe, không ảnh hưởng accuracy
    # (landmark coordinates được normalize 0-1, sau đó map về original size)
    _INFERENCE_SIZE = 480

    def __init__(self) -> None:
        # Cache ngưỡng từ Config (đọc 1 lần, tránh Config lookup trong hot loop)
        self._ZONE_UPPER        = Config.HAND_ZONE_UPPER_RATIO
        self._ZONE_BOTTOM       = Config.HAND_ZONE_BOTTOM_RATIO
        # desk_y: ranh giới middle/bottom (mặt bàn, chuẩn hóa 0-1).
        # Khởi tạo theo cam_side, cập nhật động qua set_desk_y() từ main thread.
        _cam = Config.CAMERA_SIDE
        if _cam in ("right", "left"):
            self._desk_y = max(0.40, self._ZONE_BOTTOM - 0.08)
        elif _cam in ("front_right", "front_left"):
            self._desk_y = min(0.72, self._ZONE_BOTTOM + 0.10)
        else:
            self._desk_y = self._ZONE_BOTTOM
        self._SPEED_STILL       = Config.HAND_SPEED_STILL
        self._SPEED_TYPING_MAX  = Config.HAND_SPEED_TYPING_MAX
        self._SPEED_READING     = Config.HAND_SPEED_READING
        self._SPEED_GESTURE_MAX = Config.HAND_SPEED_GESTURE_MAX
        self._SPEED_FACE_MAX    = Config.HAND_SPEED_FACE_MAX
        self._PHONE_THRESH      = Config.PHONE_SCORE_THRESHOLD
        self._PHONE_SPEED_CUT   = Config.PHONE_MAX_HAND_SPEED

        # Speed tracking (background thread only)
        self._prev_positions:       list  = []
        self._hand_speeds:          list  = []
        self._phone_score_history:  list  = []
        self._MAX_SPEED_HISTORY          = 15
        self._MAX_PHONE_HISTORY          = 30

        # Result cache (read từ main thread qua get_info())
        self.result = _default_result()

        # MediaPipe khởi tạo trong _load_model() (background thread)
        self._mp_hands = None

        print("🔄 HandDetector khởi động (background thread)...")
        super().__init__()   # starts background thread → _load_model()

    # ── AsyncWorker Implementation ────────────────────────────────────

    def _load_model(self) -> None:
        """Khởi tạo MediaPipe Hands trong background thread."""
        import mediapipe as mp
        self._mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.25,
            min_tracking_confidence=0.25,
        )

    def _run_inference(self, frame_bgr: np.ndarray, meta=None) -> dict:
        """
        Chạy MediaPipe Hands inference. Chạy trong background thread.

        Args:
            frame_bgr : BGR frame (original size — 1280×720).
            meta      : Unused.

        Returns:
            dict với hand_count, activity, speed, zone, phone_score, pen_grip,
            positions, hand_bboxes — tất cả dùng tọa độ original frame.
        """
        orig_h, orig_w = frame_bgr.shape[:2]

        # Resize xuống _INFERENCE_SIZE để tăng tốc MediaPipe
        small, _ = resize_for_inference(frame_bgr, self._INFERENCE_SIZE)

        # MediaPipe cần RGB
        frame_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        mp_result = self._mp_hands.process(frame_rgb)

        hand_count  = 0
        positions   = []
        hand_bboxes = []
        pen_grip    = False

        if mp_result.multi_hand_landmarks:
            hand_count = len(mp_result.multi_hand_landmarks)

            for hand_lm in mp_result.multi_hand_landmarks:
                # Landmark coordinates normalize 0-1 → map về original size
                wrist_x = int(hand_lm.landmark[0].x * orig_w)
                wrist_y = int(hand_lm.landmark[0].y * orig_h)
                positions.append((wrist_x, wrist_y))

                # Bounding box trong tọa độ original
                xs = [int(lm.x * orig_w) for lm in hand_lm.landmark]
                ys = [int(lm.y * orig_h) for lm in hand_lm.landmark]
                x1 = max(0,      min(xs) - 20)
                y1 = max(0,      min(ys) - 20)
                x2 = min(orig_w, max(xs) + 20)
                y2 = min(orig_h, max(ys) + 20)
                hand_bboxes.append((x1, y1, x2, y2))

                if self._is_pen_grip(hand_lm, orig_w, orig_h):
                    pen_grip = True

        # Tính tốc độ
        avg_speed = self._compute_speed(positions)

        # Tính zone (dùng original frame dims)
        zone = self._classify_zone(positions, orig_h)

        # Phone score
        phone_score = self._calc_phone_score(hand_count, avg_speed, zone)

        # Phân loại activity
        activity, status = self._classify_activity(hand_count, avg_speed, zone, phone_score)

        # Pen grip override
        if pen_grip and zone == "bottom":
            activity = "writing"
            status   = "✍️  Đang viết (cầm bút)"

        return {
            "hand_count"  : hand_count,
            "activity"    : activity,
            "status"      : status,
            "speed"       : round(avg_speed, 1),
            "positions"   : positions,
            "hand_bboxes" : hand_bboxes,
            "zone"        : zone,
            "phone_score" : phone_score,
            "pen_grip"    : pen_grip,
            "timestamp"   : time.monotonic(),
        }

    # ── Public API (backward compatible) ─────────────────────────────

    def detect(self, frame_rgb: np.ndarray, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Submit frame cho background inference, draw overlay từ cached result.
        Thin wrapper — main loop không bị block bởi MediaPipe (~1ms thay vì ~77ms).

        Args:
            frame_rgb : RGB frame (không dùng trực tiếp, giữ cho compat).
            frame_bgr : BGR frame — submit cho inference + vẽ overlay lên đây.

        Returns:
            frame_bgr với overlay đã vẽ.
        """
        # Submit frame cho background thread (non-blocking)
        self.submit(frame_bgr)

        # Lấy cached result (có thể từ 1-2 frame trước — OK)
        cached = self.get_result()
        if cached is not None:
            self.result.update(cached)

        # Vẽ overlay lên frame hiện tại (main thread, ~1ms)
        return self._draw_overlay(frame_bgr, self.result)

    def get_info(self) -> dict:
        """Trả về result dict gần nhất (backward compatible)."""
        return self.result

    def set_desk_y(self, y: float) -> None:
        """
        Cập nhật ngưỡng mặt bàn (chuẩn hóa 0-1) từ main thread.
        Được gọi sau mỗi YOLO update — GIL-safe (float assignment atomic).
        Thay thế hardcoded HAND_ZONE_BOTTOM_RATIO, thích nghi với góc camera.
        """
        self._desk_y = float(y)

    # ── Inference Helpers (chạy trong background thread) ─────────────

    def _compute_speed(self, positions: list) -> float:
        """Tính tốc độ tay trung bình trên sliding window 15 frames."""
        current_speed = 0.0
        if positions and self._prev_positions:
            speeds = []
            for i, pos in enumerate(positions):
                if i < len(self._prev_positions):
                    prev = self._prev_positions[i]
                    dist = np.sqrt(
                        (pos[0] - prev[0]) ** 2 +
                        (pos[1] - prev[1]) ** 2
                    )
                    speeds.append(dist)
            if speeds:
                current_speed = float(np.mean(speeds))

        self._hand_speeds.append(current_speed)
        if len(self._hand_speeds) > self._MAX_SPEED_HISTORY:
            self._hand_speeds.pop(0)

        self._prev_positions = positions
        return float(np.mean(self._hand_speeds)) if self._hand_speeds else 0.0

    def _classify_zone(self, positions: list, frame_h: int) -> str:
        """Xác định vùng tay trong frame (upper / middle / bottom / none)."""
        if not positions:
            return "none"

        avg_y = float(np.mean([p[1] for p in positions]))

        # zone_bottom: dùng desk_y động (cập nhật từ YOLO keyboard/mouse)
        # thay vì cam_side hardcoded. Thích nghi tự động với mọi góc camera.
        zone_bottom = self._desk_y

        if avg_y < frame_h * self._ZONE_UPPER:
            return "upper"
        if avg_y < frame_h * zone_bottom:
            return "middle"
        return "bottom"

    def _calc_phone_score(self, hand_count: int, avg_speed: float, zone: str) -> int:
        """
        Tính điểm khả năng đang dùng điện thoại (0-100).
        Smooth theo thời gian (30-frame window).
        """
        from core import constants as C

        if hand_count == 0:
            self._phone_score_history.append(0)
            if len(self._phone_score_history) > self._MAX_PHONE_HISTORY:
                self._phone_score_history.pop(0)
            return 0

        score = 0
        if zone == "middle":
            score += C.PHONE_SCORE_ZONE_MIDDLE
        elif zone == "upper":
            score += C.PHONE_SCORE_ZONE_UPPER

        if avg_speed < 5:
            score += C.PHONE_SCORE_SPEED_STILL
        elif avg_speed < self._PHONE_SPEED_CUT:
            score += C.PHONE_SCORE_SPEED_SLOW
        elif avg_speed < 25:
            score += C.PHONE_SCORE_SPEED_MEDIUM

        if hand_count == 1:
            score += C.PHONE_SCORE_ONE_HAND
        elif hand_count == 2:
            score += C.PHONE_SCORE_TWO_HANDS

        score = min(100, score)

        self._phone_score_history.append(score)
        if len(self._phone_score_history) > self._MAX_PHONE_HISTORY:
            self._phone_score_history.pop(0)

        return int(np.mean(self._phone_score_history))

    def _classify_activity(
        self,
        hand_count: int,
        avg_speed:  float,
        zone:       str,
        phone_score: int,
    ) -> tuple[str, str]:
        """Phân loại hoạt động tay dựa trên vùng + tốc độ + phone_score."""
        if hand_count == 0:
            return "no_hands", "🙌 Không thấy tay"

        if zone == "bottom":
            if avg_speed < self._SPEED_STILL:
                return "typing_pause",  "⌨️  Tay trên bàn phím (nghỉ)"
            if avg_speed < self._SPEED_TYPING_MAX:
                return "typing",        "⌨️  Đang gõ phím"
            return "writing",           "✍️  Đang viết bài"

        if zone == "middle":
            if phone_score >= self._PHONE_THRESH:
                return "possible_phone",  "📱 Có thể đang cầm điện thoại"
            if avg_speed < self._SPEED_READING:
                return "reading_gesture", "📖 Tay nghỉ / Đang đọc"
            if avg_speed < self._SPEED_GESTURE_MAX:
                return "gesturing",       "🖐 Đang cử động tay"
            return "active_hands",        "✋ Tay chuyển động nhiều"

        if zone == "upper":
            if phone_score >= Config.PHONE_SCORE_UPPER_THRESHOLD:
                return "possible_phone",   "📱 Có thể đang cầm điện thoại"
            if avg_speed < self._SPEED_FACE_MAX:
                return "face_touch",       "😴 Tay gần mặt / Mệt mỏi?"
            return "distracted_hands",     "⚠️ Tay chuyển động bất thường"

        return "unknown", "❓ Không xác định"

    def _is_pen_grip(self, hand_landmarks, w: int, h: int) -> bool:
        """
        Phát hiện tư thế cầm bút qua pinch ratio.

        Tỷ lệ pinch = dist(thumb_tip, index_tip) / dist(wrist, middle_mcp)
          < 0.55 → pen grip (pinch chặt quanh bút mỏng)
          ≥ 0.55 → phone grip / open hand

        Threshold 0.55 (từ 0.45): khi viết theo tripod grip, thumb và index
        cách nhau ~3-4cm, hand_px ~8-10cm → ratio ~0.38-0.50.
        Noise từ góc camera / occlusion có thể đẩy ratio lên 0.46-0.52 → 0.45 quá chặt.
        Phone grip: thumb-to-index ~7-10cm → ratio ~0.8-1.2 → an toàn với 0.55.
        """
        lm    = hand_landmarks.landmark
        thumb = lm[4]
        index = lm[8]
        wrist = lm[0]
        m_mcp = lm[9]

        pinch_px = np.sqrt(
            ((thumb.x - index.x) * w) ** 2 +
            ((thumb.y - index.y) * h) ** 2
        )
        hand_px = max(1.0, np.sqrt(
            ((wrist.x - m_mcp.x) * w) ** 2 +
            ((wrist.y - m_mcp.y) * h) ** 2
        ))
        return (pinch_px / hand_px) < 0.55

    # ── Drawing (main thread) ─────────────────────────────────────────

    def _draw_overlay(self, frame_bgr: np.ndarray, result: dict) -> np.ndarray:
        """
        Vẽ overlay lên frame_bgr từ cached result dict.
        Chạy trong main thread — chỉ dùng OpenCV primitives (~1ms).
        """
        h, w = frame_bgr.shape[:2]
        zone        = result.get("zone", "none")
        phone_score = result.get("phone_score", 0)
        hand_bboxes = result.get("hand_bboxes", [])

        # Vẽ hand bounding boxes
        for (x1, y1, x2, y2) in hand_bboxes:
            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (255, 165, 0), 2)

        # Dùng desk_y động (đồng bộ với _classify_zone)
        zone_bottom = self._desk_y

        # Đường phân vùng zone
        cv2.line(frame_bgr,
                 (0, int(h * self._ZONE_UPPER)), (w, int(h * self._ZONE_UPPER)),
                 (50, 50, 50), 1)
        cv2.line(frame_bgr,
                 (0, int(h * zone_bottom)), (w, int(h * zone_bottom)),
                 (50, 50, 50), 1)

        # Label vùng hiện tại
        _zone_labels = {
            "bottom": "VUNG BAN/BAN PHIM",
            "middle": "VUNG GIUA",
            "upper" : "VUNG TREN",
        }
        _zone_colors = {
            "bottom": (0, 255, 0),
            "middle": (0, 165, 255),
            "upper" : (0, 0, 255),
        }
        if zone in _zone_labels:
            color = _zone_colors[zone]
            cv2.putText(
                frame_bgr,
                _zone_labels[zone],
                (w - 300, int(h * zone_bottom) + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, color, 1,
            )

        # Phone score (khi đáng kể)
        if phone_score >= 40:
            bar_color = (0, 165, 255) if phone_score < self._PHONE_THRESH else (0, 0, 255)
            cv2.putText(
                frame_bgr,
                f"Phone: {phone_score}%",
                (w - 150, int(h * self._ZONE_BOTTOM) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45, bar_color, 1,
            )

        return frame_bgr
