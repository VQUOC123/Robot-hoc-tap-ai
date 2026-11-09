# core/exceptions.py
# Custom exceptions cho AI Tutor system.
# Import từ đây để tránh magic string error handling.


class AITutorError(Exception):
    """Base exception cho toàn bộ hệ thống."""


class DetectorError(AITutorError):
    """Lỗi trong quá trình detect (MediaPipe, YOLO...)."""


class ModelLoadError(DetectorError):
    """Không load được model — file không tồn tại hoặc format sai."""


class InferenceError(DetectorError):
    """Lỗi khi chạy inference trên frame."""


class CameraError(AITutorError):
    """Lỗi camera — không mở được hoặc mất kết nối."""


class ConfigError(AITutorError):
    """Lỗi cấu hình — giá trị không hợp lệ hoặc thiếu key bắt buộc."""
