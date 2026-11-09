# detectors/multi_person_tracker.py
# Theo dõi nhiều người với YOLO (person anchor) + FaceDetector (gaze) + Hands.
#
# Kiến trúc:
#   - YOLO (background thread) → person bboxes làm anchor chính
#     → hoạt động với mặt nghiêng 60-90° (profile view)
#   - FaceDetector (round-robin, 1 crop/frame) → hướng nhìn + biểu cảm
#     → Backend 1: Face Landmarker (frontal ≤70°) + blendshapes
#     → Backend 2: MediaPipe Pose fallback (mọi góc, pitch fixed)
#   - MediaPipe Hands (full frame) → gán tay vào nearest person bbox
#   - PersonSession (1/người) → ActivityAnalyzer riêng
#
# Threading:
#   - Main thread: FaceDetector + Hands + session analysis
#   - YOLO worker thread (trong YoloDetector): inference async

import cv2
import numpy as np
import time
import sys
import os
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config
from core.thermal import ThermalManager
from detectors.face_detector import FaceDetector
from detectors.hand_detector import HandDetector
from detectors.yolo_detector import YoloDetector, YoloResult
from analyzers.activity_analyzer import ActivityAnalyzer


# ── Màu sắc cho từng người (BGR) ─────────────────────────────────────────────
_PERSON_COLORS = [
    (50,  200, 255),   # A — vàng cam
    (50,  255, 50),    # B — xanh lá
    (255, 100, 50),    # C — xanh dương
    (200, 50,  255),   # D — tím
    (50,  200, 200),   # E — vàng
]
_LABEL_CHARS = list("ABCDE")

# Màu bounding box theo loại vật thể (BGR)
_OBJECT_COLORS = {
    "phone"   : (0,   0,   255),   # đỏ
    "laptop"  : (255, 100,   0),   # xanh dương
    "monitor" : (200,  80,   0),   # xanh dương đậm
    "mouse"   : (0,   255, 200),   # xanh lá nhạt
    "keyboard": (0,   200,   0),   # xanh lá
    "book"    : (0,   165, 255),   # cam
    "bottle"  : (200, 200,   0),   # cyan
    "cup"     : (180, 105, 255),   # hồng
}


def _get_color(idx: int) -> tuple:
    return _PERSON_COLORS[idx % len(_PERSON_COLORS)]


def _label(idx: int) -> str:
    return _LABEL_CHARS[idx] if idx < len(_LABEL_CHARS) else f"P{idx}"


def desk_y_from_yolo(yolo_result, frame_h: int) -> float | None:
    """
    Ước tính mặt bàn (y chuẩn hóa 0-1) từ keyboard/mouse YOLO bboxes.

    Keyboard và mouse luôn nằm trên mặt bàn → y_center của chúng = desk level.
    Trả về None nếu không phát hiện được (cần dùng EMA từ frame trước).
    """
    if not yolo_result or frame_h <= 0:
        return None
    desk_ys = [
        b.cy / frame_h
        for b in yolo_result.boxes
        if b.cls_name in ("keyboard", "mouse") and 0.25 < b.cy / frame_h < 0.95
    ]
    return float(sum(desk_ys) / len(desk_ys)) if desk_ys else None


