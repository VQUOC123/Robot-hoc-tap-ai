# analyzers/signals.py
# ═══════════════════════════════════════════════════════════════════
#  SignalBundle — frozen dataclass kết hợp tất cả tín hiệu từ detectors
#  Dùng bởi ActivityClassifier và ConfidenceScorer.
#
#  Cấu trúc:
#    HandSignals   — từ hand_detector.py
#    GazeSignals   — từ face_detector.py (sau gaze normalization)
#    ObjectSignals — từ yolo_detector.py (qua pose_info / gaze_info)
#    SignalBundle  — container + convenience properties
# ═══════════════════════════════════════════════════════════════════

from dataclasses import dataclass


@dataclass(frozen=True)
class HandSignals:
    """Tín hiệu từ MediaPipe Hands detector."""
    has_hands:   bool
    activity:    str    # "typing", "writing", "no_hands", "reading_gesture", "gesturing", ...
    zone:        str    # "upper", "middle", "bottom", "none"
    speed:       float  # px/frame
    phone_score: int    # 0-100 (từ hand_detector, dựa trên zone/speed/count)
    pen_grip:    bool   # True = pinch ratio thấp → đang cầm bút
    hand_count:  int    # 0, 1, 2
    hand_spread: float  # khoảng cách 2 tay (tỷ lệ), -1 = không rõ / 1 tay
    arm_on_desk: bool = False  # True khi wrist (Pose) ở phần dưới frame → cánh tay trên bàn


@dataclass(frozen=True)
class GazeSignals:
    """Tín hiệu từ FaceDetector (sau gaze normalization)."""
    direction:           str    # "looking_screen", "looking_down", "looking_left",
                                # "looking_right", "looking_up", "head_tilt", "unknown"
    pitch:               float  # độ, âm = cúi đầu
    yaw:                 float  # độ, dương = nhìn trái (từ góc camera phía trước)
    roll:                float  # độ, |roll| lớn = nghiêng đầu
    distraction_seconds: float  # giây nhìn sang nơi khác liên tiếp
    jaw_open:            float  # 0-1, blendshape jawOpen
    talking:             bool   # expressions.talking
    smiling:             bool   # expressions.smiling
    eye_closure:         float  # avg(eye_blink_l, eye_blink_r) 0-1


@dataclass(frozen=True)
class ObjectSignals:
    """Tín hiệu từ YOLO detector (qua pose_info)."""
    has_phone:       bool
    has_keyboard:    bool
    has_mouse:       bool
    has_book:        bool
    has_monitor:     bool
    has_laptop:      bool
    has_bottle:      bool
    has_cup:         bool
    has_pen:         bool
    has_notepaper:   bool
    phone_in_hand:   bool   # phone bbox gần hand bbox (hand_detector spatial check)
    phone_near_hand: bool   # phone bbox overlap / very close to hand bbox
    book_in_hand:    bool   # has_book AND hand zone in middle/upper
    bottle_in_reach: bool   # bottle trong phần trên person bbox (đang cầm/uống)
    cup_in_reach:    bool   # cup trong phần trên person bbox
    has_screen:      bool   # has_monitor OR has_laptop (computed)


