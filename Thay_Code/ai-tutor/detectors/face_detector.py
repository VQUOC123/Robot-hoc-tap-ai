# detectors/face_detector.py
"""
Phát hiện khuôn mặt + phân tích hướng nhìn (head pose) + biểu cảm.

Kiến trúc — Strategy Pattern + Facade:
  FaceDetector         — public facade, thử từng backend theo thứ tự ưu tiên
  _FaceBackend (ABC)   — interface chung, bất kỳ backend nào cũng có thể thay thế
  _LandmarkerBackend   — MediaPipe Face Landmarker (frontal ≤ 70°)
                         · head pose từ 4×4 transformation matrix (chính xác)
                         · 52 blendshapes → smile, talking, blink, drowsy
  _PoseBackend         — MediaPipe Pose (fallback, hoạt động ở mọi góc kể cả 90°)
                         · FIXED: pitch dùng body_ref thay vì shoulder_w
                           (tránh mẫu số → 0 khi camera ở góc profile)
  _CameraSideDetector  — tích lũy vote từ ear visibility để auto-detect camera side

SOLID:
  S — Mỗi class chỉ có 1 nhiệm vụ
  O — Thêm backend mới không cần sửa FaceDetector
  L — Mọi backend thay thế được nhau qua interface chung
  I — _FaceBackend chỉ yêu cầu 2 method: detect() + name
  D — FaceDetector phụ thuộc abstraction, không phụ thuộc implementation cụ thể

DRY:
  classify_gaze()  — logic phân loại hướng nhìn ở 1 nơi duy nhất
  Config           — tất cả ngưỡng tập trung tại core/config.py
"""

from __future__ import annotations

import abc
import dataclasses
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import mediapipe as mp
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config


# ══════════════════════════════════════════════════════════════════════════════
#  Ngưỡng biểu cảm (blendshape thresholds) — điều chỉnh theo môi trường thực
# ══════════════════════════════════════════════════════════════════════════════
_BS_TALKING  = 0.20   # jawOpen: > 0.20 → đang nói chuyện / há miệng
_BS_SMILING  = 0.30   # (mouthSmileLeft + mouthSmileRight) / 2
_BS_BLINK    = 0.50   # eyeBlinkLeft / Right: > 0.50 → đang chớp mắt
_BS_DROWSY   = 0.65   # cả 2 mắt nháy cùng lúc hoặc mở thấp → buồn ngủ

# Đường dẫn model Face Landmarker
_PROJECT_ROOT = Path(__file__).parent.parent
_MODEL_DIR    = _PROJECT_ROOT / "models"
_MODEL_FILE   = "face_landmarker.task"
_MODEL_PATH   = _MODEL_DIR / _MODEL_FILE
_MODEL_URL    = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


# ══════════════════════════════════════════════════════════════════════════════
#  Value Objects — immutable, typed output (không có logic)
# ══════════════════════════════════════════════════════════════════════════════

@dataclasses.dataclass(frozen=True)
class HeadPose:
    """Góc đầu (độ). Convention: + = ngửa/trái, - = cúi/phải."""
    pitch:  float   # Cúi/ngửa: + = ngửa lên, - = cúi xuống
    yaw:    float   # Trái/phải: + = quay trái, - = quay phải
    roll:   float   # Nghiêng: |roll| > threshold = nghiêng đầu
    source: str     # "landmarker" hoặc "pose"


@dataclasses.dataclass(frozen=True)
class Expressions:
    """Biểu cảm khuôn mặt. Chỉ có từ LandmarkerBackend (có blendshapes)."""
    talking:  bool = False   # jawOpen > _BS_TALKING
    smiling:  bool = False   # mouthSmile > _BS_SMILING
    drowsy:   bool = False   # cả 2 mắt nhắm nhiều → buồn ngủ
    blink_l:  bool = False   # chớp mắt trái
    blink_r:  bool = False   # chớp mắt phải
    # Raw blendshape values for DrowsinessTracker
    jaw_open:    float = 0.0   # raw jawOpen (0.0-1.0)
    eye_blink_l: float = 0.0   # raw eyeBlinkLeft (0.0-1.0)
    eye_blink_r: float = 0.0   # raw eyeBlinkRight (0.0-1.0)


