# utils/image_utils.py
# Tiện ích xử lý ảnh — resize, JPEG encode, đánh giá chất lượng, crop ROI.
#
# Tái sử dụng ở nhiều module: YoloDetector, HandDetector, HomeworkService.
# Tập trung tại đây để tránh duplicate code.

import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import Config
from core.types  import ImageQuality


def resize_for_inference(
    frame: np.ndarray,
    target_size: int,
) -> tuple[np.ndarray, float]:
    """
    Resize frame để tăng tốc inference (giữ aspect ratio).

    Args:
        frame       : BGR hoặc RGB ndarray.
        target_size : Cạnh dài tối đa sau khi resize (pixel).

    Returns:
        (frame_resized, scale)
        scale = target_size / max(h, w) — dùng để map bbox về tọa độ gốc.

    Ví dụ: 1280×720 → target=320 → 320×180, scale=0.25
    """
    h, w = frame.shape[:2]
    scale = target_size / max(h, w)
    if scale >= 1.0:
        return frame, 1.0
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    return resized, scale


def encode_jpeg(frame: np.ndarray, quality: int | None = None) -> bytes:
    """
    Encode frame BGR sang JPEG bytes.

    Args:
        frame   : BGR ndarray.
        quality : JPEG quality (1-100). None → dùng Config.JPEG_QUALITY.

    Raises:
        ValueError nếu encode thất bại.
    """
    q = quality if quality is not None else Config.JPEG_QUALITY
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, q])
    if not ok:
        raise ValueError("JPEG encode thất bại — frame có thể rỗng hoặc sai format")
    return buf.tobytes()


def assess_image_quality(
    frame: np.ndarray,
    roi_box: tuple[int, int, int, int] | None = None,
) -> ImageQuality:
    """
    Đánh giá chất lượng ảnh trước khi gửi AI.

    Args:
        frame   : BGR frame đầy đủ.
        roi_box : (x1, y1, x2, y2) pixel coords của vùng quan tâm (notebook/vở).
                  None → đánh giá toàn frame.

    Returns:
        ImageQuality với các metrics và is_acceptable flag.

    Ngưỡng chấp nhận (từ constants.py group 19):
        blur_score  ≥ IMAGE_QUALITY_MIN_BLUR_SCORE  (Laplacian variance)
        coverage    ≥ IMAGE_QUALITY_MIN_COVERAGE    (tỷ lệ diện tích ROI)
        brightness trong [MIN_BRIGHTNESS, MAX_BRIGHTNESS]
    """
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if roi_box is not None:
        x1, y1, x2, y2 = roi_box
        x1, x2 = max(0, x1), min(w, x2)
        y1, y2 = max(0, y1), min(h, y2)
        region   = gray[y1:y2, x1:x2] if (y2 > y1 and x2 > x1) else gray
        coverage = ((x2 - x1) * (y2 - y1)) / max(1, h * w)
    else:
        region   = gray
        coverage = 1.0

    if region.size == 0:
        region   = gray
        coverage = 1.0

    blur_score = float(cv2.Laplacian(region, cv2.CV_64F).var())
    brightness = float(region.mean())
    contrast   = float(region.std())

    is_acceptable = (
        blur_score >= Config.IMAGE_QUALITY_MIN_BLUR_SCORE
        and coverage   >= Config.IMAGE_QUALITY_MIN_COVERAGE
        and brightness >= Config.IMAGE_QUALITY_MIN_BRIGHTNESS
        and brightness <= Config.IMAGE_QUALITY_MAX_BRIGHTNESS
    )

    return ImageQuality(
        blur_score     = blur_score,
        brightness     = brightness,
        contrast       = contrast,
        coverage_ratio = coverage,
        is_acceptable  = is_acceptable,
    )


def crop_roi(
    frame: np.ndarray,
    roi_ratios: tuple[float, float, float, float],
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """
    Crop frame theo ROI tỷ lệ.

    Args:
        frame       : BGR hoặc RGB ndarray.
        roi_ratios  : (x1, y1, x2, y2) tỷ lệ trong [0.0, 1.0].

    Returns:
        (frame_cropped, pixel_rect) — pixel_rect = (x1, y1, x2, y2).
    """
    h, w = frame.shape[:2]
    x1 = max(0, int(w * roi_ratios[0]))
    y1 = max(0, int(h * roi_ratios[1]))
    x2 = min(w, int(w * roi_ratios[2]))
    y2 = min(h, int(h * roi_ratios[3]))
    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)
