# analyzers/activity_classifier.py
# ═══════════════════════════════════════════════════════════════════
#  Strategy Pattern — Activity Classifiers
#
#  Mỗi ActivityClassifier tính điểm confidence (0-100) cho 1 activity.
#  ConfidenceScorer chạy tất cả classifiers, chọn hoạt động có điểm cao nhất.
#
#  Thiết kế:
#   - Không có side effects (pure scoring)
#   - Không phụ thuộc vào trạng thái trước (temporal state ở ActivityAnalyzer)
#   - Tín hiệu cộng/trừ điểm rõ ràng → dễ debug, tinh chỉnh
#   - Hard blockers trả về 0 → tuyệt đối không classify khi có conflict
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations
from abc import ABC, abstractmethod
from analyzers.signals import SignalBundle


class ActivityClassifier(ABC):
    """Base class cho tất cả activity classifiers."""

    @property
    @abstractmethod
    def activity(self) -> str:
        """Mã hoạt động trả về (phải khớp với ACTIVITY_* trong constants.py)."""
        ...

    @abstractmethod
    def score(self, signals: SignalBundle) -> int:
        """
        Tính điểm confidence (0-100) cho activity này.

        Returns:
            0  = không thể xảy ra với signals này (hard blocked)
            1-49 = tín hiệu yếu, chưa đủ để classify
            50-100 = tín hiệu đủ mạnh (kết hợp với threshold trong scorer)
        """
        ...

    def is_possible(self, signals: SignalBundle) -> bool:
        """
        Kiểm tra nhanh xem activity này có khả năng không.
        Nếu False → score() bị bỏ qua (tiết kiệm tính toán).
        Override nếu cần điều kiện tiên quyết (vd: cần có_screen).
        """
        return True

    @staticmethod
    def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
        return max(lo, min(hi, value))


# ──────────────────────────────────────────────────────────────────
#  1. WritingClassifier
# ──────────────────────────────────────────────────────────────────

class WritingClassifier(ActivityClassifier):
    """
    Phát hiện viết tay / ghi chép.

    Tín hiệu dương: pen_grip (+35), hand_writing (+25), gaze_down (+18),
                    has_pen (+15), has_notepaper (+12), arm_on_desk (+20),
                    has_book (+8), zone_bottom (+7)
    Tín hiệu âm:    gaze_screen (-20), keyboard_only (-15), phone_score>=55 (-25)
    Hard blockers:  phone_in_hand → 0
                    writing + YOLO phone + no pen_grip → 0
    """

    @property
    def activity(self) -> str:
        return "writing_notes"

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects

        # ── Hard blockers ────────────────────────────────────────
        if o.phone_in_hand:
            return 0
        # writing motion + YOLO phone + không có pen grip → likely phone, not pen
        if h.activity == "writing" and o.has_phone and not h.pen_grip:
            return 0
        # keyboard YOLO + high phone score + no pen grip → typing / phone, not writing
        if o.has_keyboard and h.phone_score >= 80 and not h.pen_grip:
            return 0

        s = 0
        # ── Positive signals ─────────────────────────────────────
        if h.pen_grip:
            s += 35   # pinch grip = chắc chắn cầm bút/bút chì
        if h.activity == "writing":
            s += 35   # speed > TYPING_MAX ở bottom zone = viết nhanh (tăng từ 25→35)
        elif h.activity in ("typing", "typing_pause") and h.pen_grip:
            s += 20   # viết chậm (speed < TYPING_MAX) nhưng grip = cầm bút (không phải gõ phím)
        if g.direction == "looking_down":
            s += 18   # nhìn xuống vở/bàn khi viết
        elif g.direction == "head_tilt" and (
                h.activity == "writing" or h.pen_grip or o.has_pen):
            s += 18   # cúi đầu thấp khi viết = tương đương looking_down
        if o.has_pen:
            s += 15   # YOLO detect bút trong scene
        if o.has_notepaper:
            s += 12   # YOLO detect giấy / vở
        if h.arm_on_desk:
            s += 20   # cổ tay (Pose) ở vùng thấp → cánh tay trên bàn (độc lập Hands)
        if o.has_book:
            s += 8    # sách / vở (proxy)
        if h.zone == "bottom":
            s += 7    # tay vùng bàn = đang cầm gì đó trên bàn

        # ── Negative signals ─────────────────────────────────────
        if g.direction == "looking_screen":
            # Nhìn màn hình trong khi có pen/book = chép bài từ màn hình → penalty nhẹ.
            # Không có evidence viết = likely typing/watching → penalty mạnh.
            if h.pen_grip or o.has_pen or o.has_book or o.has_notepaper:
                s -= 5
            else:
                s -= 20
        if o.has_keyboard and not o.has_notepaper and not h.pen_grip and h.activity != "writing":
            s -= 15   # keyboard YOLO không có vở/pen = bàn phím thật (không áp dụng khi tay đang viết)
        if h.phone_score >= 55 and not h.pen_grip:
            s -= 25   # hand detector nghĩ là phone + không có pen grip

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  2. ReadingClassifier
# ──────────────────────────────────────────────────────────────────

