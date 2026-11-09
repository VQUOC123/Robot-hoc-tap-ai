# utils/time_utils.py
# Tiện ích thời gian — format duration, elapsed, timestamps.
# Không phụ thuộc vào bất kỳ module nào trong project.

import time


def format_duration(seconds: float) -> str:
    """
    Format số giây thành chuỗi tiếng Việt thân thiện.

    Ví dụ:
        30    → "30 giây"
        90    → "1 phút 30s"
        3600  → "1 giờ"
        3661  → "1 giờ 1 phút"
    """
    s = max(0, int(seconds))
    if s < 60:
        return f"{s} giây"
    minutes, secs = divmod(s, 60)
    if minutes < 60:
        return f"{minutes} phút {secs}s" if secs > 0 else f"{minutes} phút"
    hours, mins = divmod(minutes, 60)
    return f"{hours} giờ {mins} phút" if mins > 0 else f"{hours} giờ"


def monotonic_elapsed(start: float) -> float:
    """Số giây kể từ thời điểm start (dùng time.monotonic())."""
    return time.monotonic() - start


def now_timestamp() -> float:
    """Unix timestamp hiện tại (time.time())."""
    return time.time()


def seconds_to_hms(seconds: float) -> tuple[int, int, int]:
    """Phân tách số giây thành (hours, minutes, seconds)."""
    s = max(0, int(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return h, m, sec