@dataclasses.dataclass
class FaceResult:
    """Kết quả nhận diện khuôn mặt từ 1 lần detect(). Backward compatible."""
    detected:       bool
    backend:        str                      # "landmarker" | "pose" | "none"
    gaze_direction: str          = "unknown"
    head_pose:      Optional[HeadPose]   = None
    expressions:    Optional[Expressions] = None
    wrist_landmarks: list = dataclasses.field(default_factory=list)

    def to_gaze_info(self) -> dict:
        """
        Chuyển sang dict tương thích với PersonSession.update() và ActivityAnalyzer.
        Giữ đúng format cũ để không phá vỡ code downstream.
        """
        pose = self.head_pose
        expr = self.expressions
        d = {
            "face_detected"      : self.detected,
            "gaze_direction"     : self.gaze_direction,
            "pitch"              : round(pose.pitch, 1) if pose else 0.0,
            "yaw"                : round(pose.yaw,   1) if pose else 0.0,
            "roll"               : round(pose.roll,  1) if pose else 0.0,
            "distraction_seconds": 0,       # PersonSession tự cập nhật
            "gaze_source"        : self.backend,
            "status"             : self._status(),
            # Extra (ActivityAnalyzer sẽ bỏ qua nếu chưa dùng)
            "expressions"        : dataclasses.asdict(expr) if expr else {},
        }
        if self.wrist_landmarks:
            d["wrist_landmarks"] = self.wrist_landmarks
        return d

    def _status(self) -> str:
        expr_tags = []
        if self.expressions:
            if self.expressions.talking: expr_tags.append("nói")
            if self.expressions.smiling: expr_tags.append("cười")
            if self.expressions.drowsy:  expr_tags.append("buồn ngủ")
        suffix = f" [{', '.join(expr_tags)}]" if expr_tags else ""
        src = f"[{self.backend}]"
        return f"{src} {self.gaze_direction}{suffix}" if self.detected else f"{src} Không detect được"


# ══════════════════════════════════════════════════════════════════════════════
#  Pure function — DRY: dùng chung cho cả 2 backend
# ══════════════════════════════════════════════════════════════════════════════

def classify_gaze(pitch: float, yaw: float, roll: float,
                  cam_side: str = "front") -> str:
    """
    Phân loại hướng nhìn từ góc pitch/yaw/roll (độ).
    Ngưỡng đọc từ Config (→ constants.py) để điều chỉnh được từ .env.

    Convention (tương thích ActivityAnalyzer):
      pitch > GAZE_PITCH_UP   → looking_up
      pitch < GAZE_PITCH_DOWN → looking_down
      yaw > YAW_THRESHOLD     → looking_left
      yaw < -YAW_THRESHOLD    → looking_right
      |roll| > ROLL_THRESHOLD → head_tilt
      else                    → looking_screen

    Camera-side compensation (cam_side='left' hoặc 'right'):
      Khi camera đặt bên cạnh, nhìn xuống bàn (vở/điện thoại bên cạnh) tạo ra
      pitch thấp hơn ngưỡng bình thường VÀ yaw lệch phía camera đối diện.
      Combined check: pitch < (GAZE_PITCH_DOWN + BOOST) AND |yaw| < (YAW + SLACK)
      → classify là "looking_down" trước khi yaw check kịp thắng.
    """
    if pitch > Config.GAZE_PITCH_UP:
        return "looking_up"

    # ── Camera-side combined pitch+yaw check ──────────────────────────────
    # Áp dụng khi camera bên trái/phải: nới rộng ngưỡng pitch xuống BOOST°.
    # Chỉ bắt nếu yaw không quá cực đoan (< YAW + SLACK) để tránh nhận nhầm
    # "nhìn tường xa" thành "nhìn xuống bàn".
    if cam_side in ("left", "right"):
        side_pitch_min = Config.GAZE_PITCH_DOWN + Config.GAZE_SIDE_PITCH_BOOST
        yaw_desk_max   = Config.GAZE_YAW_THRESHOLD + Config.GAZE_SIDE_YAW_SLACK
        if pitch < side_pitch_min and abs(yaw) < yaw_desk_max:
            return "looking_down"

    # ── Camera phía trước lệch nhẹ (front_left / front_right) ─────────────
    # Boost nhỏ hơn camera cạnh: pitch -11° thay vì -8°, yaw slack 8° thay vì 15°
    if cam_side in ("front_left", "front_right"):
        front_pitch_min = Config.GAZE_PITCH_DOWN + Config.GAZE_FRONT_PITCH_BOOST
        yaw_desk_max    = Config.GAZE_YAW_THRESHOLD + Config.GAZE_FRONT_YAW_SLACK
        if pitch < front_pitch_min and abs(yaw) < yaw_desk_max:
            return "looking_down"

    if pitch < Config.GAZE_PITCH_DOWN:
        return "looking_down"
    if yaw > Config.GAZE_YAW_THRESHOLD:
        return "looking_left"
    if yaw < -Config.GAZE_YAW_THRESHOLD:
        return "looking_right"
    if abs(roll) > Config.GAZE_ROLL_THRESHOLD:
        return "head_tilt"
    return "looking_screen"


