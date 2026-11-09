# analyzers/drowsiness_tracker.py
"""
Multi-signal temporal drowsiness detection.

Phat hien buon ngu/met moi qua 6 tin hieu ket hop:
1. Eye closure (EAR) — nham mat keo dai
2. Yawning — ngap (jawOpen cao)
3. Blink frequency — chop mat lien tuc
4. Head tilt — nghieng dau keo dai
5. Head nod — gat dau lap lai
6. Head drop — guc dau (-> sleeping)

Duck-typing: head_pose can co .pitch, .yaw, .roll
             expressions can co .eye_blink_l, .eye_blink_r, .jaw_open (float 0-1)
Khong import tu face_detector de tranh circular imports.
"""

import time
import sys
import os
from enum import IntEnum
from dataclasses import dataclass, field
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config


# ═══════════════════════════════════════════════════════════════════════════
#  Value Objects
# ═══════════════════════════════════════════════════════════════════════════

class DrowsinessLevel(IntEnum):
    """Muc do buon ngu, tang dan tu 0 (tinh tao) den 3 (ngu guc)."""
    ALERT    = 0   # Binh thuong
    MILD     = 1   # 1 signal active (ngap 1 lan, chop mat nhieu)
    MODERATE = 2   # 2+ signals hoac 1 signal keo dai
    SEVERE   = 3   # Eye closure + head drop -> sleeping


@dataclass
class DrowsinessResult:
    """Ket qua danh gia buon ngu cho 1 frame."""
    level: DrowsinessLevel = DrowsinessLevel.ALERT
    signals: list = field(default_factory=list)  # active signal names
    duration: float = 0.0      # seconds in current drowsy state
    is_yawning: bool = False
    is_sleeping: bool = False


# ═══════════════════════════════════════════════════════════════════════════
#  DrowsinessTracker
# ═══════════════════════════════════════════════════════════════════════════