def build_object_context(person_bbox: tuple, yolo_result,
                          margin_x_ratio: float = 0.2,
                          hand_bboxes: list = None) -> dict:
    """
    Trả về dict object context từ YOLO result cho 1 person bbox.
    Các key mới này được merge vào pose_info (additive, backward compatible).

    hand_bboxes: list[(x1,y1,x2,y2)] pixel coords của tay — dùng để check
                 khoảng cách phone↔tay (phone_near_hand).
    """
    empty = {
        "has_phone"       : False,
        "has_laptop"      : False,
        "has_monitor"     : False,
        "has_screen"      : False,   # True khi có laptop HOẶC monitor
        "has_keyboard"    : False,
        "has_mouse"       : False,
        "has_book"        : False,
        "has_pen"         : False,
        "has_notepaper"   : False,
        "phone_in_hand"   : False,   # phone Y ≤ top 55% của person bbox → đang cầm
        "phone_near_hand" : False,   # phone bbox chồng/gần hand bbox → tay đang cầm
        "has_bottle"      : False,
        "has_cup"         : False,
        "has_wine_glass"  : False,
        "has_fork"        : False,
        "has_spoon"       : False,
        "has_bowl"        : False,
        # _in_reach = bottle/cup nằm trong phần thân trên (không chỉ trên bàn)
        # Dùng cho eating detection để tránh false positive khi cup để yên trên bàn
        "bottle_in_reach" : False,
        "cup_in_reach"    : False,
        "detected_objects": [],
        "object_scores"   : {},
    }
    if yolo_result is None or person_bbox is None:
        return empty

    objects = yolo_result.objects_near(person_bbox, margin_x_ratio=margin_x_ratio)
    if not objects:
        return empty

    ctx = dict(empty)
    ctx["detected_objects"] = []
    ctx["object_scores"]    = {}

    for box in objects:
        name = box.cls_name
        if name not in ctx["detected_objects"]:
            ctx["detected_objects"].append(name)
        ctx["object_scores"][name] = round(box.score, 2)
        if name == "phone":
            ctx["has_phone"] = True
            if person_bbox is not None:
                x1_p, y1_p, x2_p, y2_p = person_bbox
                p_h = max(1, y2_p - y1_p)
                p_w = max(1, x2_p - x1_p)
                # phone_in_hand: Y-position heuristic
                # Threshold mở rộng từ 0.55 → 0.75: khi ngồi cầm/nhìn điện thoại
                # đặt trên bàn, phone center thường ở 65-75% chiều cao person bbox.
                # 0.55 chỉ bắt phone cầm trên cao (ngang ngực/bụng).
                if box.cy <= y1_p + 0.75 * p_h:
                    ctx["phone_in_hand"] = True
                # phone_near_hand: phone bbox chồng/gần hand bbox
                # Chính xác hơn phone_in_hand — dùng tọa độ tay thực từ MediaPipe
                if hand_bboxes:
                    prox = max(p_w, p_h) * 0.12   # 12% kích thước person = ~15cm
                    for hx1, hy1, hx2, hy2 in hand_bboxes:
                        if (hx1 - prox <= box.cx <= hx2 + prox
                                and hy1 - prox <= box.cy <= hy2 + prox):
                            ctx["phone_near_hand"] = True
                            break
        if name == "laptop":
            # Heuristic: laptop bbox center ở nửa TRÊN person bbox (ngực/vai)
            # → người đang giữ vật phẳng trước người (sách, vở, giấy).
            # Laptop thật luôn nằm ở nửa DƯỚI (trên bàn, phần bụng/đùi trở xuống).
            # Tránh false: screen=True khi học sinh cầm sách → không phải working_computer.
            if (person_bbox is not None
                    and box.cy <= person_bbox[1] + 0.50 * max(1, person_bbox[3] - person_bbox[1])):
                ctx["has_book"] = True   # reclassify: vật phẳng cầm trên tay → sách/vở
            else:
                ctx["has_laptop"] = True; ctx["has_screen"] = True
        elif name == "monitor":  ctx["has_monitor"]  = True; ctx["has_screen"] = True
        if name == "mouse":    ctx["has_mouse"]    = True
        if name == "keyboard": ctx["has_keyboard"] = True
        if name == "book":        ctx["has_book"]      = True
        if name == "pen":         ctx["has_pen"]       = True
        if name == "pencil_case": ctx["has_pen"]       = True
        if name == "notepaper":   ctx["has_notepaper"] = True
        if name == "bottle":
            ctx["has_bottle"] = True
            # Check vị trí dọc: bottle phải trong phần thân trên (không chỉ trên bàn)
            if person_bbox is not None:
                x1_p, y1_p, x2_p, y2_p = person_bbox
                p_h = max(1, y2_p - y1_p)
                if box.cy <= y1_p + 0.75 * p_h:
                    ctx["bottle_in_reach"] = True
        if name in ("cup", "wine_glass"):
            ctx["has_cup"] = True
            if name == "wine_glass":
                ctx["has_wine_glass"] = True
            if person_bbox is not None:
                x1_p, y1_p, x2_p, y2_p = person_bbox
                p_h = max(1, y2_p - y1_p)
                if box.cy <= y1_p + 0.75 * p_h:
                    ctx["cup_in_reach"] = True
        if name == "fork":
            ctx["has_fork"] = True
        if name == "spoon":
            ctx["has_spoon"] = True
        if name == "bowl":
            ctx["has_bowl"] = True

    # Phone được detect → loại bỏ "book" (YOLO hay nhầm phone với book)
    if ctx["has_phone"] and "book" in ctx["detected_objects"]:
        ctx["detected_objects"].remove("book")
        ctx["has_book"] = False

    return ctx


# ── PersonSession ─────────────────────────────────────────────────────────────

class PersonSession:
    """
    Trạng thái của 1 người đang được theo dõi.
    Mỗi person có ActivityAnalyzer riêng để giữ lịch sử độc lập.
    """

    def __init__(self, label: str, face_cx: float):
        self.label          = label
        self.face_cx        = face_cx      # X trung tâm (từ YOLO bbox)
        self.missing_frames = 0
        self.analyzer       = ActivityAnalyzer()

        # Distraction tracking
        self._distraction_start: float | None = None
        self._DISTRACTION_GAZES = {"looking_left", "looking_right", "looking_up"}

        # Absence tracking
        self._absent_start: float | None    = None
        self._absent_duration: int          = 0

        # Face-hidden tracking: YOLO thấy người nhưng face detection fail
        # Khi kéo dài → signal cho phone/drowsy (mặt bị che/cúi)
        self._face_hidden_start: float | None = None
        self._face_hidden_seconds: int        = 0

        self.last_result = {}

    def _update_distraction(self, gaze_dir: str, now: float) -> int:
        """Trả về số giây nhìn sang nơi khác liên tiếp."""
        if gaze_dir in self._DISTRACTION_GAZES:
            if self._distraction_start is None:
                self._distraction_start = now
            return int(now - self._distraction_start)
        else:
            self._distraction_start = None
            return 0

    def _update_absence(self, face_present: bool, now: float) -> tuple:
        """Cập nhật absent timer. Trả về (absent_duration, absence_level).

        Buffer ABSENCE_BUFFER_FRAMES frame liên tiếp mới bắt đầu tính absent.
        Tránh false positive khi YOLO miss ngắn (ánh sáng, góc camera, bị che).
        """
        if face_present:
            self._absent_start    = None
            self._absent_duration = 0
            return 0, "present"

        # Buffer: trong N frame đầu miss → coi như vẫn present
        if self.missing_frames < Config.ABSENCE_BUFFER_FRAMES:
            return 0, "present"

        if self._absent_start is None:
            self._absent_start = now

        self._absent_duration = int(now - self._absent_start)
        dur = self._absent_duration

        if dur >= Config.ABSENCE_LONG_THRESHOLD:
            return dur, "absent"
        return dur, "briefly_away"

    def update(self, pose_gaze: dict | None, hand_info: dict,
               w: int, h: int, now: float,
               yolo_objects: dict = None,
               yolo_tracked: bool = False) -> dict:
        """
        Cập nhật trạng thái với Pose gaze result + hand info + YOLO objects.

        pose_gaze    : output của _compute_pose_gaze() hoặc None (không detect được)
        hand_info    : dict từ HandDetector
        yolo_objects : dict object context từ build_object_context()
        yolo_tracked : True nếu YOLO vẫn track body (person bbox tồn tại)
        """
        face_present   = pose_gaze is not None
        person_present = face_present or yolo_tracked

        # ── Gaze từ Pose result ─────────────────────────────────────
        if face_present:
            gaze_dir = pose_gaze.get("gaze_direction", "looking_screen")
            pitch    = pose_gaze.get("pitch", 0.0)
            yaw      = pose_gaze.get("yaw", 0.0)
            roll     = pose_gaze.get("roll", 0.0)
            gaze_status = pose_gaze.get("status", "")
        else:
            # YOLO tracked but no face → "unknown" (person visible, gaze indeterminate)
            # No YOLO, no face → "absent" (person left)
            gaze_dir = "unknown" if yolo_tracked else "absent"
            pitch = yaw = roll = 0.0
            gaze_status = "YOLO only — không detect được mặt" if yolo_tracked \
                          else "Không detect được"

        distraction_s = self._update_distraction(gaze_dir, now)
        absent_dur, absence_level = self._update_absence(person_present, now)

        # Face-hidden: YOLO thấy người nhưng mặt không detect được
        # Từ camera chếch bên, mặt bị che thường = cúi nhìn phone / ngủ
        if yolo_tracked and not face_present:
            if self._face_hidden_start is None:
                self._face_hidden_start = now
            self._face_hidden_seconds = int(now - self._face_hidden_start)
        else:
            self._face_hidden_start = None
            self._face_hidden_seconds = 0

        gaze_info = {
            "face_detected"       : face_present,
            "gaze_direction"      : gaze_dir,
            "pitch"               : pitch,
            "yaw"                 : yaw,
            "roll"                : roll,
            "distraction_seconds" : distraction_s,
            "face_hidden_seconds" : self._face_hidden_seconds,
            "status"              : gaze_status,
            # Expressions (blendshapes) cho DrowsinessTracker
            "expressions"         : pose_gaze.get("expressions", {})
                                    if pose_gaze else {},
        }

        # ── Pose info (với YOLO object context merge vào) ──────────
        pose_info = {
            "person_present" : person_present,
            "sitting"        : person_present,
            "absent_duration": absent_dur,
            "absence_level"  : absence_level,
            "posture"        : "sitting_good" if face_present
                               else ("unknown" if yolo_tracked else "unknown"),
            "shoulder_level" : 0.5,
            "status"         : "",
            # Additive: YOLO object context (ActivityAnalyzer đọc nếu có)
            **(yolo_objects or {}),
        }

        result = self.analyzer.analyze(hand_info, gaze_info, pose_info)
        self.last_result = result
        return result