@dataclass(frozen=True)
class SignalBundle:
    """
    Container tổng hợp tất cả tín hiệu, bất biến (frozen).

    Convenience properties giúp classifier code ngắn gọn hơn.
    Được build từ detector dicts đã qua reclassification
    (has_keyboard/has_book có thể khác raw dict nếu đã reclassify).
    """
    hand:           HandSignals
    gaze:           GazeSignals
    objects:        ObjectSignals
    person_present: bool
    sitting:        bool

    # ── Convenience properties ────────────────────────────────────

    @property
    def is_looking_down(self) -> bool:
        return self.gaze.direction == "looking_down"

    @property
    def is_looking_at_screen(self) -> bool:
        return self.gaze.direction in ("looking_screen", "looking_forward")

    @property
    def has_writing_tools(self) -> bool:
        """Có bút, giấy, hoặc pen grip → likely đang viết tay."""
        return (self.objects.has_pen
                or self.objects.has_notepaper
                or self.hand.pen_grip)

    @property
    def has_drinking_vessel(self) -> bool:
        return self.objects.has_bottle or self.objects.has_cup

    @property
    def is_actively_working(self) -> bool:
        """Tay đang gõ / viết với tốc độ > 0 → chắc chắn không ngủ."""
        return (self.hand.activity in ("typing", "writing")
                and self.hand.speed > 2.0)

    # ── Factory ───────────────────────────────────────────────────

    @classmethod
    def build(cls,
              hand_info: dict,
              gaze_info: dict,
              pose_info: dict,
              gaze_direction: str,
              *,
              has_keyboard: bool | None = None,
              has_book: bool | None = None,
              has_screen: bool | None = None) -> "SignalBundle":
        """
        Tạo SignalBundle từ detector dicts.

        Args:
            hand_info      : Kết quả từ hand_detector
            gaze_info      : Kết quả từ face_detector
            pose_info      : Kết quả từ YOLO / multi_person_tracker
            gaze_direction : Đã normalize theo camera side
            has_keyboard   : Override nếu đã reclassify (None = dùng pose_info)
            has_book       : Override nếu đã reclassify
            has_screen     : Override nếu đã reclassify
        """
        expressions = gaze_info.get("expressions", {}) or {}
        hand_zone   = hand_info.get("zone", "none")

        # arm_on_desk: cổ tay (từ MediaPipe Pose) ở gần mặt bàn → cánh tay trên bàn.
        # Độc lập với MediaPipe Hands — Pose track wrist ngay cả khi palm-down (viết tay).
        # desk_y_norm: ngưỡng mặt bàn động (từ YOLO keyboard/mouse), thích nghi góc camera.
        # Margin -0.12: cổ tay khi viết thường cao hơn bàn phím 5-12% frame height.
        _desk_y  = pose_info.get("desk_y_norm", 0.52)
        _wrists  = gaze_info.get("wrist_landmarks", [])
        _arm_on_desk = any(
            w.get("y", 0) > (_desk_y - 0.12) and w.get("visibility", 1.0) > 0.10
            for w in _wrists
        )

        # Objects từ pose_info (YOLO results)
        _has_laptop  = pose_info.get("has_laptop",  False)
        _has_monitor = pose_info.get("has_monitor", False)
        _has_book    = has_book   if has_book   is not None else pose_info.get("has_book",    False)
        _has_screen  = has_screen if has_screen is not None else (
            pose_info.get("has_screen", False) or _has_laptop or _has_monitor
        )
        _has_keyboard = has_keyboard if has_keyboard is not None else pose_info.get("has_keyboard", False)

        eye_blink_l = expressions.get("eye_blink_l", 0.0)
        eye_blink_r = expressions.get("eye_blink_r", 0.0)

        hand = HandSignals(
            has_hands   = hand_info.get("hand_count", 0) > 0,
            activity    = hand_info.get("activity",   "no_hands"),
            zone        = hand_zone,
            speed       = float(hand_info.get("speed", 0)),
            phone_score = int(hand_info.get("phone_score", 0)),
            pen_grip    = bool(hand_info.get("pen_grip", False)),
            hand_count  = int(hand_info.get("hand_count", 0)),
            hand_spread = float(hand_info.get("hand_spread", -1)),
            arm_on_desk = _arm_on_desk,
        )

        gaze = GazeSignals(
            direction           = gaze_direction,
            pitch               = float(gaze_info.get("pitch", 0.0)),
            yaw                 = float(gaze_info.get("yaw",   0.0)),
            roll                = float(gaze_info.get("roll",  0.0)),
            distraction_seconds = float(gaze_info.get("distraction_seconds", 0.0)),
            jaw_open            = float(expressions.get("jaw_open",    0.0)),
            talking             = bool(expressions.get("talking",      False)),
            smiling             = bool(expressions.get("smiling",      False)),
            eye_closure         = (eye_blink_l + eye_blink_r) / 2.0,
        )

        _has_bottle = pose_info.get("has_bottle", False)
        _has_cup    = pose_info.get("has_cup",    False)

        objects = ObjectSignals(
            has_phone        = pose_info.get("has_phone",        False),
            has_keyboard     = _has_keyboard,
            has_mouse        = pose_info.get("has_mouse",        False),
            has_book         = _has_book,
            has_monitor      = _has_monitor,
            has_laptop       = _has_laptop,
            has_bottle       = _has_bottle,
            has_cup          = _has_cup,
            has_pen          = pose_info.get("has_pen",          False),
            has_notepaper    = pose_info.get("has_notepaper",    False),
            phone_in_hand    = pose_info.get("phone_in_hand",    False),
            phone_near_hand  = pose_info.get("phone_near_hand",  False),
            book_in_hand     = _has_book and hand_zone in ("middle", "upper"),
            bottle_in_reach  = pose_info.get("bottle_in_reach",  False),
            cup_in_reach     = pose_info.get("cup_in_reach",     False),
            has_screen       = _has_screen,
        )

        return cls(
            hand           = hand,
            gaze           = gaze,
            objects        = objects,
            person_present = pose_info.get("person_present", False),
            sitting        = pose_info.get("sitting",        False),
        )