# ══════════════════════════════════════════════════════════════════════════════
#  Camera side auto-detection (Single Responsibility)
# ══════════════════════════════════════════════════════════════════════════════

class _CameraSideDetector:
    """
    Multi-signal camera side auto-detection using 3 independent signals:
      1. Shoulder width ratio   (weight=2, most reliable)
      2. Nose-to-ear X distance (weight=1)
      3. Ear visibility diff    (weight=1, tightened thresholds)

    Tích lũy weighted votes để xác định vị trí camera (front/left/right)
    sau 25-40 frame Pose thành công.

    MediaPipe Pose landmarks used:
      nose(0), left_ear(7), right_ear(8), left_shoulder(11), right_shoulder(12)

    Khi xác định xong → ghi vào Config.CAMERA_SIDE để toàn hệ thống dùng.
    """

    # ── Signal 1: Shoulder width ratio thresholds ─────────────────────────
    # Front view: shoulders appear wide  → ratio ≈ 0.35-0.60
    # Side view:  shoulders foreshortened → ratio ≈ 0.05-0.20
    _SHOULDER_FRONT_MIN = 0.30   # ratio > này → likely front view
    _SHOULDER_SIDE_MAX  = 0.22   # ratio < này → likely side view

    # ── Signal 2: Nose-to-ear X distance ratio thresholds ─────────────────
    # Front view: ears roughly equidistant from nose → ratio > 0.65
    # Side view:  one ear much closer to nose        → ratio < 0.40
    _NOSE_EAR_FRONT_MIN = 0.65   # min(dist)/max(dist) > này → front
    _NOSE_EAR_SIDE_MAX  = 0.40   # min(dist)/max(dist) < này → side

    # ── Signal 3: Ear visibility (tightened from original) ────────────────
    _DIFF_SIDE_THRESH  = 0.15   # |diff| > này → 1 tai rõ hơn rõ rệt (was 0.25)
    _DIFF_FRONT_THRESH = 0.10   # |diff| < này + cả 2 cao → front   (was 0.15)
    _FRONT_MIN_VIS     = 0.65   # ngưỡng tối thiểu "cả 2 tai đều thấy" (was 0.50)

    # ── Voting convergence ────────────────────────────────────────────────
    _VOTES_FULL        = 40     # số weighted-vote tối đa trước khi quyết định
    _VOTES_EARLY_WIN   = 25     # early detect: nếu 1 hướng > 80% sau N vote
    _CONFIDENCE_EARLY  = 80.0   # % confidence để early detect

    # ── Signal weights ────────────────────────────────────────────────────
    _WEIGHT_SHOULDER   = 2      # shoulder ratio is most reliable signal
    _WEIGHT_NOSE_EAR   = 1
    _WEIGHT_EAR_VIS    = 1

    # ── Debug logging ─────────────────────────────────────────────────────
    _DEBUG_LOG_INTERVAL = 10    # log every N frames

    def __init__(self) -> None:
        self._votes: dict[str, int] = {"right": 0, "left": 0, "front": 0}
        self._total_frames: int = 0
        # Nếu đã cấu hình thủ công → bỏ qua auto-detect
        self._done: bool = (Config.CAMERA_SIDE != "auto")

    def vote(self, lms, crop_w: int, crop_h: int) -> None:
        """
        Nhận full Pose landmarks + crop dimensions, chạy 3 signal detectors
        và tích lũy weighted votes.

        Args:
            lms: MediaPipe Pose landmarks list (33 landmarks)
            crop_w: width of the crop in pixels
            crop_h: height of the crop in pixels
        """
        if self._done:
            return

        self._total_frames += 1

        sig_shoulder = self._shoulder_signal(lms, crop_w, crop_h)
        sig_nose_ear = self._nose_ear_signal(lms, crop_w)
        sig_ear_vis  = self._ear_visibility_signal(lms)

        # Accumulate weighted votes from each signal
        if sig_shoulder is not None:
            self._votes[sig_shoulder] += self._WEIGHT_SHOULDER
        if sig_nose_ear is not None:
            self._votes[sig_nose_ear] += self._WEIGHT_NOSE_EAR
        if sig_ear_vis is not None:
            self._votes[sig_ear_vis] += self._WEIGHT_EAR_VIS

        # Debug logging every N frames
        if self._total_frames % self._DEBUG_LOG_INTERVAL == 0:
            print(
                f"[CamSide] frame={self._total_frames} "
                f"votes={dict(self._votes)} "
                f"signals: shoulder={sig_shoulder}, nose_ear={sig_nose_ear}, "
                f"ear_vis={sig_ear_vis}"
            )

        self._check_and_apply()

    def _shoulder_signal(self, lms, crop_w: int, crop_h: int) -> str | None:
        """
        Signal 1: Shoulder width ratio (weight=2).
        Front view → shoulders wide (ratio > 0.30).
        Side view  → shoulders foreshortened (ratio < 0.22).
        For side: nose position relative to shoulder midpoint → LEFT vs RIGHT.
        """
        l_sh = lms[11]  # left shoulder
        r_sh = lms[12]  # right shoulder
        nose = lms[0]

        # Need reasonable visibility for shoulders
        if l_sh.visibility < 0.5 or r_sh.visibility < 0.5:
            return None

        shoulder_px_w = abs(l_sh.x - r_sh.x) * crop_w
        ratio = shoulder_px_w / crop_h if crop_h > 0 else 0

        if ratio >= self._SHOULDER_FRONT_MIN:
            return "front"
        elif ratio <= self._SHOULDER_SIDE_MAX:
            # Determine LEFT vs RIGHT from nose position relative to shoulder midpoint
            mid_sh_x = (l_sh.x + r_sh.x) / 2
            # If nose is to the right of shoulder midpoint → camera is on the right
            # (person is turning left to face rightward camera)
            if nose.x > mid_sh_x:
                return "right"
            else:
                return "left"

        # Ambiguous zone (0.22 < ratio < 0.30) → inconclusive
        return None

    def _nose_ear_signal(self, lms, crop_w: int) -> str | None:
        """
        Signal 2: Nose-to-ear X distance ratio (weight=1).
        Front view → ears roughly equidistant from nose (ratio > 0.65).
        Side view  → one ear much closer to nose (ratio < 0.40).
        The closer ear indicates camera side.
        """
        nose   = lms[0]
        l_ear  = lms[7]
        r_ear  = lms[8]

        # Need reasonable visibility for both ears and nose
        if nose.visibility < 0.5 or l_ear.visibility < 0.3 or r_ear.visibility < 0.3:
            return None

        dist_left  = abs(nose.x - l_ear.x) * crop_w
        dist_right = abs(nose.x - r_ear.x) * crop_w

        max_dist = max(dist_left, dist_right)
        if max_dist < 1.0:  # avoid division by near-zero
            return None

        ratio = min(dist_left, dist_right) / max_dist

        if ratio >= self._NOSE_EAR_FRONT_MIN:
            return "front"
        elif ratio <= self._NOSE_EAR_SIDE_MAX:
            # The closer ear indicates camera side
            if dist_left < dist_right:
                return "left"    # left ear closer to nose → camera on left
            else:
                return "right"   # right ear closer to nose → camera on right

        # Ambiguous zone → inconclusive
        return None

    def _ear_visibility_signal(self, lms) -> str | None:
        """
        Signal 3: Ear visibility differential (weight=1, tightened thresholds).
        Uses the visibility difference between left(7) and right(8) ears.
        """
        l_ear_v = float(lms[7].visibility)
        r_ear_v = float(lms[8].visibility)
        diff = r_ear_v - l_ear_v

        if diff > self._DIFF_SIDE_THRESH:
            return "right"   # Right ear more visible → camera on right
        elif diff < -self._DIFF_SIDE_THRESH:
            return "left"    # Left ear more visible → camera on left
        elif (abs(diff) < self._DIFF_FRONT_THRESH
              and r_ear_v > self._FRONT_MIN_VIS
              and l_ear_v > self._FRONT_MIN_VIS):
            return "front"   # Both ears clearly visible → front

        # Inconclusive
        return None

    # Lean threshold: khi "front" thắng nhưng ≥ N% vote nghiêng 1 bên → front_left/right
    _LEAN_THRESH_PCT = 15.0

    def _check_and_apply(self) -> None:
        total = sum(self._votes.values())
        if total == 0:
            return

        best      = max(self._votes, key=self._votes.get)
        conf      = self._votes[best] / total * 100
        early_ok  = (total >= self._VOTES_EARLY_WIN and conf >= self._CONFIDENCE_EARLY)

        if not early_ok and total < self._VOTES_FULL:
            return

        # Khi "front" thắng nhưng có lean rõ sang 1 bên → front_right / front_left
        # "left" votes (left ear more visible / face turns left) = camera bên phải user
        # "right" votes (right ear more visible / face turns right) = camera bên trái user
        if best == "front":
            left_pct  = self._votes["left"]  / total * 100
            right_pct = self._votes["right"] / total * 100
            if left_pct >= self._LEAN_THRESH_PCT and left_pct > right_pct:
                best = "front_right"
            elif right_pct >= self._LEAN_THRESH_PCT and right_pct > left_pct:
                best = "front_left"

        # Đủ vote hoặc early win → xác nhận và ghi vào Config
        self._done = True
        if best != Config.CAMERA_SIDE:
            print(
                f"\n📷 Auto-detect camera side: '{best}' "
                f"(confidence {conf:.0f}%, votes: {dict(self._votes)}, "
                f"frames: {self._total_frames})"
            )
            Config.CAMERA_SIDE = best
        else:
            print(
                f"\n📷 Camera side confirmed: '{best}' "
                f"({conf:.0f}%, frames: {self._total_frames})"
            )

    def vote_from_yaw(self, yaw: float) -> None:
        """
        Vote camera side từ Landmarker head pose yaw.
        Chỉ vote khi yaw rõ ràng, tránh vote sai cho góc mơ hồ.

        Landmarker chỉ detect được mặt ≤70° → camera không ở 90° side.
        Yaw convention: >0 = quay trái, <0 = quay phải.

        Thresholds (conservative — chỉ vote khi rõ ràng):
          |yaw| < 10°  → front  (weight=2, head rất thẳng)
          yaw > 25°    → left   (weight=1, mặt quay trái rõ)
          yaw < -25°   → right  (weight=1, mặt quay phải rõ)
          10-25°       → no vote (góc mơ hồ, không kết luận được)
        """
        if self._done:
            return

        self._total_frames += 1

        if abs(yaw) < 10:
            self._votes["front"] += 2
        elif yaw > 25:
            self._votes["left"] += 1
        elif yaw < -25:
            self._votes["right"] += 1
        # 10-25°: không vote — góc mơ hồ

        if self._total_frames % self._DEBUG_LOG_INTERVAL == 0:
            print(
                f"[CamSide] frame={self._total_frames} "
                f"votes={dict(self._votes)} "
                f"signal: landmarker_yaw={yaw:.1f}"
            )

        self._check_and_apply()

    @property
    def resolved_side(self) -> str:
        """Camera side hiện tại. Nếu chưa xác định → dùng leader vote hoặc 'front'."""
        if Config.CAMERA_SIDE != "auto":
            return Config.CAMERA_SIDE
        if any(self._votes.values()):
            return max(self._votes, key=self._votes.get)
        return "front"

    @property
    def is_done(self) -> bool:
        return self._done