class ReadingClassifier(ActivityClassifier):
    """
    Phát hiện đọc sách / tài liệu giấy.

    3 sub-cases:
      A. Sách trên bàn + nhìn xuống + tay nghỉ
      B. Tay cầm sách lên (middle/upper zone)
      C. Inferred: nhìn xuống + tay nghỉ + không có màn hình
    Lấy max của 3 sub-cases.
    """

    @property
    def activity(self) -> str:
        return "reading"

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects
        s1 = self._score_book_table(h, g, o)
        s2 = self._score_book_holding(h, g, o)
        s3 = self._score_inferred(h, g, o)
        return self._clamp(max(s1, s2, s3))

    def _score_book_table(self, h, g, o) -> int:
        """Sách nằm trên bàn, nhìn xuống đọc."""
        if not (o.has_book or o.has_notepaper):
            return 0
        # has_keyboard inferred từ typing → nếu True = đang gõ phím, không đọc
        if o.has_keyboard:
            return 0
        s = 0
        if o.has_book:
            s += 20
        if o.has_notepaper:
            s += 15
        if g.direction == "looking_down":
            s += 28
        if h.speed < 8:
            s += 18   # tay gần như không di chuyển = đang đọc
        if h.activity in ("no_hands", "reading_gesture", "typing_pause"):
            s += 10
        if o.has_pen:
            s -= 15   # bút trong scene → viết tay không phải đọc sách
        if h.arm_on_desk and (h.activity == "writing" or o.has_pen or h.pen_grip):
            s -= 20   # cánh tay trên bàn + bằng chứng viết → không phải đọc sách
        return s

    def _score_book_holding(self, h, g, o) -> int:
        """Tay cầm sách lên (middle/upper zone)."""
        if not o.book_in_hand:
            return 0
        s = 35   # book_in_hand = tín hiệu mạnh nhất
        if h.zone in ("middle", "upper"):
            s += 20
        if g.direction in ("looking_screen", "looking_down"):
            s += 15
        if h.activity in ("reading_gesture", "no_hands", "gesturing"):
            s += 10
        return s

    def _score_inferred(self, h, g, o) -> int:
        """Không có YOLO book nhưng dáng điệu giống đang đọc."""
        if o.has_screen:
            return 0   # có màn hình → watching/working, không phải đọc giấy
        if g.direction != "looking_down":
            return 0
        s = 15
        if h.activity in ("no_hands", "reading_gesture", "typing_pause"):
            s += 18
        if h.speed < 5:
            s += 12   # tay hoàn toàn đứng yên
        return s


# ──────────────────────────────────────────────────────────────────
#  3. ComputerWorkClassifier
# ──────────────────────────────────────────────────────────────────

class ComputerWorkClassifier(ActivityClassifier):
    """
    Phát hiện làm việc trên máy tính (gõ phím, dùng chuột, nhìn màn hình).

    Gate: phải có tín hiệu screen/keyboard/mouse.
    Hard blockers: pen_grip hoặc phone_in_hand → 0.
    """

    @property
    def activity(self) -> str:
        return "working_computer"

    def is_possible(self, signals: SignalBundle) -> bool:
        o = signals.objects
        return o.has_screen or o.has_keyboard or o.has_mouse

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects

        if h.pen_grip or o.phone_in_hand:
            return 0

        s = 0
        # Hardware signals
        if o.has_monitor:
            s += 22
        if o.has_laptop:
            s += 20
        if o.has_keyboard:
            s += 12
        if o.has_mouse:
            s += 10
        # Hand activity
        if h.activity == "typing":
            s += 25
        elif h.activity == "typing_pause":
            s += 12
        if o.has_keyboard and h.zone == "bottom":
            s += 18   # tay đặt đúng vị trí bàn phím
        # Gaze direction
        if g.direction == "looking_screen":
            s += 20
        elif g.direction == "looking_up" and o.has_monitor:
            s += 15   # monitor cao hơn tầm mắt → nhìn hơi lên
        elif g.direction == "looking_down" and o.has_laptop:
            s += 12   # laptop thấp → nhìn hơi xuống

        # Negative: writing evidence (YOLO pen không kèm keyboard = viết tay, không phải gõ phím)
        if o.has_pen and not o.has_keyboard:
            s -= 20   # bút trong scene nhưng không có bàn phím = ghi chép tay
        if o.has_book and not o.has_mouse and not o.has_keyboard:
            s -= 10   # chỉ có sách, không có chuột/bàn phím thật = đọc/viết
        if h.activity == "writing":
            s -= 30   # motion viết tay ≠ gõ bàn phím (tăng penalty từ 20→30)

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  4. PhoneClassifier
# ──────────────────────────────────────────────────────────────────

