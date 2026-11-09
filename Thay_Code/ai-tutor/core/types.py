# core/types.py
# Shared types: enums, dataclasses dùng chung giữa nhiều modules.
# Import từ đây để tránh circular imports và tập trung type definitions.
#
# Nguyên tắc:
#   - File này KHÔNG import từ bất kỳ module nào trong project
#   - Tất cả types ở đây đều pure Python (enum, dataclass)
#   - Thêm type mới tại đây, KHÔNG scatter trong các detector/analyzer

from __future__ import annotations

import time
from enum import Enum
from dataclasses import dataclass, field


# ── Activity States ────────────────────────────────────────────────────────────

class ActivityState(str, Enum):
    """
    15 trạng thái hoạt động của học sinh.
    Dùng string value để tương thích với code cũ (so sánh string trực tiếp).
    """
    SLEEPING         = "sleeping"
    USING_PHONE      = "using_phone"
    DISTRACTED       = "distracted"
    DROWSY           = "drowsy"
    EATING_DRINKING  = "eating_drinking"
    WORKING_COMPUTER = "working_computer"
    WRITING_NOTES    = "writing_notes"
    READING          = "reading"
    FOCUSED_STUDYING = "focused_studying"
    WATCHING_SCREEN  = "watching_screen"
    TALKING          = "talking"
    PLAYING          = "playing"
    PRESENT          = "present"
    BRIEFLY_AWAY     = "briefly_away"
    ABSENT           = "absent"

    @classmethod
    def studying_states(cls) -> frozenset[ActivityState]:
        """Các trạng thái học tập — trigger HomeworkService."""
        return frozenset({
            cls.WRITING_NOTES,
            cls.READING,
            cls.FOCUSED_STUDYING,
            cls.WORKING_COMPUTER,
        })

    @classmethod
    def distraction_states(cls) -> frozenset[ActivityState]:
        """Các trạng thái mất tập trung — trigger alert."""
        return frozenset({
            cls.USING_PHONE,
            cls.DISTRACTED,
            cls.SLEEPING,
            cls.PLAYING,
        })

    @classmethod
    def absence_states(cls) -> frozenset[ActivityState]:
        """Các trạng thái vắng mặt."""
        return frozenset({cls.BRIEFLY_AWAY, cls.ABSENT})


# ── Drowsiness Levels ──────────────────────────────────────────────────────────

class DrowsinessLevel(int, Enum):
    """4 mức độ buồn ngủ từ DrowsinessTracker."""
    ALERT    = 0
    MILD     = 1
    MODERATE = 2
    SEVERE   = 3


# ── Homework States ────────────────────────────────────────────────────────────

class HomeworkState(str, Enum):
    """State machine của HomeworkService."""
    IDLE       = "idle"
    REQUESTING = "requesting"   # Đang yêu cầu học sinh giơ bài
    CAPTURED   = "captured"     # Đã chụp ảnh, chờ phân tích
    COOLDOWN   = "cooldown"     # Sau khi phân tích, chờ trước khi hỏi lại


# ── Image Quality ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ImageQuality:
    """Kết quả đánh giá chất lượng ảnh từ image_utils.assess_image_quality()."""
    blur_score:     float   # Laplacian variance — cao hơn = nét hơn
    brightness:     float   # Mean pixel value (0-255)
    contrast:       float   # Stddev pixel value
    coverage_ratio: float   # Diện tích ROI / tổng diện tích frame (0.0-1.0)
    is_acceptable:  bool    # True nếu đạt ngưỡng chất lượng để gửi AI
