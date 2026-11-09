# analyzers/confidence_scorer.py
# ═══════════════════════════════════════════════════════════════════
#  ConfidenceScorer — Orchestrator cho tất cả ActivityClassifiers
#
#  Thay thế 20-step binary waterfall bằng weighted confidence scoring:
#    1. Chạy tất cả classifiers song song
#    2. Lấy activity có điểm cao nhất vượt ngưỡng tương ứng
#    3. Tie-breaking: activity có ngưỡng cao hơn ưu tiên hơn
#
#  Không có temporal state — stateless, thread-safe.
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import constants as C
from analyzers.signals import SignalBundle
from analyzers.activity_classifier import (
    WritingClassifier,
    ReadingClassifier,
    ComputerWorkClassifier,
    PhoneClassifier,
    DistractedClassifier,
    TalkingClassifier,
    EatingClassifier,
    PlayingClassifier,
    FocusedStudyingClassifier,
    WatchingScreenClassifier,
)

# Ngưỡng tối thiểu để classify activity này (từ constants, có thể override qua config)
_THRESHOLDS: dict[str, int] = {
    "writing_notes"    : C.CONFIDENCE_WRITING_THRESHOLD,
    "reading"          : C.CONFIDENCE_READING_THRESHOLD,
    "working_computer" : C.CONFIDENCE_COMPUTER_THRESHOLD,
    "using_phone"      : C.CONFIDENCE_PHONE_THRESHOLD,
    "focused_studying" : C.CONFIDENCE_FOCUSED_THRESHOLD,
    "watching_screen"  : C.CONFIDENCE_WATCHING_THRESHOLD,
    "talking"          : C.CONFIDENCE_TALKING_THRESHOLD,
    "eating_drinking"  : C.CONFIDENCE_EATING_THRESHOLD,
    "playing"          : C.CONFIDENCE_PLAYING_THRESHOLD,
    "distracted"       : C.CONFIDENCE_DISTRACTED_THRESHOLD,
}


class ConfidenceScorer:
    """
    Stateless orchestrator: score tất cả activity classifiers và chọn winner.

    Cách dùng:
        scorer = ConfidenceScorer()
        activity, score = scorer.classify(signals)
        writing = scorer.writing_score(signals)
    """

    def __init__(self):
        self._classifiers = [
            WritingClassifier(),
            ReadingClassifier(),
            ComputerWorkClassifier(),
            PhoneClassifier(),
            DistractedClassifier(),
            TalkingClassifier(),
            EatingClassifier(),
            PlayingClassifier(),
            FocusedStudyingClassifier(),
            WatchingScreenClassifier(),
        ]

    def score_all(self, signals: SignalBundle) -> dict[str, int]:
        """
        Chạy tất cả classifiers.

        Returns:
            {activity: score} cho tất cả classifiers.
            Classifiers bị is_possible=False trả về 0.
        """
        return {
            c.activity: (c.score(signals) if c.is_possible(signals) else 0)
            for c in self._classifiers
        }

    def classify(self, signals: SignalBundle) -> tuple[str, int]:
        """
        Chọn activity có điểm cao nhất vượt ngưỡng.

        Returns:
            (activity_code, score) — "present" nếu không có gì vượt ngưỡng.
        """
        scores = self.score_all(signals)
        best_activity = "present"
        best_score    = -1
        for activity, score in scores.items():
            threshold = _THRESHOLDS.get(activity, C.CONFIDENCE_MIN_CLASSIFY)
            if score >= threshold and score > best_score:
                best_activity = activity
                best_score    = score
        return best_activity, max(best_score, 0)

    def classify_excluding(self,
                            signals: SignalBundle,
                            exclude: set[str]) -> tuple[str, int]:
        """
        Classify nhưng bỏ qua một số activities.
        Dùng khi hard intercept đã xác định (vd: đã biết is_phone → loại using_phone).

        Returns:
            (activity_code, score) — "present" nếu không có gì vượt ngưỡng.
        """
        scores = self.score_all(signals)
        best_activity = "present"
        best_score    = -1
        for activity, score in scores.items():
            if activity in exclude:
                continue
            threshold = _THRESHOLDS.get(activity, C.CONFIDENCE_MIN_CLASSIFY)
            if score >= threshold and score > best_score:
                best_activity = activity
                best_score    = score
        return best_activity, max(best_score, 0)

    def writing_score(self, signals: SignalBundle) -> int:
        """Điểm của WritingClassifier cho signals này (dùng cho homework_visible)."""
        for c in self._classifiers:
            if c.activity == "writing_notes":
                return c.score(signals) if c.is_possible(signals) else 0
        return 0

    def phone_score(self, signals: SignalBundle) -> int:
        """Raw score của PhoneClassifier (trước temporal filter)."""
        for c in self._classifiers:
            if c.activity == "using_phone":
                return c.score(signals) if c.is_possible(signals) else 0
        return 0