class PhoneClassifier(ActivityClassifier):
    """
    Phát hiện dùng điện thoại.

    Gate: phone_score >= 30 OR YOLO phone detected.
    Hard blockers: pen_grip, writing+YOLO phone, keyboard+low score,
                   bottle/cup blocking, book in hand, YOLO pen.
    """

    @property
    def activity(self) -> str:
        return "using_phone"

    def is_possible(self, signals: SignalBundle) -> bool:
        h, o = signals.hand, signals.objects
        return h.phone_score >= 30 or o.has_phone

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects

        # ── Hard blockers ────────────────────────────────────────
        if h.pen_grip:
            return 0
        if h.activity == "writing" and o.has_phone:
            return 0   # viết bài không phải dùng phone
        # Keyboard block: chỉ áp dụng khi YOLO KHÔNG thấy phone.
        # Lý do: khi YOLO confirm phone=True, cần cho qua dù có keyboard
        # (phone trên bàn cạnh keyboard, hoặc người dùng phone ở đây gõ)
        if o.has_keyboard and not o.has_phone and h.phone_score < 55:
            return 0
        if (o.has_bottle or o.has_cup) and h.zone in ("middle", "upper") and not o.has_phone:
            return 0   # tay cầm ly/chai, không phải phone
        if o.book_in_hand and h.zone in ("middle", "upper") and not o.has_phone:
            return 0   # tay cầm sách
        if o.has_pen and not o.has_phone:
            return 0   # YOLO thấy bút → không phải phone

        s = 0
        # ── Positive: spatial confirmation ───────────────────────
        if o.phone_in_hand:
            s += 45   # phone trong vùng người (threshold 75% person height)
        if o.phone_near_hand:
            s += 25   # phone bbox gần hand bbox từ MediaPipe
        if o.has_phone:
            s += 15   # YOLO detect phone trong frame

        # ── Positive: hand zone + YOLO phone ────────────────────
        # Ngồi nhìn xuống dùng phone: hand ở bottom/middle, cùng vùng phone
        if o.has_phone and h.zone in ("bottom", "middle"):
            s += 15

        # ── Positive: phone_score từ hand_detector ───────────────
        if h.phone_score >= 75:
            s += 30
        elif h.phone_score >= 55:
            s += 20
        elif h.phone_score >= 40:
            s += 10

        # ── Positive: gaze signals ───────────────────────────────
        if g.direction in ("looking_down", "head_tilt"):
            s += 10   # nhìn xuống phone trên bàn / nghiêng đầu xem phone
        elif g.direction == "looking_screen" and h.zone in ("middle", "upper"):
            s += 5    # phone ngang tầm mắt

        # ── Negative: computer work (chỉ khi KHÔNG có YOLO phone) ────────────
        # Scroll phone = motion giống gõ phím → hand detector nhầm "typing"
        # Nếu YOLO đã confirm phone → không penalty thêm
        if h.activity in ("typing", "typing_pause") and o.has_screen and not o.has_phone:
            s -= 30

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  5. DistractedClassifier
# ──────────────────────────────────────────────────────────────────

class DistractedClassifier(ActivityClassifier):
    """
    Phát hiện mất tập trung (nhìn sang trái/phải/lên kéo dài).

    Gate: gaze phải là looking_left/right/up.
    Negative: typing/writing mạnh → không thể mất tập trung.
    """

    @property
    def activity(self) -> str:
        return "distracted"

    def is_possible(self, signals: SignalBundle) -> bool:
        return signals.gaze.direction in ("looking_left", "looking_right", "looking_up")

    def score(self, signals: SignalBundle) -> int:
        h, g = signals.hand, signals.gaze

        if g.direction not in ("looking_left", "looking_right", "looking_up"):
            return 0

        s = 20   # base: đang nhìn sang nơi khác
        ds = g.distraction_seconds
        if ds >= 10:
            s += 30
        elif ds >= 5:
            s += 20
        elif ds >= 2:
            s += 10

        # Negative: đang tích cực làm việc
        if h.activity in ("typing", "writing"):
            s -= 35

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  6. TalkingClassifier
# ──────────────────────────────────────────────────────────────────