# ── MultiPersonTracker ────────────────────────────────────────────────────────

class MultiPersonTracker:
    """
    Theo dõi nhiều người trong cùng 1 frame.

    Pipeline mỗi frame:
      1. YOLOv8n (async) → person bboxes + object bboxes
      2. Match YOLO person bboxes → PersonSession labels (nearest X-center)
      3. Pose (round-robin, 1 crop/frame) → gaze từ nose+shoulder
      4. HandDetector (full frame) → gán tay vào nearest person bbox
      5. Per-session update (gaze + hand + objects) → activity + focus score
      6. Vẽ overlay
      7. Thermal check mỗi 30 frame

    Interface không đổi: process(frame_rgb, frame_bgr) → (frame_bgr, list[dict])
    """

    def __init__(self, imx500=None, picam2=None):
        """
        imx500: IMX500 device object từ CameraModule (None → CPU-only YOLO).
        picam2: Picamera2 instance (cần cho IMX500 coordinate conversion).
        Dependency Injection cho phép unit test và dễ swap backend.
        """
        self._max_persons  = Config.MAX_PERSONS
        self._label_pool   = list("ABCDE")[:self._max_persons]
        self._MATCH_DIST   = Config.PERSON_MATCH_DISTANCE
        self._MISSING_THRESH = Config.PERSON_MISSING_FRAMES

        # ── Detectors ───────────────────────────────────────────────
        # YOLO: background thread, person + object detection
        # IMX500 mode: primary YOLO chạy trên camera chip, secondary+tertiary trên CPU
        self.yolo = (
            YoloDetector(imx500=imx500, picam2=picam2)
            if Config.YOLO_ENABLED else None
        )

        # FaceDetector: quản lý Face Landmarker + Pose fallback + cam auto-detect
        # (thay thế inline Pose trực tiếp — clean, extensible)
        self.face_detector = FaceDetector()

        # Hands: chạy trên full frame
        self.hand_detector = HandDetector()

        # ── Dynamic desk plane ───────────────────────────────────────
        # desk_y_ema: mặt bàn (y chuẩn hóa 0-1) ước tính từ YOLO keyboard/mouse.
        # Thích nghi với mọi góc camera (cúi xuống/ngẩng lên/trái/phải).
        # Khởi tạo theo cam_side, cập nhật dần qua EMA (alpha=0.03, ~10s convergence).
        _cam = Config.CAMERA_SIDE
        if _cam in ("right", "left"):
            _desk_default = max(0.40, Config.HAND_ZONE_BOTTOM_RATIO - 0.08)
        elif _cam in ("front_right", "front_left"):
            _desk_default = min(0.72, Config.HAND_ZONE_BOTTOM_RATIO + 0.10)
        else:
            _desk_default = Config.HAND_ZONE_BOTTOM_RATIO   # 0.52
        self._desk_y_ema: float = _desk_default

        # ── Session management ───────────────────────────────────────
        self._sessions: dict[str, PersonSession] = {}

        # ── Face cache (round-robin) ─────────────────────────────────
        # label → gaze_info dict (to_gaze_info() output)
        self._face_cache:     dict[str, dict] = {}
        self._face_cache_age: dict[str, int]  = {}
        self._face_rr_idx = 0                        # round-robin index

        # ── Wrist fallback speed tracking ─────────────────────────────
        self._wrist_prev_positions: dict[str, list] = {}   # label → [(x, y), ...]
        self._wrist_speed_history: dict[str, list] = {}    # label → [speed, ...]

        # ── Frame counter + thermal ──────────────────────────────────
        self._frame_count = 0
        self._thermal     = ThermalManager()
        self._extra_skip  = 0
        self._extra_sleep = 0.0

        # ── Display flags (controlled via /api/display) ───────────────
        self.show_yolo_boxes = True

        print(f"✅ MultiPersonTracker (YOLO+FaceDetector) — tối đa {self._max_persons} người: "
              f"{', '.join(self._label_pool)}")

    # ── IMX500 Interface ──────────────────────────────────────────────

    def feed_imx500_metadata(self, metadata: dict) -> None:
        """
        Delegate IMX500 camera metadata tới YoloDetector để cập nhật primary boxes.
        Gọi từ main thread ngay sau camera.capture_frame(), trước process().
        No-op nếu YOLO disabled hoặc metadata là None.
        """
        if self.yolo is not None and metadata is not None:
            self.yolo.feed_imx500_metadata(metadata)

    # ── YOLO helpers ──────────────────────────────────────────────────

    def _get_person_bboxes(self) -> list:
        """
        Lấy tối đa MAX_PERSONS person bboxes gần camera nhất (diện tích bbox lớn nhất).
        Sorted trái → phải sau khi lọc.
        """
        if self.yolo is None:
            return []
        result = self.yolo.get_result()
        if result is None:
            return []
        persons = result.persons()
        if not persons:
            return []
        # Chọn MAX_PERSONS người có diện tích bbox lớn nhất (gần camera nhất)
        persons.sort(key=lambda b: (b.x2 - b.x1) * (b.y2 - b.y1), reverse=True)
        persons = persons[:self._max_persons]
        # Re-sort trái → phải
        persons.sort(key=lambda b: b.x1)
        return [p.as_tuple() for p in persons]

    # ── Session matching ──────────────────────────────────────────────

    def _match_yolo_to_sessions(self, person_bboxes: list, now: float) -> dict:
        """
        Gán YOLO person bboxes → session labels bằng nearest X-center.
        Chỉ match vào session ĐANG ACTIVE (missing_frames < MISSING_THRESH).
        Session dormant không được nhận người mới → tránh label swap.
        Xóa session sau MISSING_THRESH * 4 frames (~18s ở 10fps).
        Returns: {label → (x1, y1, x2, y2)}
        """
        used_labels: set    = set()
        label_to_bbox: dict = {}

        if not person_bboxes:
            for lbl in list(self._sessions.keys()):
                sess = self._sessions[lbl]
                sess.missing_frames += 1
                sess._update_absence(False, now)
                if sess.missing_frames > self._MISSING_THRESH * 4:
                    print(f"\n  Xoa session {lbl}")
                    del self._sessions[lbl]
                    self._face_cache.pop(lbl, None)
                    self._face_cache_age.pop(lbl, None)
                    self._wrist_prev_positions.pop(lbl, None)
                    self._wrist_speed_history.pop(lbl, None)
            return {}

        # Sort bboxes trái → phải theo center X
        bboxes_lr = sorted(person_bboxes, key=lambda b: (b[0] + b[2]) / 2)

        for bbox in bboxes_lr:
            cx = (bbox[0] + bbox[2]) / 2.0

            # Chỉ match vào session đang ACTIVE (recently seen)
            best_lbl  = None
            best_dist = self._MATCH_DIST + 1

            for lbl, sess in self._sessions.items():
                if lbl in used_labels:
                    continue
                if sess.missing_frames >= self._MISSING_THRESH:
                    continue   # dormant — không nhận người mới
                d = abs(cx - sess.face_cx)
                if d < best_dist:
                    best_dist = d
                    best_lbl  = lbl

            if best_lbl:
                label_to_bbox[best_lbl] = bbox
                self._sessions[best_lbl].face_cx        = cx
                self._sessions[best_lbl].missing_frames = 0
                used_labels.add(best_lbl)
            else:
                # Người mới (không khớp session nào active)
                new_lbl = self._assign_new_label(cx)
                if new_lbl:
                    self._sessions[new_lbl] = PersonSession(new_lbl, cx)
                    label_to_bbox[new_lbl]  = bbox
                    used_labels.add(new_lbl)

        # Tăng missing + xóa session cũ sau MISSING_THRESH * 4 frames
        for lbl in list(self._sessions.keys()):
            sess = self._sessions[lbl]
            if lbl not in used_labels:
                sess.missing_frames += 1
                sess._update_absence(False, now)
                if sess.missing_frames > self._MISSING_THRESH * 4:
                    print(f"\n  Xoa session {lbl}")
                    del self._sessions[lbl]
                    self._face_cache.pop(lbl, None)
                    self._face_cache_age.pop(lbl, None)
                    self._wrist_prev_positions.pop(lbl, None)
                    self._wrist_speed_history.pop(lbl, None)
            else:
                sess.missing_frames = 0

        return label_to_bbox

    def _assign_new_label(self, cx: float) -> str | None:
        """Lấy label chưa dùng đầu tiên trong pool."""
        used      = set(self._sessions.keys())
        available = [l for l in self._label_pool if l not in used]
        return available[0] if available else None

    # ── Face round-robin ──────────────────────────────────────────────

    def _run_face_round_robin(self, frame_rgb: np.ndarray,
                               label_to_bbox: dict) -> dict:
        """
        Chạy FaceDetector.detect() trên 1 person crop theo round-robin mỗi frame.
        Các người khác dùng cached gaze_info từ frame trước (tránh lãng phí CPU).

        FaceDetector tự xử lý backend selection (Landmarker → Pose fallback)
        và camera side auto-detect — tracker không cần biết chi tiết.

        Returns: {label → gaze_info dict} (backward compatible với PersonSession)
        """
        active = sorted(label_to_bbox.keys())

        if not active:
            self._age_face_cache()
            return dict(self._face_cache)

        # Round-robin: mỗi frame chạy 1 người
        target = active[self._face_rr_idx % len(active)]
        self._face_rr_idx += 1

        bbox = label_to_bbox.get(target)
        if bbox is not None:
            crop = self._crop_person(frame_rgb, bbox)
            if crop is not None:
                face_result = self.face_detector.detect(crop)
                if face_result.detected:
                    self._face_cache[target]     = face_result.to_gaze_info()
                    self._face_cache_age[target] = 0

        self._age_face_cache()
        return dict(self._face_cache)

    def _crop_person(self, frame_rgb: np.ndarray, bbox: tuple) -> np.ndarray | None:
        """
        Crop person bbox từ frame, mở rộng xuống 30% để include phần thân.
        Trả về None nếu crop quá nhỏ.
        """
        h_frame, w_frame = frame_rgb.shape[:2]
        x1, y1, x2, y2  = [int(v) for v in bbox]
        y2_exp = min(h_frame, int(y2 + (y2 - y1) * 0.3))
        x1 = max(0, x1);  y1 = max(0, y1)
        x2 = min(w_frame, x2);  y2_exp = min(h_frame, y2_exp)
        crop = frame_rgb[y1:y2_exp, x1:x2]
        if crop.shape[0] < Config.MIN_POSE_CROP_H or crop.shape[1] < Config.MIN_POSE_CROP_W:
            return None
        return crop

    def _age_face_cache(self) -> None:
        """Tăng tuổi cache, xóa entry quá cũ (stale)."""
        for lbl in list(self._face_cache_age):
            self._face_cache_age[lbl] = self._face_cache_age.get(lbl, 0) + 1
            if self._face_cache_age[lbl] > Config.MAX_POSE_CACHE_FRAMES:
                self._face_cache.pop(lbl, None)
                self._face_cache_age.pop(lbl, None)

    # ── Hand assignment ───────────────────────────────────────────────

    def _assign_hands_to_persons(self, hand_info: dict,
                                  label_to_bbox: dict) -> dict:
        """
        Gán tay vào người theo nearest X-center của person bbox.
        Mỗi tay → người có center X gần nhất.
        """
        default_hand = {
            "hand_count" : 0,
            "activity"   : "no_hands",
            "status"     : "Không thấy tay",
            "speed"      : 0,
            "positions"  : [],
            "zone"       : "none",
            "phone_score": 0,
        }
        labels       = list(label_to_bbox.keys())
        person_hands = {lbl: dict(default_hand) for lbl in labels}

        if not hand_info.get("positions") or not labels:
            return person_hands

        # Precompute center X của mỗi person bbox
        centers = {
            lbl: (label_to_bbox[lbl][0] + label_to_bbox[lbl][2]) / 2.0
            for lbl in labels
        }

        for hx, hy in hand_info["positions"]:
            # Gán tay cho người có center X gần nhất
            assigned = min(labels, key=lambda l: abs(hx - centers[l]))
            ph = person_hands[assigned]
            ph["hand_count"] += 1
            ph["positions"].append((hx, hy))

        # Copy speed/zone/phone_score cho mỗi người có tay
        for lbl in labels:
            if person_hands[lbl]["hand_count"] > 0:
                person_hands[lbl].update({
                    "activity"   : hand_info.get("activity",    "active_hands"),
                    "status"     : hand_info.get("status",      ""),
                    "speed"      : hand_info.get("speed",       0),
                    "zone"       : hand_info.get("zone",        "none"),
                    "phone_score": hand_info.get("phone_score", 0),
                })

        # ── Recalculate zone relative to person YOLO bbox ──────────────
        # HandDetector classifies zones using full-frame Y coordinates,
        # which fails at side camera angles. Person-relative zones are
        # camera-angle independent because they use the person's own bbox.
        for lbl in labels:
            ph = person_hands[lbl]
            if ph["hand_count"] > 0 and lbl in label_to_bbox:
                bbox = label_to_bbox[lbl]
                bx1, by1, bx2, by2 = bbox
                bbox_h = max(by2 - by1, 1)

                avg_hand_y = np.mean([p[1] for p in ph["positions"]])
                relative_y = (avg_hand_y - by1) / bbox_h

                # Person-relative zones (camera-angle independent):
                #   upper:  < 0.30 (face/head area of person bbox)
                #   middle: 0.30 - 0.50 (torso area)
                #   bottom: > 0.50 (desk/keyboard area — hands on desk)
                # Note: 0.50 instead of 0.65 because from frontal/side cameras,
                # hands on keyboard appear at relative_y ≈ 0.40-0.60 within YOLO bbox.
                if relative_y < 0.30:
                    new_zone = "upper"
                elif relative_y > 0.50:
                    new_zone = "bottom"
                else:
                    new_zone = "middle"

                # Override zone — person-relative is more reliable than full-frame
                ph["zone"] = new_zone

                # Re-classify hand activity based on corrected zone
                speed = ph["speed"]
                ph["activity"], ph["status"] = self._classify_hand_by_zone(
                    new_zone, speed, ph.get("phone_score", 0)
                )

                # ── Hand proximity: phân biệt phone vs typing ở bottom zone ─
                # Typing: 2 tay trải trên bàn phím (spread > 30% bbox width)
                # Phone 2 tay: 2 tay sát nhau (spread < 30% bbox width)
                # Phone 1 tay: chỉ 1 tay detected ở bottom (tay kia cầm phone)
                bbox_w = max(bx2 - bx1, 1)
                if new_zone == "bottom" and ph["hand_count"] >= 2:
                    xs = [p[0] for p in ph["positions"]]
                    spread = abs(max(xs) - min(xs))
                    ph["hand_spread"] = spread / bbox_w  # ratio vs bbox width
                else:
                    ph["hand_spread"] = -1  # unknown (0 or 1 hand)

        return person_hands

    def _classify_hand_by_zone(self, zone: str, speed: float,
                                phone_score: int,
                                pose_wrist: bool = False) -> tuple:
        """Re-classify hand activity based on person-relative zone + speed.

        Args:
            pose_wrist: True when using Pose wrist fallback (noisier data,
                        use higher typing_max threshold to avoid writing misclass)
        """
        if zone == "bottom":
            # Pose wrist has residual noise after ÷2 smoothing; use 1.5× typing_max
            typing_max = int(Config.HAND_SPEED_TYPING_MAX * 1.5) if pose_wrist else Config.HAND_SPEED_TYPING_MAX
            if speed < Config.HAND_SPEED_STILL:
                return "typing_pause", "⌨️ Tay trên bàn phím (nghỉ)"
            elif speed < typing_max:
                return "typing", "⌨️ Đang gõ phím"
            else:
                return "writing", "✍️ Đang viết bài"
        elif zone == "middle":
            if phone_score >= Config.PHONE_SCORE_THRESHOLD:
                return "possible_phone", "📱 Có thể đang cầm điện thoại"
            elif speed < Config.HAND_SPEED_READING:
                return "reading_gesture", "📖 Tay nghỉ / Đang đọc"
            elif speed < Config.HAND_SPEED_GESTURE_MAX:
                return "gesturing", "🖐 Đang cử động tay"
            else:
                return "active_hands", "✋ Tay chuyển động nhiều"
        elif zone == "upper":
            if phone_score >= Config.PHONE_SCORE_UPPER_THRESHOLD:
                return "possible_phone", "📱 Có thể đang cầm điện thoại"
            elif speed < Config.HAND_SPEED_FACE_MAX:
                return "face_touch", "😴 Tay gần mặt / Mệt mỏi?"
            else:
                return "distracted_hands", "⚠️ Tay chuyển động bất thường"
        return "unknown", "❓ Không xác định"

    # ── Overlay drawing ───────────────────────────────────────────────

    def _draw_yolo_objects(self, frame_bgr, yolo_result) -> None:
        """Vẽ bounding boxes màu sắc cho các vật thể YOLO (không phải người)."""
        if yolo_result is None or not self.show_yolo_boxes:
            return
        fh = frame_bgr.shape[0]
        for box in yolo_result.boxes:
            if box.cls_id == 0:   # bỏ qua person
                continue
            color = _OBJECT_COLORS.get(box.cls_name, (180, 180, 180))
            x1, y1 = int(box.x1), int(box.y1)
            x2, y2 = int(box.x2), int(box.y2)
            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 2)
            lbl_txt = f"{box.cls_name} {box.score:.0%}"
            ty = max(y1 - 5, 14)
            cv2.putText(frame_bgr, lbl_txt, (x1, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

    def _draw_person_overlay(self, frame_bgr, label: str, color: tuple,
                              bx1: int, by1: int, bx2: int, by2: int,
                              result: dict):
        """Vẽ bounding box, nhãn, trạng thái + tay cho 1 người."""
        fh = frame_bgr.shape[0]
        # YOLO person bbox
        cv2.rectangle(frame_bgr, (bx1, by1), (bx2, by2), color, 2)

        # Nhãn (A/B/C)
        label_y = max(by1 - 8, 20)
        cv2.putText(frame_bgr, label,
                    (bx1, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # Activity + focus
        activity = result.get("final_activity", "")
        focus    = result.get("focus_score", 0)

        # Hand info
        h_count = result.get("hand_count", 0)
        h_zone  = result.get("hand_zone", "none")
        hand_str = f" | Tay:{h_count} {h_zone}" if h_count > 0 else ""

        # Objects detected
        objects = result.get("detected_objects", [])
        obj_str = " ".join(f"[{o}]" for o in objects) if objects else ""

        status_text = f"{activity} F:{focus}{hand_str}"
        if obj_str:
            status_text += f" {obj_str}"

        text_y = by2 + 18
        if text_y > fh - 5:
            text_y = by1 - 10
        cv2.putText(frame_bgr, status_text,
                    (bx1, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1)

        # Gaze direction (debug, inside box top)
        gaze = result.get("details", {}).get("gaze", "")
        if gaze:
            cv2.putText(frame_bgr, gaze[:24],
                        (bx1, by1 + 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1)

    def _draw_absent_overlay(self, frame_bgr, label: str, color: tuple,
                              sess: PersonSession,
                              bx1: int, by1: int, bx2: int, by2: int):
        """Vẽ overlay vắng mặt cho người không còn trong frame."""
        dur  = sess._absent_duration
        mins = dur // 60;  secs = dur % 60

        overlay = frame_bgr.copy()
        cv2.rectangle(overlay, (bx1, by1), (bx2, by2), color, -1)
        cv2.addWeighted(overlay, 0.08, frame_bgr, 0.92, 0, frame_bgr)
        cv2.rectangle(frame_bgr, (bx1, by1), (bx2, by2), color, 1)

        cv2.putText(frame_bgr, label,
                    (bx1 + 5, max(by1 + 25, 25)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        if dur >= Config.ABSENCE_LONG_THRESHOLD:
            txt   = f"VANG MAT {mins:02d}:{secs:02d}"
            tcol  = (0, 0, 255)
        else:
            txt   = f"ROI CHO {mins:02d}:{secs:02d}"
            tcol  = (0, 165, 255)

        cx = (bx1 + bx2) // 2;  cy = (by1 + by2) // 2
        tw, _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.putText(frame_bgr, txt,
                    (cx - tw[0] // 2, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, tcol, 2)

    def _draw_summary_panel(self, frame_bgr, persons_results: list):
        """Bảng tóm tắt góc trên trái."""
        if not persons_results:
            return frame_bgr

        panel_x = 10;  panel_y = 10
        line_h  = 22;  panel_w = 340
        panel_h = 15 + len(persons_results) * line_h

        overlay = frame_bgr.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                      (panel_x + panel_w, panel_y + panel_h),
                      (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.6, frame_bgr, 0.4, 0, frame_bgr)

        # Nhiệt độ ở góc
        temp_txt = f"CPU:{self._thermal.last_temp:.0f}C" \
                   if self._thermal.last_temp > 0 else ""
        if temp_txt:
            cv2.putText(frame_bgr, temp_txt,
                        (panel_x + panel_w - 70, panel_y + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                        (0, 200, 200) if self._thermal.last_temp < 75 else (0, 100, 255), 1)

        for i, pr in enumerate(persons_results):
            lbl      = pr.get("label", "?")
            activity = pr.get("final_activity", "unknown")
            focus    = pr.get("focus_score", 0)
            color    = _get_color(ord(lbl) - ord("A"))

            sess = self._sessions.get(lbl)
            if sess and sess.missing_frames >= self._MISSING_THRESH:
                dur  = sess._absent_duration
                m    = dur // 60;  s = dur % 60
                text = f"{lbl}: VANG MAT {m:02d}:{s:02d}"
                col  = (0, 0, 255) if dur >= Config.ABSENCE_LONG_THRESHOLD \
                       else (0, 140, 255)
            else:
                objs = pr.get("detected_objects", [])
                obj_tag = f" [{','.join(objs[:2])}]" if objs else ""
                text    = f"{lbl}: {activity:<16} F:{focus:3d}{obj_tag}"
                col     = color

            y = panel_y + 18 + i * line_h
            cv2.putText(frame_bgr, text, (panel_x + 8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)

        return frame_bgr

    # ── Main process ──────────────────────────────────────────────────

    def process(self, frame_rgb: np.ndarray,
                frame_bgr: np.ndarray) -> tuple:
        """
        Xử lý 1 frame: detect người, gaze, tay, objects → overlay.

        Returns: (frame_bgr_with_overlay, persons_results)
        persons_results = list[dict], mỗi dict là kết quả 1 người (có key "label")
        """
        self._frame_count += 1
        h, w = frame_rgb.shape[:2]
        now  = time.time()

        # ── 1. Thermal check (mỗi THERMAL_READ_INTERVAL frame) ──────
        if self._frame_count % Config.THERMAL_READ_INTERVAL == 0:
            extra_skip, extra_sleep = self._thermal.get_throttle()
            self._extra_sleep = extra_sleep
            if self.yolo:
                self.yolo.set_skip(Config.YOLO_SKIP_FRAMES + extra_skip)

        # ── 2. YOLO: submit frame + đọc result cached (non-blocking) ─
        if self.yolo:
            self.yolo.submit_frame(frame_bgr, self._frame_count)
        yolo_result = self.yolo.get_result() if self.yolo else None

        # Cập nhật desk_y EMA từ keyboard/mouse YOLO (thích nghi với góc camera)
        raw_desk = desk_y_from_yolo(yolo_result, h)
        if raw_desk is not None:
            self._desk_y_ema = 0.97 * self._desk_y_ema + 0.03 * raw_desk
        self.hand_detector.set_desk_y(self._desk_y_ema)

        # Vẽ object bboxes (phone/laptop/monitor/keyboard/book) ngay sau YOLO
        self._draw_yolo_objects(frame_bgr, yolo_result)

        # ── 3. Match YOLO person bboxes → session labels ─────────────
        person_bboxes = self._get_person_bboxes()
        label_to_bbox = self._match_yolo_to_sessions(person_bboxes, now)

        # ── 4. Face round-robin (1 person crop / frame) ──────────────
        # FaceDetector: thử Landmarker trước, fallback Pose nếu cần
        pose_gazes = self._run_face_round_robin(frame_rgb, label_to_bbox)

        # ── 5. Hands full frame (~53ms) ──────────────────────────────
        frame_bgr = self.hand_detector.detect(frame_rgb, frame_bgr)
        hand_info = self.hand_detector.result.copy()

        # ── 6. Gán tay → persons by nearest bbox X-center ───────────
        person_hand_infos = self._assign_hands_to_persons(
            hand_info, label_to_bbox
        )

        # ── 7. Per-session update ─────────────────────────────────────
        persons_results: list = []
        sorted_labels = sorted(
            self._sessions.keys(),
            key=lambda l: self._sessions[l].face_cx
        )

        for lbl in sorted_labels:
            sess      = self._sessions[lbl]
            pose_gaze = pose_gazes.get(lbl)   # None nếu không có cache
            h_info    = person_hand_infos.get(lbl, {
                "hand_count": 0, "activity": "no_hands",
                "status": "", "speed": 0,
                "positions": [], "zone": "none", "phone_score": 0,
            })

            # ── Wrist fallback: if no hands from MediaPipe, use Pose wrists ─
            if h_info.get("hand_count", 0) == 0 and pose_gaze is not None:
                wrists = pose_gaze.get("wrist_landmarks", [])
                if wrists:
                    # Fix 1: Map crop-relative coords to full-frame coords
                    bbox = label_to_bbox.get(lbl)
                    if bbox:
                        bx1, by1, bx2, by2 = [int(v) for v in bbox]
                        crop_w = bx2 - bx1
                        crop_h_exp = int((by2 - by1) * 1.3)  # _crop_person expands 30% down
                        wrist_positions = [
                            (int(bx1 + wr["x"] * crop_w),
                             int(by1 + wr["y"] * crop_h_exp))
                            for wr in wrists
                        ]
                    else:
                        wrist_positions = [
                            (int(wr["x"] * w), int(wr["y"] * h)) for wr in wrists
                        ]

                    # Fix 2: Cross-frame wrist speed tracking
                    wrist_speed = 0.0
                    prev_wrists = self._wrist_prev_positions.get(lbl, [])
                    if prev_wrists and wrist_positions:
                        speeds = []
                        for i, pos in enumerate(wrist_positions):
                            if i < len(prev_wrists):
                                dx = pos[0] - prev_wrists[i][0]
                                dy = pos[1] - prev_wrists[i][1]
                                speeds.append((dx**2 + dy**2) ** 0.5)
                        if speeds:
                            wrist_speed = sum(speeds) / len(speeds)
                    self._wrist_prev_positions[lbl] = wrist_positions

                    # Smooth speed over several frames (longer window for Pose noise)
                    # Pose wrist positions are noisier than MediaPipe Hands:
                    # YOLO bbox jitter + Pose prediction instability → artificial speed ~20-30px.
                    # Scale down by 2x to approximate actual hand movement.
                    history = self._wrist_speed_history.setdefault(lbl, [])
                    history.append(wrist_speed)
                    if len(history) > 20:
                        history.pop(0)
                    avg_wrist_speed = (sum(history) / len(history) / 2.0) if history else 0

                    # Fix 3: Pose-based phone detection
                    pose_phone_score = 0
                    high_wrists = []
                    low_wrists = []
                    bbox_for_zone = label_to_bbox.get(lbl)
                    if bbox_for_zone is not None and wrists:
                        bx1z, by1z, bx2z, by2z = [int(v) for v in bbox_for_zone]
                        bbox_hz = max(by2z - by1z, 1)

                        wrist_ys = [p[1] for p in wrist_positions]
                        wrist_rel_ys = [(wy - by1z) / bbox_hz for wy in wrist_ys]

                        high_wrists = [ry for ry in wrist_rel_ys if ry < 0.35]
                        low_wrists = [ry for ry in wrist_rel_ys if ry >= 0.50]

                        if high_wrists:
                            pose_phone_score += 40  # Wrist at face level

                        if len(high_wrists) == 1 and len(low_wrists) >= 1:
                            pose_phone_score += 15  # Asymmetric (one hand up, one down)

                        if avg_wrist_speed < 5:
                            pose_phone_score += 15  # Relatively still (reading phone)

                        # Looking down while wrist elevated → scrolling phone
                        gaze_dir = pose_gaze.get("gaze_direction", "unknown")
                        if gaze_dir == "looking_down" and high_wrists:
                            pose_phone_score += 15

                    # Determine zone from wrist positions relative to EXPANDED bbox.
                    # From side cameras, the wrist on keyboard appears at rel_y ≈ 0.35-0.60
                    # because the desk is at torso level from the camera's perspective.
                    # Combine with gaze: if looking at screen/down + wrist below head → desk activity.
                    _gaze_for_zone = pose_gaze.get("gaze_direction", "unknown") if pose_gaze else "unknown"
                    _desk_gaze = _gaze_for_zone in ("looking_screen", "looking_down")

                    if high_wrists and not low_wrists:
                        wzone = "upper"
                    elif high_wrists:
                        wzone = "middle"
                    elif bbox_for_zone is not None:
                        avg_wy = np.mean([p[1] for p in wrist_positions])
                        rel_y = (avg_wy - by1z) / bbox_hz
                        if rel_y < 0.25:
                            wzone = "upper"
                        elif rel_y > 0.30:
                            # Wrist below head area → desk/keyboard level.
                            # From side cameras, keyboard wrists appear at rel_y ≈ 0.35-0.60
                            # (desk is at torso level from camera perspective).
                            # Phone detection is handled separately by pose_phone_score.
                            wzone = "bottom"
                        else:
                            wzone = "middle"
                    else:
                        wzone = "bottom"

                    h_info = {
                        "hand_count" : len(wrists),
                        "activity"   : "typing_pause",
                        "status"     : "Tay phát hiện qua Pose",
                        "speed"      : avg_wrist_speed,
                        "positions"  : wrist_positions,
                        "zone"       : wzone,
                        "phone_score": pose_phone_score,
                    }
                    h_info["activity"], h_info["status"] = self._classify_hand_by_zone(
                        wzone, avg_wrist_speed, pose_phone_score,
                        pose_wrist=True
                    )

            # Object context từ YOLO (+ hand bboxes để check phone proximity)
            bbox         = label_to_bbox.get(lbl)
            _hand_bboxes = h_info.get("hand_bboxes", []) if h_info else []
            obj_ctx      = build_object_context(
                bbox, yolo_result,
                margin_x_ratio=0.6,
                hand_bboxes=_hand_bboxes,
            ) if bbox else {}
            obj_ctx["desk_y_norm"] = self._desk_y_ema  # dynamic desk level

            result         = sess.update(pose_gaze, h_info, w, h, now, obj_ctx,
                                        yolo_tracked=(lbl in label_to_bbox))
            result["label"]             = lbl
            result["detected_objects"]  = obj_ctx.get("detected_objects", [])
            result["hand_count"]        = h_info.get("hand_count", 0)
            result["hand_zone"]         = h_info.get("zone", "none")
            persons_results.append(result)

            # Vẽ overlay nếu có bbox
            if bbox:
                idx   = ord(lbl) - ord("A")
                color = _get_color(idx)
                bx1, by1, bx2, by2 = [int(v) for v in bbox]
                self._draw_person_overlay(
                    frame_bgr, lbl, color,
                    bx1, by1, bx2, by2, result
                )

        # ── 8. Overlay vắng mặt cho session không có bbox ───────────
        for lbl, sess in self._sessions.items():
            if lbl not in label_to_bbox and \
                    sess.missing_frames >= self._MISSING_THRESH:
                idx   = ord(lbl) - ord("A")
                color = _get_color(idx)
                # Ước tính bbox từ face_cx cũ
                est_w = 120
                cx    = int(sess.face_cx)
                bx1, by1, bx2, by2 = cx - est_w, 0, cx + est_w, h
                self._draw_absent_overlay(
                    frame_bgr, lbl, color, sess,
                    bx1, by1, bx2, by2
                )

        # ── 9. Summary panel ─────────────────────────────────────────
        frame_bgr = self._draw_summary_panel(frame_bgr, persons_results)

        # ── 10. Thermal sleep (nếu nhiệt độ cao) ─────────────────────
        if self._extra_sleep > 0:
            time.sleep(self._extra_sleep)

        return frame_bgr, persons_results

    @property
    def sessions(self):
        return self._sessions

    def stop(self):
        """Dừng YOLO background thread. Gọi khi tắt hệ thống."""
        if self.yolo:
            self.yolo.stop()
