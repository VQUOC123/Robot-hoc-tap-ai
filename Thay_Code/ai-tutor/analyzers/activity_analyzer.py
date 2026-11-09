# analyzers/activity_analyzer.py
# ═══════════════════════════════════════════════════════════════════
#  ActivityAnalyzer — tổng hợp signals → activity + focus score
#
#  Pipeline:
#    1. Pre-process dicts → reclassify keyboard/book
#    2. Build SignalBundle (immutable)
#    3. DrowsinessTracker.update()
#    4. Phone temporal filter  (PhoneClassifier → counter → is_phone)
#    5. Homework visibility    (WritingClassifier score + book/notepaper)
#    6. _determine_raw_activity() — 6 hard intercepts + ConfidenceScorer
#    7. Smoothing (majority vote)
#    8. Phone duration tracking
# ═══════════════════════════════════════════════════════════════════

import time
from collections import Counter, deque

from core.config import Config
from core import constants as C
from analyzers.drowsiness_tracker import DrowsinessTracker, DrowsinessLevel
from analyzers.signals import SignalBundle
from analyzers.confidence_scorer import ConfidenceScorer


class ActivityAnalyzer:
    """
    Tổng hợp kết quả từ tất cả detectors → kết luận cuối cùng.

    Các trạng thái đầu ra (final_activity):
    ┌──────────────────┬──────────────────────────────────────────────────┐
    │ Trạng thái       │ Điều kiện                                        │
    ├──────────────────┼──────────────────────────────────────────────────┤
    │ working_computer │ Nhìn màn hình + gõ phím/chuột                   │
    │ focused_studying │ Nhìn màn hình + gesture/tương tác               │
    │ writing_notes    │ Viết tay + bút/vở (ConfidenceScorer)            │
    │ reading          │ Nhìn xuống/cầm sách (ConfidenceScorer)          │
    │ watching_screen  │ Nhìn màn hình không gõ                          │
    │ using_phone      │ PhoneClassifier + temporal filter (~4s)          │
    │ eating_drinking  │ bottle/cup trong reach + tay chuyển động        │
    │ talking          │ jawOpen + nhìn sang ngang (sustained)            │
    │ playing          │ smiling + tay nhanh + gaze không tập trung      │
    │ distracted       │ Nhìn nơi khác > DISTRACTION_DURATION giây       │
    │ drowsy           │ DrowsinessTracker MODERATE+ signals              │
    │ sleeping         │ DrowsinessTracker SEVERE (gục đầu + nhắm mắt)   │
    │ present          │ Có mặt, không xác định rõ                       │
    ├──────────────────┼──────────────────────────────────────────────────┤
    │ briefly_away     │ Vắng mặt < ABSENCE_LONG_THRESHOLD               │
    │ absent           │ Vắng mặt ≥ ABSENCE_LONG_THRESHOLD               │
    └──────────────────┴──────────────────────────────────────────────────┘
    """

    def __init__(self):
        self._history       = []
        self._session_start = time.time()
        self._last_time     = time.time()
        self._debug_frame   = 0

        # Smoothing
        self._activity_window = deque(maxlen=Config.ACTIVITY_SMOOTH_FRAMES)

        # Thresholds
        self._ABSENCE_SHORT    = Config.ABSENCE_SHORT_THRESHOLD
        self._ABSENCE_LONG     = Config.ABSENCE_LONG_THRESHOLD
        self._DISTRACTION_DUR  = Config.DISTRACTION_DURATION
        self._SLEEPING_LOG_MIN = Config.DROWSY_SLEEPING_LOG_MIN
        self._PHONE_ENABLED    = Config.PHONE_DETECTION_ENABLED

        # Phone temporal filter
        self._PHONE_MIN_SUSTAINED     = Config.PHONE_MIN_SUSTAINED_FRAMES
        self._phone_sustained         = 0
        self._PHONE_DURATION_INTERVAL = Config.PHONE_DURATION_LOG_INTERVAL
        self._phone_start_time        = None
        self._was_phone               = False

        # Talking/playing temporal counters
        self._TALKING_MIN_FRAMES = Config.TALKING_MIN_FRAMES
        self._PLAYING_MIN_FRAMES = Config.PLAYING_MIN_FRAMES
        self._talking_frames     = 0
        self._playing_frames     = 0

        # Writing context tracker: suppress keyboard inference cho N frames sau khi
        # detect hand=writing (tránh oscillation writing_notes ↔ working_computer)
        self._recent_writing_frames = 0

        # Pen sticky buffer: giữ has_pen=True cho N frames sau khi YOLO detect bút.
        # YOLO input size 320px → bút chỉ ~2-3px rộng → detect rất không ổn định.
        # Temporal smoothing: nếu bút thấy gần đây → giả định vẫn còn trong scene.
        self._pen_sticky_frames = 0
        self._PEN_STICKY_MAX = 20   # ~2s @ 10fps

        # Eating temporal filter
        self._EATING_MIN_FRAMES = Config.EATING_MIN_FRAMES
        self._EATING_MIN_SPEED  = Config.EATING_MIN_HAND_SPEED
        self._PHONE_MAX_SPEED   = Config.PHONE_MAX_HAND_SPEED
        self._eating_frames     = 0

        # Homework
        self._HOMEWORK_WRITING_MIN = Config.HOMEWORK_WRITING_MIN_SCORE

        # Workers
        self._drowsy_tracker = DrowsinessTracker()
        self._scorer         = ConfidenceScorer()

        # Focus score weights
        self._S = {
            "sitting"          : Config.SCORE_SITTING,
            "sitting_good"     : Config.SCORE_SITTING_GOOD,
            "standing"         : Config.SCORE_STANDING,
            "gaze_screen"      : Config.SCORE_GAZE_SCREEN,
            "gaze_down"        : Config.SCORE_GAZE_DOWN,
            "gaze_tilt"        : Config.SCORE_GAZE_TILT,
            "gaze_other"       : Config.SCORE_GAZE_OTHER,
            "typing"           : Config.SCORE_HAND_TYPING,
            "writing"          : Config.SCORE_HAND_WRITING,
            "typing_pause"     : Config.SCORE_HAND_TYPING_PAUSE,
            "reading_gesture"  : Config.SCORE_HAND_READING,
            "gesturing"        : Config.SCORE_HAND_GESTURING,
            "no_hands"         : Config.SCORE_HAND_NONE,
            "face_touch"       : Config.SCORE_HAND_FACE,
            "active_hands"     : Config.SCORE_HAND_ACTIVE,
            "default"          : Config.SCORE_HAND_DEFAULT,
            "penalty_phone"    : Config.SCORE_PENALTY_PHONE,
            "penalty_distract" : Config.SCORE_PENALTY_DISTRACTION,
            "penalty_playing"  : Config.SCORE_PENALTY_PLAYING,
            "eating"           : Config.SCORE_EATING,
            "sleeping"         : Config.SCORE_SLEEPING,
        }

        # Public state (đọc từ ngoài)
        self.final_status   = "Đang khởi động..."
        self.final_activity = "starting"
        self.focus_score    = 0

        print("✅ Activity Analyzer sẵn sàng!")

    # ──────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────

    def analyze(self, hand_info: dict, gaze_info: dict, pose_info: dict) -> dict:
        """
        Tổng hợp từ 3 detector dicts → activity + focus + homework signals.

        Args:
            hand_info : kết quả hand_detector  (activity, zone, speed, phone_score, pen_grip, ...)
            gaze_info : kết quả face_detector   (gaze_direction, pitch, expressions, ...)
            pose_info : kết quả YOLO + pose     (has_phone, has_book, person_present, ...)

        Returns:
            dict với: final_activity, final_status, focus_score, details,
                      homework_visible, homework_writing_score, homework_book_detected, ...
        """
        now = time.time()
        dt  = now - self._last_time
        self._last_time = now

        # ── 1. Extract vars NOT in SignalBundle ──────────────────
        gaze_direction  = self._normalize_gaze(gaze_info.get("gaze_direction", "unknown"))
        absent_duration = pose_info.get("absent_duration", 0)
        absence_level   = pose_info.get("absence_level",   "present")
        posture         = pose_info.get("posture",          "unknown")
        face_hidden_s   = gaze_info.get("face_hidden_seconds", 0)
        expressions     = gaze_info.get("expressions", {}) or {}

        # ── 2. Pre-process: infer + reclassify ──────────────────
        hand_activity = hand_info.get("activity", "no_hands")
        hand_zone     = hand_info.get("zone",     "none")
        has_phone_raw = pose_info.get("has_phone",    False)
        has_laptop    = pose_info.get("has_laptop",   False)
        has_monitor   = pose_info.get("has_monitor",  False)
        has_keyboard  = pose_info.get("has_keyboard", False)
        has_mouse     = pose_info.get("has_mouse",    False)
        has_book      = pose_info.get("has_book",     False)
        has_screen    = pose_info.get("has_screen",   False) or has_laptop or has_monitor

        # Writing context: cập nhật counter để nhớ writing motion gần đây.
        # Khi hand=writing → giữ 40 frames (~4s). Giảm dần mỗi frame khác.
        # Mục đích: khi tay dao động writing↔typing speed hoặc MediaPipe mất track,
        # không infer kb từ typing frame và không override sang drowsy/reading.
        if hand_activity == "writing":
            self._recent_writing_frames = 40
        elif self._recent_writing_frames > 0:
            self._recent_writing_frames -= 1

        # Typing → infer keyboard/screen, nhưng CHỈ KHI không có writing context gần đây.
        # Nếu recent_writing_frames > 0: học sinh vừa viết tay → typing là noise, không phải bàn phím thật.
        # YOLO-detected keyboard/screen vẫn giữ nguyên (không bị ghi đè).
        _no_recent_writing = self._recent_writing_frames == 0
        if hand_activity in ("typing", "typing_pause") and not has_phone_raw and _no_recent_writing:
            has_keyboard = True
            has_screen   = True
        if (has_screen and hand_zone == "bottom"
                and hand_activity in ("typing", "typing_pause")
                and not has_phone_raw and not has_book
                and _no_recent_writing):
            has_keyboard = True

        # YOLO keyboard nhầm notebook/vở → reclassify khi tay đang viết
        if (has_keyboard and hand_activity == "writing"
                and not has_screen and not has_mouse):
            has_keyboard = False
            has_book     = True

        # Maintain writing context: khi hand=no_hands nhưng vừa viết gần đây (40-frame window)
        # + tư thế vẫn nhất quán (nhìn xuống / nghiêng đầu, không có bàn phím/màn hình) →
        # giả định tay vẫn trên bàn viết (MediaPipe tạm mất track).
        if (self._recent_writing_frames > 0
                and hand_activity == "no_hands"
                and gaze_direction in ("looking_down", "head_tilt")
                and not has_keyboard
                and not has_screen):
            hand_info     = {**hand_info, "activity": "writing", "zone": "bottom"}
            hand_activity = "writing"
            hand_zone     = "bottom"

        # ── Temporal has_pen smoothing ───────────────────────────────
        # YOLO_INPUT_SIZE=320 → bút chỉ ~2-3px rộng trong ảnh resize → detection bất ổn.
        # Giữ has_pen=True cho _PEN_STICKY_MAX frames sau lần detect gần nhất.
        # Chỉ kích hoạt mạnh khi có writing evidence (tránh false positive).
        _has_pen_raw = pose_info.get("has_pen", False)
        _writing_evidence = (hand_activity in ("writing", "typing")
                             or hand_info.get("pen_grip", False))
        if _has_pen_raw and _writing_evidence:
            self._pen_sticky_frames = self._PEN_STICKY_MAX        # ~2s sticky
        elif _has_pen_raw:
            self._pen_sticky_frames = max(self._pen_sticky_frames, 8)   # ~0.8s
        elif self._pen_sticky_frames > 0:
            self._pen_sticky_frames -= 1

        if self._pen_sticky_frames > 0 and not _has_pen_raw:
            pose_info = {**pose_info, "has_pen": True}

        # ── 3. Build SignalBundle ────────────────────────────────
        signals = SignalBundle.build(
            hand_info, gaze_info, pose_info, gaze_direction,
            has_keyboard=has_keyboard,
            has_book=has_book,
            has_screen=has_screen,
        )

        # ── 4. DrowsinessTracker ─────────────────────────────────
        head_pose_obj = _SimpleHeadPose(
            gaze_info.get("pitch", 0.0),
            gaze_info.get("yaw",   0.0),
            gaze_info.get("roll",  0.0),
        ) if signals.person_present else None

        expr_obj = _SimpleExpressions(
            expressions.get("jaw_open",    0.0),
            expressions.get("eye_blink_l", 0.0),
            expressions.get("eye_blink_r", 0.0),
            expressions.get("talking",     False),
            expressions.get("smiling",     False),
        ) if expressions else None

        drowsy_result = self._drowsy_tracker.update(head_pose_obj, expr_obj, dt)

        # ── 5. Debug log (mỗi 30 frame ≈ 3s @ 10fps) ────────────
        self._debug_frame += 1
        if self._debug_frame % 30 == 0:
            self._debug_log(signals, face_hidden_s, drowsy_result)

        # ── 6. Phone temporal filter ─────────────────────────────
        is_phone = self._PHONE_ENABLED and self._update_phone_counter(signals)

        # ── 7. Focus score ───────────────────────────────────────
        self.focus_score = self._calc_focus_score(signals, posture, is_phone, drowsy_result)

        # ── 8. Homework visibility ───────────────────────────────
        writing_score_val = self._scorer.writing_score(signals)
        homework_book     = signals.objects.has_book or signals.objects.has_notepaper
        homework_visible  = self._calc_homework_visible(signals, writing_score_val)

        # Debug: log khi homework_visible thay đổi hoặc mỗi 10 frame khi True
        if homework_visible and self._debug_frame % 10 == 0:
            h, g, o = signals.hand, signals.gaze, signals.objects
            print(f"[Homework] visible=True writing={writing_score_val} "
                  f"pen={o.has_pen} pen_grip={h.pen_grip} "
                  f"book={o.has_book} notepaper={o.has_notepaper} "
                  f"hand={h.activity} gaze={g.direction}")

        # ── 9. Raw activity ──────────────────────────────────────
        raw_activity, raw_status = self._determine_raw_activity(
            signals, absent_duration, absence_level, is_phone, drowsy_result
        )

        # ── 10. Smoothing: bỏ qua smooth cho vắng mặt / ngủ ────
        if raw_activity in (C.ACTIVITY_ABSENT, C.ACTIVITY_BRIEFLY_AWAY, C.ACTIVITY_SLEEPING):
            activity = raw_activity
            status   = raw_status
            self._activity_window.clear()
        else:
            self._activity_window.append(raw_activity)
            if len(self._activity_window) >= 15:
                activity = Counter(self._activity_window).most_common(1)[0][0]
                status   = (raw_status if activity == raw_activity
                            else self._activity_to_status(activity)[1])
            else:
                activity = raw_activity
                status   = raw_status

        # ── 11. Phone duration tracking ──────────────────────────
        if activity == C.ACTIVITY_USING_PHONE:
            if not self._was_phone:
                self._phone_start_time = now
            duration_str = self._format_phone_duration()
            if duration_str:
                status = C.STATUS_FMT_USING_PHONE.format(duration=duration_str)
        else:
            self._phone_start_time = None
        self._was_phone = (activity == C.ACTIVITY_USING_PHONE)

        self.final_activity = activity
        self.final_status   = status

        self._history.append({"time": now, "activity": activity, "score": self.focus_score})
        if len(self._history) > 30:
            self._history.pop(0)

        return {
            "final_status"          : self.final_status,
            "final_activity"        : self.final_activity,
            "focus_score"           : self.focus_score,
            "details": {
                "hand"       : hand_info.get("status", ""),
                "gaze"       : gaze_info.get("status", ""),
                "pose"       : pose_info.get("status", ""),
                "phone"      : f"📱 Score: {signals.hand.phone_score}%" if is_phone else "",
                "distraction": (f"⚠️ Mất TT: {signals.gaze.distraction_seconds}s"
                                if signals.gaze.distraction_seconds >= 2 else ""),
                "drowsy"     : (f"😴 {','.join(drowsy_result.signals)}"
                                if drowsy_result.signals else ""),
            },
            "session_time"          : int(now - self._session_start),
            "is_phone"              : is_phone,
            "distraction_s"         : signals.gaze.distraction_seconds,
            "absence_level"         : absence_level,
            "detected_objects"      : pose_info.get("detected_objects", []),
            "drowsy_level"          : drowsy_result.level.name,
            "homework_visible"      : homework_visible,
            "homework_writing_score": writing_score_val,
            "homework_book_detected": homework_book,
        }

    def get_stats(self) -> dict:
        """Thống kê phiên học."""
        if not self._history:
            return {}
        activities = [h["activity"] for h in self._history]
        scores     = [h["score"]    for h in self._history]
        count      = Counter(activities)
        total      = len(activities)
        return {
            "avg_focus_score": round(sum(scores) / len(scores), 1),
            "activity_breakdown": {
                act: round(cnt / total * 100, 1)
                for act, cnt in count.most_common(5)
            },
            "session_duration": int(time.time() - self._session_start),
        }

    # ──────────────────────────────────────────────────────────────
    #  Private: core logic
    # ──────────────────────────────────────────────────────────────

    def _determine_raw_activity(self,
                                 signals: SignalBundle,
                                 absent_duration: float,
                                 absence_level: str,
                                 is_phone: bool,
                                 drowsy_result) -> tuple[str, str]:
        """
        Xác định trạng thái hoạt động thô (chưa smooth).

        Steps 1-6: Hard intercepts theo thứ tự ưu tiên.
        Step 7:    ConfidenceScorer cho các trường hợp còn lại.
        """
        h, g, o = signals.hand, signals.gaze, signals.objects

        # ── 1. Vắng mặt ─────────────────────────────────────────
        if not signals.person_present:
            self._reset_temporal_counters()
            return self._classify_absence(absent_duration, absence_level)

        _actively_working = signals.is_actively_working

        # ── 2. Đang ngủ gật (SEVERE) ────────────────────────────
        if (drowsy_result and drowsy_result.is_sleeping
                and drowsy_result.duration >= self._SLEEPING_LOG_MIN
                and not _actively_working):
            return (C.ACTIVITY_SLEEPING,
                    C.STATUS_FMT_SLEEPING.format(seconds=int(drowsy_result.duration)))

        # ── 3. Dùng điện thoại ───────────────────────────────────
        if is_phone:
            return C.ACTIVITY_USING_PHONE, C.STATUS_USING_PHONE

        # ── 4. Mất tập trung kéo dài ────────────────────────────
        _phone_on_side = o.has_phone and g.direction in ("looking_right", "looking_left")
        if (g.distraction_seconds >= self._DISTRACTION_DUR
                and g.direction in ("looking_left", "looking_right", "looking_up")
                and not _phone_on_side
                and not _actively_working):
            direction_label = {"looking_left": "trái",
                               "looking_right": "phải",
                               "looking_up": "trên"}.get(g.direction, "")
            return (C.ACTIVITY_DISTRACTED,
                    C.STATUS_FMT_DISTRACTED.format(
                        seconds=g.distraction_seconds, direction=direction_label))

        # ── 5. Buồn ngủ (MODERATE+) ──────────────────────────────
        # Không override drowsy khi có writing context gần đây (head_tilt khi viết ≠ ngủ)
        if (drowsy_result and drowsy_result.level >= DrowsinessLevel.MODERATE
                and not _actively_working
                and self._recent_writing_frames == 0):
            return C.ACTIVITY_DROWSY, C.STATUS_DROWSY_MODERATE

        # ── 6. Ăn / Uống — temporal filter ──────────────────────
        _eating_object = o.bottle_in_reach or o.cup_in_reach
        _eating_compat = h.activity not in ("typing", "typing_pause", "writing", "reading_gesture")
        if (_eating_object
                and h.hand_count > 0
                and h.zone in ("middle", "upper")
                and _eating_compat
                and self._EATING_MIN_SPEED <= h.speed < self._PHONE_MAX_SPEED
                and g.direction not in ("looking_screen", "looking_left", "looking_right")):
            self._eating_frames += 1
            if self._eating_frames >= self._EATING_MIN_FRAMES:
                return C.ACTIVITY_EATING_DRINKING, C.STATUS_EATING_DRINKING
        else:
            self._eating_frames = max(0, self._eating_frames - 2)

        # ── 7. ConfidenceScorer ──────────────────────────────────
        _exclude = {C.ACTIVITY_USING_PHONE, C.ACTIVITY_DISTRACTED, C.ACTIVITY_EATING_DRINKING}
        scored_activity, _ = self._scorer.classify_excluding(signals, _exclude)

        # Talking/playing dùng temporal counter để tránh flicker
        if scored_activity == C.ACTIVITY_TALKING:
            self._playing_frames = max(0, self._playing_frames - 1)
            self._talking_frames += 1
            if self._talking_frames < self._TALKING_MIN_FRAMES:
                scored_activity = C.ACTIVITY_PRESENT
        elif scored_activity == C.ACTIVITY_PLAYING:
            self._talking_frames = max(0, self._talking_frames - 1)
            self._playing_frames += 1
            if self._playing_frames < self._PLAYING_MIN_FRAMES:
                scored_activity = C.ACTIVITY_PRESENT
        else:
            self._talking_frames = max(0, self._talking_frames - 1)
            self._playing_frames = max(0, self._playing_frames - 1)

        # Drowsy nhẹ khi scorer không thấy activity nào rõ
        if scored_activity == C.ACTIVITY_PRESENT and not _actively_working:
            if drowsy_result and drowsy_result.level >= DrowsinessLevel.MILD:
                return C.ACTIVITY_DROWSY, C.STATUS_DROWSY_MILD
            if g.direction == "head_tilt":
                # head_tilt + có bằng chứng viết = cúi đầu viết bài, không phải ngủ gật
                _writing_evidence = (
                    h.activity in ("typing", "writing")
                    or self._recent_writing_frames > 0
                    or o.has_pen or h.pen_grip or o.has_book or o.has_notepaper
                )
                if not _writing_evidence:
                    return C.ACTIVITY_DROWSY, C.STATUS_DROWSY

        return self._activity_to_status(scored_activity)

    def _update_phone_counter(self, signals: SignalBundle) -> bool:
        """
        Cập nhật temporal filter phone.

        raw_phone từ PhoneClassifier → tích lũy counter.
        is_phone khi counter >= PHONE_MIN_SUSTAINED.

        Returns:
            True nếu đang dùng điện thoại (counter đã đủ ngưỡng).
        """
        raw_phone = self._scorer.phone_score(signals) >= Config.CONFIDENCE_PHONE_THRESHOLD

        if raw_phone:
            # YOLO confirmed (phone + tay) → tích lũy nhanh hơn
            _yolo_confirmed = (signals.objects.has_phone
                               and (signals.objects.phone_in_hand or signals.objects.phone_near_hand))
            increment = 4 if _yolo_confirmed else 2
            self._phone_sustained = min(
                self._phone_sustained + increment, self._PHONE_MIN_SUSTAINED
            )
        else:
            # Typing mạnh hoặc rõ ràng đang viết → clear nhanh
            _strong_typing = (signals.hand.activity == "typing"
                              and signals.hand.speed > 8.0
                              and signals.hand.phone_score == 0)
            _strong_writing = ((signals.hand.activity == "writing"
                                or signals.hand.pen_grip
                                or signals.objects.has_pen)
                               and not signals.objects.phone_in_hand)
            decrement = 3 if (_strong_typing or _strong_writing) else 1
            self._phone_sustained = max(0, self._phone_sustained - decrement)

        return self._phone_sustained >= self._PHONE_MIN_SUSTAINED

    def _calc_focus_score(self, signals: SignalBundle, posture: str,
                           is_phone: bool, drowsy_result) -> int:
        """Tính điểm tập trung 0-100 từ tư thế + gaze + hand + penalties."""
        if not signals.person_present:
            return 0

        S = self._S
        score = 0

        # Tư thế
        if signals.sitting:
            score += S["sitting"]
            if posture == "sitting_good":
                score += S["sitting_good"]
        else:
            score += S["standing"]

        # Hướng nhìn
        score += {
            "looking_screen": S["gaze_screen"],
            "looking_down"  : S["gaze_down"],
            "head_tilt"     : S["gaze_tilt"],
            "looking_up"    : S["gaze_other"],
            "looking_left"  : S["gaze_other"],
            "looking_right" : S["gaze_other"],
        }.get(signals.gaze.direction, 0)

        # Hoạt động tay
        score += {
            "typing"         : S["typing"],
            "writing"        : S["writing"],
            "typing_pause"   : S["typing_pause"],
            "reading_gesture": S["reading_gesture"],
            "gesturing"      : S["gesturing"],
            "no_hands"       : S["no_hands"],
            "face_touch"     : S["face_touch"],
            "active_hands"   : S["active_hands"],
        }.get(signals.hand.activity, S["default"])

        # Penalties
        if is_phone:
            score = max(0, score + S["penalty_phone"])
        if signals.gaze.distraction_seconds >= self._DISTRACTION_DUR:
            score = max(0, score + S["penalty_distract"])
        if drowsy_result and drowsy_result.level >= DrowsinessLevel.MODERATE:
            score = max(0, score + S["penalty_playing"])
        if drowsy_result and drowsy_result.is_sleeping:
            return S["sleeping"]

        return min(100, score)

    def _normalize_gaze(self, gaze_direction: str) -> str:
        """Chuẩn hoá hướng nhìn theo vị trí camera."""
        side = getattr(Config, "CAMERA_SIDE", "front")
        if side == "auto":
            return gaze_direction
        _MAP = {
            "right"      : {"looking_right": "looking_screen"},
            "left"       : {"looking_left" : "looking_screen"},
            "front_right": {"looking_right": "looking_screen"},
            "front_left" : {"looking_left" : "looking_screen"},
        }
        return _MAP.get(side, {}).get(gaze_direction, gaze_direction)

    def _classify_absence(self, absent_duration: float, absence_level: str) -> tuple[str, str]:
        """Phân loại 2 mức vắng mặt: briefly_away vs absent."""
        mins = int(absent_duration) // 60
        secs = int(absent_duration) % 60

        if absence_level == "absent" or absent_duration >= self._ABSENCE_LONG:
            return (C.ACTIVITY_ABSENT,
                    C.STATUS_FMT_ABSENT.format(
                        mins=mins, secs=secs, threshold=self._ABSENCE_LONG // 60))

        if absent_duration >= self._ABSENCE_SHORT:
            return (C.ACTIVITY_BRIEFLY_AWAY,
                    C.STATUS_FMT_BRIEFLY_AWAY_MED.format(
                        mins=mins, secs=secs, threshold=self._ABSENCE_LONG // 60))

        return (C.ACTIVITY_BRIEFLY_AWAY,
                C.STATUS_FMT_BRIEFLY_AWAY_SHORT.format(secs=secs))

    def _activity_to_status(self, activity: str) -> tuple[str, str]:
        """Map activity code → (activity, status_text)."""
        _MAP = {
            C.ACTIVITY_WORKING_COMPUTER : C.STATUS_WORKING_COMPUTER,
            C.ACTIVITY_FOCUSED_STUDYING : C.STATUS_FOCUSED_STUDYING,
            C.ACTIVITY_WRITING_NOTES    : C.STATUS_WRITING_NOTES,
            C.ACTIVITY_READING          : C.STATUS_READING,
            C.ACTIVITY_WATCHING_SCREEN  : C.STATUS_WATCHING_SCREEN,
            C.ACTIVITY_USING_PHONE      : C.STATUS_USING_PHONE,
            C.ACTIVITY_EATING_DRINKING  : C.STATUS_EATING_DRINKING,
            C.ACTIVITY_TALKING          : C.STATUS_TALKING,
            C.ACTIVITY_PLAYING          : C.STATUS_PLAYING,
            C.ACTIVITY_SLEEPING         : C.STATUS_FMT_SLEEPING.format(seconds=0),
            C.ACTIVITY_DISTRACTED       : C.STATUS_FMT_DISTRACTED_SHORT.format(seconds=0),
            C.ACTIVITY_DROWSY           : C.STATUS_DROWSY,
            C.ACTIVITY_PRESENT          : C.STATUS_PRESENT,
        }
        return activity, _MAP.get(activity, C.STATUS_PRESENT)

    def _format_phone_duration(self) -> str:
        """Chuỗi thời gian dùng phone, snap về mốc PHONE_DURATION_LOG_INTERVAL."""
        if self._phone_start_time is None:
            return ""
        total_secs = int(time.time() - self._phone_start_time)
        snapped = (total_secs // self._PHONE_DURATION_INTERVAL) * self._PHONE_DURATION_INTERVAL
        if snapped == 0:
            return ""
        if snapped < 60:
            return f"{snapped} giây"
        mins = snapped // 60
        rem  = snapped % 60
        return f"{mins} phút" if rem == 0 else f"{mins} phút {rem}s"

    def _reset_temporal_counters(self) -> None:
        self._talking_frames = 0
        self._playing_frames = 0
        self._eating_frames  = 0

    def _calc_homework_visible(self, signals: SignalBundle, writing_score: int) -> bool:
        """
        Homework visible = weighted confidence >= 45.

        Thay thế logic cũ (writing_score >= 60 AND has_book/notepaper) vốn
        quá strict vì YOLO notepaper class 233 (Object365) không reliable với
        vở đóng gáy kiểu Việt Nam (train cho tờ giấy rời / loose sheets).

        Nguồn tín hiệu:
          writing_score//2   (0-50) — WritingClassifier đã tổng hợp pen, gaze, motion
          has_book/notepaper  +25   — YOLO xác nhận (reliable khi có)
          pen_grip            +22   — pinch grip = rất reliable, proxy cho bút
          has_pen (YOLO)      +15   — bút trong scene = proxy cho vở
          hand=writing        +12   — motion viết tay
          gaze=looking_down   +8    — nhìn xuống vở/bàn
          gaze=screen+pen/wr  +5    — học online: màn hình + tay vẫn viết

        Scenarios đã verify:
          writing + looking_down + pen=True     → ~67 ✓
          writing + looking_screen + pen=True   → ~45 ✓  (học online)
          typing + pen=True + looking_down      → ~35 ✗  (chỉ gõ phím)
          typing + no pen                       → ~20 ✗
          pen_grip + writing + looking_down     → ~84 ✓
        """
        h, g, o = signals.hand, signals.gaze, signals.objects
        score = 0

        # Core: writing classifier score (đã bao gồm nhiều sub-signals)
        score += writing_score // 2   # range 0-50

        # Physical paper/pen evidence (proxy khi YOLO notepaper fail)
        if o.has_book or o.has_notepaper:
            score += 25   # YOLO xác nhận sách/giấy — reliable
        if h.pen_grip:
            score += 22   # pinch grip rất đặc trưng khi cầm bút
        elif o.has_pen:
            score += 15   # YOLO detect bút trong scene

        # Writing motion bonus
        if h.activity == "writing":
            score += 12   # motion > typing speed ở bottom zone

        # Gaze alignment
        if g.direction == "looking_down":
            score += 8    # nhìn xuống vở/bàn
        elif g.direction == "head_tilt" and h.activity == "writing":
            score += 6    # cúi đầu thấp khi viết = proxy looking_down
        elif g.direction == "looking_screen" and (
                h.pen_grip or o.has_pen or h.activity == "writing"):
            score += 5    # học online: màn hình trước mặt + tay đang viết

        return score >= 45

    def _debug_log(self, signals: SignalBundle, face_hidden_s: float, drowsy_result) -> None:
        h, g, o = signals.hand, signals.gaze, signals.objects
        cam_side = getattr(Config, "CAMERA_SIDE", "?")
        fh = f" face_hidden={face_hidden_s:.0f}s" if face_hidden_s > 0 else ""
        hs = f" spread={h.hand_spread:.2f}" if h.hand_spread >= 0 else ""
        dr = (f" drowsy={drowsy_result.level.name}"
              if drowsy_result.level > DrowsinessLevel.ALERT else "")
        # homework_visible và writing_score để dễ debug
        ws = self._scorer.writing_score(signals)
        hv = self._calc_homework_visible(signals, ws)
        hw = f" HW={'✓' if hv else '✗'}({ws})"
        print(f"[Activity] gaze={g.direction} hand={h.activity} "
              f"zone={h.zone} speed={h.speed:.1f} phone_score={h.phone_score}"
              f"{hs}{fh}{dr}{hw} cam={cam_side} | "
              f"kb={o.has_keyboard} mouse={o.has_mouse} screen={o.has_screen} "
              f"phone={o.has_phone} pen={o.has_pen} pen_grip={h.pen_grip} "
              f"arm={h.arm_on_desk} "
              f"notepaper={o.has_notepaper} bottle={o.has_bottle} cup={o.has_cup}")


# ──────────────────────────────────────────────────────────────────────
#  Lightweight duck-types cho DrowsinessTracker (tránh circular import)
# ──────────────────────────────────────────────────────────────────────

class _SimpleHeadPose:
    __slots__ = ("pitch", "yaw", "roll")

    def __init__(self, pitch: float, yaw: float, roll: float):
        self.pitch = pitch
        self.yaw   = yaw
        self.roll  = roll


class _SimpleExpressions:
    __slots__ = ("jaw_open", "eye_blink_l", "eye_blink_r", "talking", "smiling")

    def __init__(self, jaw_open: float, eye_blink_l: float,
                 eye_blink_r: float, talking: bool, smiling: bool):
        self.jaw_open    = jaw_open
        self.eye_blink_l = eye_blink_l
        self.eye_blink_r = eye_blink_r
        self.talking     = talking
        self.smiling     = smiling