class TalkingClassifier(ActivityClassifier):
    """
    Phát hiện đang nói chuyện (jawOpen lớn, looking_left/right).
    """

    @property
    def activity(self) -> str:
        return "talking"

    def score(self, signals: SignalBundle) -> int:
        h, g = signals.hand, signals.gaze

        s = 0
        if g.jaw_open > 0.35:
            s += 30
        elif g.jaw_open > 0.25:
            s += 20
        if g.talking:
            s += 20
        if g.direction in ("looking_left", "looking_right"):
            s += 20   # nhìn sang người khác khi nói
        if h.activity not in ("typing", "typing_pause", "writing"):
            s += 10   # không đang gõ / viết = tay tự do khi nói chuyện

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  7. EatingClassifier
# ──────────────────────────────────────────────────────────────────

class EatingClassifier(ActivityClassifier):
    """
    Phát hiện ăn uống.

    Gate: phải có bottle/cup trong frame.
    Negative: đang gõ phím / viết → không ăn uống.
    """

    @property
    def activity(self) -> str:
        return "eating_drinking"

    def is_possible(self, signals: SignalBundle) -> bool:
        return signals.has_drinking_vessel

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects

        s = 0
        if o.bottle_in_reach or o.cup_in_reach:
            s += 25   # bottle/cup trong phần trên person bbox → đang cầm
        if h.zone in ("middle", "upper"):
            s += 20   # tay nâng lên cao → đưa ly lên miệng
        if h.hand_count > 0:
            s += 10   # phải thấy tay
        if 3 <= h.speed < 20:
            s += 15   # tay di chuyển nhẹ (không đứng yên, không quá nhanh)

        # Negative
        if h.activity in ("typing", "typing_pause", "writing", "reading_gesture"):
            s -= 30
        if g.direction in ("looking_left", "looking_right"):
            s -= 10   # nhìn ngang = nói chuyện, không ăn uống

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  8. PlayingClassifier
# ──────────────────────────────────────────────────────────────────

class PlayingClassifier(ActivityClassifier):
    """
    Phát hiện chơi đùa (cười + tay cử động nhanh + gaze không tập trung).
    """

    @property
    def activity(self) -> str:
        return "playing"

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects

        # Hard blockers: tay đang viết → không thể chơi đùa
        if h.activity == "writing":
            return 0
        # Có bút / pen_grip → đang ghi chép, không phải chơi đùa
        if h.pen_grip or o.has_pen:
            return 0

        s = 0
        if g.smiling:
            s += 25
        if h.speed > 15:
            s += 25   # tay cử động rất nhanh

        # head_tilt + writing context = cúi đầu làm việc, không phải gaze lạc trôi
        _writing_context = (
            h.activity in ("typing", "writing")
            or o.has_pen or h.pen_grip or o.has_book or o.has_notepaper
        )
        if g.direction not in ("looking_screen", "looking_down"):
            if not (g.direction == "head_tilt" and _writing_context):
                s += 15   # không tập trung vào công việc

        if h.activity not in ("typing", "writing"):
            s += 10

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  9. FocusedStudyingClassifier
# ──────────────────────────────────────────────────────────────────

class FocusedStudyingClassifier(ActivityClassifier):
    """
    Tập trung học tập (nhìn màn hình + gesture/typing + có screen).

    Gate: phải có screen.
    """

    @property
    def activity(self) -> str:
        return "focused_studying"

    def is_possible(self, signals: SignalBundle) -> bool:
        return signals.objects.has_screen

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects

        s = 0
        if g.direction == "looking_screen":
            s += 30
        if h.activity == "typing":
            s += 25
        if h.activity == "gesturing":
            s += 20   # giải thích / trình bày
        if o.has_monitor:
            s += 15
        if o.has_laptop:
            s += 10

        return self._clamp(s)


# ──────────────────────────────────────────────────────────────────
#  10. WatchingScreenClassifier
# ──────────────────────────────────────────────────────────────────

class WatchingScreenClassifier(ActivityClassifier):
    """
    Nhìn màn hình không gõ / đang suy nghĩ.

    Gate: phải có screen.
    Negative: typing/writing → working_computer, không phải watching.
    """

    @property
    def activity(self) -> str:
        return "watching_screen"

    def is_possible(self, signals: SignalBundle) -> bool:
        return signals.objects.has_screen

    def score(self, signals: SignalBundle) -> int:
        h, g, o = signals.hand, signals.gaze, signals.objects

        s = 0
        if g.direction == "looking_screen":
            s += 35
        if h.activity in ("no_hands", "reading_gesture", "typing_pause"):
            s += 20
        if o.has_monitor or o.has_laptop:
            s += 15

        # Negative: đang tích cực gõ/viết
        if h.activity == "typing":
            s -= 20
        if h.activity == "writing":
            s -= 30

        return self._clamp(s)