# ══════════════════════════════════════════════════════════════════════════════
#  Abstract Backend Interface (Interface Segregation + Liskov Substitution)
# ══════════════════════════════════════════════════════════════════════════════

class _FaceBackend(abc.ABC):
    """
    Interface tối giản cho face detector backend.
    Bất kỳ backend nào implement đủ 2 thành phần này đều dùng được với FaceDetector.
    """

    @abc.abstractmethod
    def detect(self, crop_rgb: np.ndarray, cam_side: str) -> FaceResult:
        """
        Nhận diện khuôn mặt trong crop_rgb.
        Luôn trả về FaceResult (detected=False nếu không tìm thấy).
        Không bao giờ raise exception.
        """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Tên backend (dùng trong log và FaceResult.backend)."""


# ══════════════════════════════════════════════════════════════════════════════
#  Backend 1: MediaPipe Face Landmarker (primary)
# ══════════════════════════════════════════════════════════════════════════════

class _LandmarkerBackend(_FaceBackend):
    """
    Sử dụng MediaPipe Face Landmarker Task API (mediapipe >= 0.10).
    · 478 face landmarks + 4×4 transformation matrix → head pose chính xác
    · 52 blendshapes → expressions: smile, talking, blink, drowsy
    · Hoạt động tốt với góc frontal đến ~70° từ phía trước

    Model được tự động tải về lần đầu (~14MB), lưu tại models/face_landmarker.task.
    """

    @property
    def name(self) -> str:
        return "landmarker"

    def __init__(self, cam_detector: '_CameraSideDetector' = None) -> None:
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import (
            FaceLandmarker,
            FaceLandmarkerOptions,
            RunningMode,
        )

        self._cam_detector = cam_detector
        model_path = self._ensure_model()

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.IMAGE,     # Stateless: phù hợp với round-robin
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._detector = FaceLandmarker.create_from_options(options)
        print("✅ Face Landmarker backend sẵn sàng!")

    def detect(self, crop_rgb: np.ndarray, cam_side: str) -> FaceResult:
        try:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=crop_rgb)
            result   = self._detector.detect(mp_image)
        except Exception:
            return FaceResult(detected=False, backend=self.name)

        if not result.face_landmarks:
            return FaceResult(detected=False, backend=self.name)

        head_pose   = self._extract_head_pose(result)
        expressions = self._extract_expressions(result)
        gaze_dir    = classify_gaze(head_pose.pitch, head_pose.yaw, head_pose.roll, cam_side)

        # Vote camera side khi Landmarker thành công
        if self._cam_detector is not None:
            self._cam_detector.vote_from_yaw(head_pose.yaw)

        return FaceResult(
            detected       = True,
            backend        = self.name,
            gaze_direction = gaze_dir,
            head_pose      = head_pose,
            expressions    = expressions,
        )

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _ensure_model() -> str:
        """Tải model về nếu chưa có. Trả về đường dẫn tuyệt đối."""
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)

        if _MODEL_PATH.exists():
            return str(_MODEL_PATH)

        print(f"⬇️  Đang tải {_MODEL_FILE} (~14MB) từ Google Storage...")

        def _progress(count: int, block: int, total: int) -> None:
            pct = min(count * block * 100 // max(total, 1), 100)
            print(f"\r   {pct}%", end="", flush=True)

        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH, reporthook=_progress)
        print(f"\r✅ Tải xong: {_MODEL_PATH}")
        return str(_MODEL_PATH)

    @staticmethod
    def _extract_head_pose(result) -> HeadPose:
        """
        Trích xuất pitch/yaw/roll từ facial_transformation_matrixes[0].
        Ma trận 4×4 chuyển từ face space sang camera space (column-major).

        Convention (tương thích classify_gaze):
          pitch > 0 = ngửa lên   pitch < 0 = cúi xuống
          yaw   > 0 = quay trái  yaw   < 0 = quay phải

        Dùng trực tiếp trục tọa độ mặt (face axes) thay vì Euler decomposition:
          mat[:3, 2] = face Z axis (forward/gaze direction) trong camera space
          mat[:3, 0] = face X axis (right direction) trong camera space
          → pitch = arcsin(fwd_y): fwd_y < 0 khi nhìn xuống (camera Y tăng xuống)
          → yaw   = arctan2(fwd_x, fwd_z): + khi nhìn sang trái
          → roll  = arctan2(-rgt_y, rgt_x)
        """
        mat = np.array(result.facial_transformation_matrixes[0])
        if mat.shape != (4, 4):
            mat = mat.reshape(4, 4)

        fwd = mat[:3, 2]   # face Z axis (forward/gaze direction)
        rgt = mat[:3, 0]   # face X axis (right direction)

        pitch = float(np.degrees(np.arcsin(np.clip(float(fwd[1]), -1.0, 1.0))))
        yaw   = float(np.degrees(np.arctan2(float(fwd[0]), float(fwd[2]))))
        roll  = float(np.degrees(np.arctan2(-float(rgt[1]), float(rgt[0]))))

        return HeadPose(
            pitch  = round(pitch, 1),
            yaw    = round(yaw,   1),
            roll   = round(roll,  1),
            source = "landmarker",
        )

    @staticmethod
    def _extract_expressions(result) -> Expressions:
        """Trích xuất biểu cảm từ 52 blendshape coefficients (0–1)."""
        if not result.face_blendshapes:
            return Expressions()

        bs = {c.category_name: float(c.score) for c in result.face_blendshapes[0]}

        jaw_open   = bs.get("jawOpen",          0.0)
        smile_avg  = (bs.get("mouthSmileLeft",  0.0) + bs.get("mouthSmileRight", 0.0)) / 2
        blink_l    = bs.get("eyeBlinkLeft",     0.0)
        blink_r    = bs.get("eyeBlinkRight",    0.0)
        blink_avg  = (blink_l + blink_r) / 2

        return Expressions(
            talking     = jaw_open  > _BS_TALKING,
            smiling     = smile_avg > _BS_SMILING,
            drowsy      = blink_avg > _BS_DROWSY,
            blink_l     = blink_l   > _BS_BLINK,
            blink_r     = blink_r   > _BS_BLINK,
            jaw_open    = jaw_open,
            eye_blink_l = blink_l,
            eye_blink_r = blink_r,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Backend 2: MediaPipe Pose (fallback, hoạt động ở mọi góc camera)
# ══════════════════════════════════════════════════════════════════════════════

class _PoseBackend(_FaceBackend):
    """
    Sử dụng MediaPipe Pose (nose + shoulder + ear landmarks) để tính head pose.
    Hoạt động tốt với camera đặt bên cạnh (profile view, 60–90°) khi
    Face Landmarker không detect được mặt.

    FIX (so với code cũ):
      pitch_raw = dy / shoulder_w   ← BUG: shoulder_w ≈ 0 ở 90° → pitch = ±infinity
      pitch_raw = dy / body_ref     ← FIX: body_ref = max(shoulder_w, crop_h * 0.25)

    Camera side auto-detect được inject qua _CameraSideDetector (Dependency Injection).
    """

    # Tỷ lệ sàn (floor) cho body_ref tránh chia gần 0 khi profile view
    _BODY_REF_RATIO  = 0.25   # crop_h × 0.25 ≈ natural shoulder width reference
    _EAR_REF_RATIO   = 0.08   # crop_h × 0.08 ≈ natural ear-to-nose distance reference

    @property
    def name(self) -> str:
        return "pose"

    def __init__(self, cam_side_detector: _CameraSideDetector) -> None:
        """
        cam_side_detector: inject để PoseBackend có thể vote camera side
                           mà không cần biết FaceDetector tồn tại.
        """
        self._cam_detector = cam_side_detector
        self._pose = mp.solutions.pose.Pose(
            static_image_mode       = False,
            model_complexity        = 0,     # lite model (~37ms RPi5)
            smooth_landmarks        = True,
            min_detection_confidence= 0.5,
            min_tracking_confidence = 0.45,
        )
        print("✅ Pose fallback backend sẵn sàng!")

    def detect(self, crop_rgb: np.ndarray, cam_side: str) -> FaceResult:
        try:
            result = self._pose.process(crop_rgb)
        except Exception:
            return FaceResult(detected=False, backend=self.name)

        if not result.pose_landmarks:
            return FaceResult(detected=False, backend=self.name)

        lms = result.pose_landmarks.landmark
        h, w = crop_rgb.shape[:2]

        # Vote camera side từ multi-signal detection (auto-detect)
        self._cam_detector.vote(lms, w, h)

        head_pose = self._compute_head_pose(lms, w, h, cam_side)
        gaze_dir  = classify_gaze(head_pose.pitch, head_pose.yaw, head_pose.roll, cam_side)

        # Extract wrist landmarks for hand fallback (LEFT_WRIST=15, RIGHT_WRIST=16)
        wrist_data = []
        for idx in (15, 16):
            lm = lms[idx]
            if lm.visibility > 0.15:   # Low threshold: Pose predicts wrists even at side angles
                wrist_data.append({
                    "x": float(lm.x),
                    "y": float(lm.y),
                    "visibility": float(lm.visibility),
                })

        return FaceResult(
            detected        = True,
            backend         = self.name,
            gaze_direction  = gaze_dir,
            head_pose       = head_pose,
            expressions     = None,   # Pose không có blendshapes
            wrist_landmarks = wrist_data,
        )

    # ── Private helpers ────────────────────────────────────────────────────

    def _compute_head_pose(
        self,
        lms,
        crop_w: int,
        crop_h: int,
        cam_side: str,
    ) -> HeadPose:
        """
        Tính head pose từ nose + shoulder + ear landmarks.

        FIX pitch: dùng body_ref = max(shoulder_w, crop_h × BODY_REF_RATIO)
          Khi camera 90° bên phải: shoulder_w ≈ 30-60px (vai gần chồng nhau)
          → chia cho 30 thổi phồng pitch lên ±100°+ → "looking_down" sai
          → body_ref = max(30, 480×0.25) = max(30, 120) = 120 → pitch hợp lý
        """
        def pt(idx: int) -> np.ndarray:
            lm = lms[idx]
            return np.array([lm.x * crop_w, lm.y * crop_h], dtype=np.float32)

        def vis(idx: int) -> float:
            return float(lms[idx].visibility)

        nose       = pt(0)
        l_ear      = pt(7);  l_ear_v = vis(7)
        r_ear      = pt(8);  r_ear_v = vis(8)
        l_shoulder = pt(11)
        r_shoulder = pt(12)

        shoulder_mid = (l_shoulder + r_shoulder) / 2.0
        shoulder_w   = float(np.linalg.norm(r_shoulder - l_shoulder)) + 1.0

        # ── Pitch (cúi/ngửa) — FIX: dùng body_ref ───────────────────────
        dy       = float(nose[1] - shoulder_mid[1])
        body_ref = max(shoulder_w, float(crop_h) * self._BODY_REF_RATIO)
        pitch_deg = float(np.degrees(np.arctan(dy / body_ref))) * Config.POSE_PITCH_SCALE

        # ── Yaw (trái/phải) — dùng tai nào nhìn thấy ─────────────────────
        yaw_deg = self._compute_yaw(
            nose, l_ear, r_ear,
            l_ear_v, r_ear_v,
            shoulder_w, crop_h, cam_side,
        )

        # ── Roll (nghiêng vai) ─────────────────────────────────────────────
        roll_dy  = float(r_shoulder[1] - l_shoulder[1])
        roll_deg = float(np.degrees(np.arctan2(roll_dy, shoulder_w)))

        return HeadPose(
            pitch  = round(pitch_deg, 1),
            yaw    = round(yaw_deg,   1),
            roll   = round(roll_deg,  1),
            source = "pose",
        )

    def _compute_yaw(
        self,
        nose: np.ndarray,
        l_ear: np.ndarray, r_ear: np.ndarray,
        l_ear_v: float, r_ear_v: float,
        shoulder_w: float, crop_h: int,
        cam_side: str,
    ) -> float:
        """
        Tính góc yaw từ tai nhìn thấy.
        FIX: ear_ref = max(shoulder_w/3, crop_h × EAR_REF_RATIO) tránh chia gần 0.
        """
        ear_ref_floor = float(crop_h) * self._EAR_REF_RATIO

        if l_ear_v > 0.5 and r_ear_v > 0.5:
            # Gần frontal — dùng midpoint của 2 tai
            ear_mid_x = (l_ear[0] + r_ear[0]) / 2.0
            ref       = max(shoulder_w / 2.0, ear_ref_floor) + 1.0
            raw       = (float(nose[0]) - ear_mid_x) / ref
            return float(np.degrees(np.arctan(raw))) * Config.POSE_YAW_SCALE

        if l_ear_v > 0.25:
            # Chỉ thấy tai trái → mặt hướng sang phải
            ear_dx = float(nose[0] - l_ear[0])
            ref    = max(shoulder_w / 3.0, ear_ref_floor) + 1.0
            sign   = 1 if cam_side == "left" else -1
            return sign * float(np.degrees(np.arctan(ear_dx / ref))) * Config.POSE_YAW_SCALE

        if r_ear_v > 0.25:
            # Chỉ thấy tai phải → mặt hướng sang trái
            ear_dx = float(r_ear[0] - nose[0])
            ref    = max(shoulder_w / 3.0, ear_ref_floor) + 1.0
            sign   = -1 if cam_side == "right" else 1
            return sign * float(np.degrees(np.arctan(ear_dx / ref))) * Config.POSE_YAW_SCALE

        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  Public Facade — điểm vào duy nhất cho toàn bộ face detection
# ══════════════════════════════════════════════════════════════════════════════

class FaceDetector:
    """
    Facade quản lý danh sách backends và thực hiện fallback tự động.

    Thứ tự ưu tiên:
      1. _LandmarkerBackend  — nếu khởi tạo thành công VÀ detect được mặt
      2. _PoseBackend        — luôn luôn có mặt như fallback

    Để thêm backend mới (Open/Closed Principle):
      1. Implement _FaceBackend
      2. Thêm vào self._backends trong __init__ theo thứ tự ưu tiên

    Usage:
      detector = FaceDetector()
      result   = detector.detect(crop_rgb)   # → FaceResult
      gaze     = result.to_gaze_info()       # → dict (backward compat)
    """

    def __init__(self) -> None:
        self._cam_detector = _CameraSideDetector()
        self._backends: list[_FaceBackend] = []

        # Backend 1: Face Landmarker (optional — tải model, có thể fail)
        try:
            self._backends.append(_LandmarkerBackend(self._cam_detector))
        except Exception as e:
            print(f"⚠️  Face Landmarker không khả dụng: {e}")
            print("   → Chỉ dùng Pose backend.")

        # Backend 2: Pose (luôn có, fallback cuối cùng)
        self._backends.append(_PoseBackend(self._cam_detector))

        backends_str = " → ".join(b.name for b in self._backends)
        print(f"✅ FaceDetector sẵn sàng! Backends: [{backends_str}]")

    def detect(self, crop_rgb: np.ndarray) -> FaceResult:
        """
        Thử từng backend theo thứ tự ưu tiên.
        Trả về kết quả của backend đầu tiên detect được mặt.
        """
        cam_side = self._cam_detector.resolved_side

        for backend in self._backends:
            result = backend.detect(crop_rgb, cam_side)
            if result.detected:
                return result

        return FaceResult(detected=False, backend="none", gaze_direction="unknown")

    @property
    def cam_side(self) -> str:
        """Camera side hiện tại (sau khi auto-detect hoặc từ config thủ công)."""
        return self._cam_detector.resolved_side