class DrowsinessTracker:
    """
    Theo doi va ket hop nhieu tin hieu de phat hien buon ngu.
    Goi update() moi frame (~10fps).

    Su dung duck-typing cho head_pose va expressions:
      - head_pose:    .pitch (float), .yaw (float), .roll (float)
      - expressions:  .eye_blink_l (float 0-1), .eye_blink_r (float 0-1),
                      .jaw_open (float 0-1)
    """

    def __init__(self):
        # ── Thresholds from Config (-> constants.py) ─────────────────────
        self._EYE_CLOSE_THRESH  = Config.DROWSY_EYE_CLOSURE_THRESHOLD   # 0.65
        self._EYE_CLOSE_DUR     = Config.DROWSY_EYE_CLOSURE_DURATION    # 2.0s
        self._YAWN_THRESH       = Config.DROWSY_YAWN_THRESHOLD          # 0.50
        self._YAWN_DUR          = Config.DROWSY_YAWN_DURATION           # 1.5s
        self._BLINK_RATE_HIGH   = Config.DROWSY_BLINK_RATE_HIGH         # 20/min
        self._TILT_DUR          = Config.DROWSY_HEAD_TILT_DURATION      # 3.0s
        self._NOD_PITCH         = Config.DROWSY_HEAD_NOD_PITCH          # -25 deg
        self._NOD_COUNT         = Config.DROWSY_HEAD_NOD_COUNT          # 3
        self._NOD_WINDOW        = Config.DROWSY_HEAD_NOD_WINDOW         # 30s
        self._DROP_PITCH        = Config.DROWSY_HEAD_DROP_PITCH         # -30 deg
        self._DROP_DUR          = Config.DROWSY_HEAD_DROP_DURATION      # 5.0s
        self._ROLL_THRESH       = Config.GAZE_ROLL_THRESHOLD            # 20 deg

        # ── Signal trackers ──────────────────────────────────────────────
        # Eye closure
        self._eye_closed_start = 0.0     # timestamp when eyes started closing

        # Yawning
        self._yawn_start = 0.0
        self._yawn_count = 0             # yawns in recent window
        self._yawn_timestamps = deque(maxlen=10)  # recent yawn timestamps

        # Blink tracking
        self._blink_times = deque(maxlen=60)  # timestamps of recent blinks
        self._prev_blink_l = False
        self._prev_blink_r = False

        # Head tilt
        self._tilt_start = 0.0

        # Head nod (pitch dip detection)
        self._nod_timestamps = deque(maxlen=10)
        self._prev_pitch = 0.0
        self._in_nod_dip = False         # currently in a dip

        # Head drop
        self._drop_start = 0.0

        # Overall drowsy state
        self._drowsy_start = 0.0         # when first became drowsy
        self._current_level = DrowsinessLevel.ALERT

        print("DrowsinessTracker san sang!")

    def update(self, head_pose, expressions, dt: float = 0.1) -> DrowsinessResult:
        """
        Update drowsiness state with new frame data.

        Args:
            head_pose:   object with .pitch, .yaw, .roll (float, degrees) or None
            expressions: object with .eye_blink_l, .eye_blink_r, .jaw_open
                         (float 0-1) or None
            dt: time delta since last frame (seconds)

        Returns:
            DrowsinessResult with current drowsiness assessment
        """
        now = time.time()
        active_signals = []

        # ── Signal 1: Eye Closure ────────────────────────────────────────
        if expressions is not None:
            eye_avg = (expressions.eye_blink_l + expressions.eye_blink_r) / 2.0
            if eye_avg >= self._EYE_CLOSE_THRESH:
                if self._eye_closed_start == 0:
                    self._eye_closed_start = now
                elif now - self._eye_closed_start >= self._EYE_CLOSE_DUR:
                    active_signals.append("eye_closure")
            else:
                self._eye_closed_start = 0.0

        # ── Signal 2: Yawning ────────────────────────────────────────────
        is_yawning = False
        if expressions is not None:
            if expressions.jaw_open >= self._YAWN_THRESH:
                if self._yawn_start == 0:
                    self._yawn_start = now
                elif now - self._yawn_start >= self._YAWN_DUR:
                    is_yawning = True
                    active_signals.append("yawning")
            else:
                # Track completed yawns
                if self._yawn_start > 0 and now - self._yawn_start >= self._YAWN_DUR:
                    self._yawn_timestamps.append(now)
                self._yawn_start = 0.0

        # ── Signal 3: Blink Frequency ────────────────────────────────────
        if expressions is not None:
            # Detect blink events (transition from open -> closed)
            blink_l = expressions.eye_blink_l > 0.50
            blink_r = expressions.eye_blink_r > 0.50
            if (blink_l and not self._prev_blink_l) or \
               (blink_r and not self._prev_blink_r):
                self._blink_times.append(now)
            self._prev_blink_l = blink_l
            self._prev_blink_r = blink_r

            # Calculate blinks per minute (from last 60 seconds)
            cutoff = now - 60.0
            while self._blink_times and self._blink_times[0] < cutoff:
                self._blink_times.popleft()
            blink_rate = len(self._blink_times)  # blinks in last 60s ~ blinks/min
            if blink_rate >= self._BLINK_RATE_HIGH:
                active_signals.append("high_blink_rate")

        # ── Signal 4: Sustained Head Tilt ────────────────────────────────
        if head_pose is not None:
            if abs(head_pose.roll) > self._ROLL_THRESH:
                if self._tilt_start == 0:
                    self._tilt_start = now
                elif now - self._tilt_start >= self._TILT_DUR:
                    active_signals.append("head_tilt")
            else:
                self._tilt_start = 0.0

        # ── Signal 5: Head Nodding (pitch oscillation) ───────────────────
        if head_pose is not None:
            pitch = head_pose.pitch
            if pitch < self._NOD_PITCH and not self._in_nod_dip:
                # Entered a dip
                self._in_nod_dip = True
            elif pitch > self._NOD_PITCH + 10 and self._in_nod_dip:
                # Recovered from dip -> count as a nod
                self._in_nod_dip = False
                self._nod_timestamps.append(now)

            # Count nods in window
            cutoff = now - self._NOD_WINDOW
            while self._nod_timestamps and self._nod_timestamps[0] < cutoff:
                self._nod_timestamps.popleft()
            if len(self._nod_timestamps) >= self._NOD_COUNT:
                active_signals.append("head_nodding")

            self._prev_pitch = pitch

        # ── Signal 6: Head Drop (guc dau) ────────────────────────────────
        is_sleeping = False
        if head_pose is not None:
            if head_pose.pitch < self._DROP_PITCH:
                if self._drop_start == 0:
                    self._drop_start = now
                elif now - self._drop_start >= self._DROP_DUR:
                    active_signals.append("head_drop")
                    is_sleeping = True
            else:
                self._drop_start = 0.0

        # ── Combine signals -> level ─────────────────────────────────────
        # is_sleeping thật: đầu gục (head_drop) VÀ nhắm mắt (eye_closure)
        # head_drop đơn lẻ = đang cúi làm việc → KHÔNG phải ngủ
        is_sleeping = (
            "head_drop" in active_signals
            and "eye_closure" in active_signals
        )

        # Phân loại tín hiệu theo độ tin cậy:
        # - Sustained (cần thời gian kéo dài): eye_closure, head_tilt, head_nodding, head_drop
        # - Transient (có thể thoáng qua): yawning, high_blink_rate
        # head_drop đã cần 8s sustained mới vào active_signals → xếp vào sustained
        sustained = [s for s in active_signals
                     if s in ("eye_closure", "head_tilt", "head_nodding", "head_drop")]
        transient = [s for s in active_signals
                     if s in ("yawning", "high_blink_rate")]

        if is_sleeping:
            level = DrowsinessLevel.SEVERE
        elif len(sustained) >= 1:
            # 1 sustained signal đã đủ MODERATE (kéo dài, đáng tin)
            level = DrowsinessLevel.MODERATE
        elif len(sustained) == 0 and len(transient) >= 2:
            # 2+ transient signals → MILD thôi (không đủ tin để MODERATE)
            level = DrowsinessLevel.MILD
        elif len(transient) == 1:
            # Chỉ 1 transient → MILD
            level = DrowsinessLevel.MILD
        else:
            level = DrowsinessLevel.ALERT

        # Track drowsy duration (bắt đầu từ khi MODERATE+, không phải MILD)
        if level >= DrowsinessLevel.MODERATE:
            if self._drowsy_start == 0:
                self._drowsy_start = now
            duration = now - self._drowsy_start
        else:
            self._drowsy_start = 0.0
            duration = 0.0

        self._current_level = level

        # Sleeping duration: dùng head_drop duration (chính xác hơn _drowsy_start)
        sleeping_duration = (now - self._drop_start) if self._drop_start > 0 else 0.0

        return DrowsinessResult(
            level=level,
            signals=active_signals,
            duration=sleeping_duration if is_sleeping else duration,
            is_yawning=is_yawning,
            is_sleeping=is_sleeping,
        )

    def reset(self):
        """Reset all tracking state."""
        self._eye_closed_start = 0.0
        self._yawn_start = 0.0
        self._yawn_timestamps.clear()
        self._blink_times.clear()
        self._tilt_start = 0.0
        self._nod_timestamps.clear()
        self._in_nod_dip = False
        self._drop_start = 0.0
        self._drowsy_start = 0.0
        self._current_level = DrowsinessLevel.ALERT
