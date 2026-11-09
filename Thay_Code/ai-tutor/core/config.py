# core/config.py
# Quản lý cấu hình tập trung — đọc từ .env, fallback về constants.py
#
# Thứ tự ưu tiên:
#   .env (override) > constants.py (default)
#
# Để thay đổi một giá trị:
#   - Nhanh/tạm thời: sửa trong constants.py
#   - Theo môi trường (production/dev): thêm vào .env
import os
from dotenv import load_dotenv
import core.constants as C

load_dotenv()


def _bool(key: str, default: bool) -> bool:
    """Đọc biến môi trường boolean (true/false, không phân biệt hoa thường)."""
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() == 'true'


class Config:
    # ── Camera ──────────────────────────────────────────────────────
    CAMERA_WIDTH    = int(os.getenv('CAMERA_WIDTH',    C.CAMERA_WIDTH))
    CAMERA_HEIGHT   = int(os.getenv('CAMERA_HEIGHT',   C.CAMERA_HEIGHT))
    CAMERA_FPS      = int(os.getenv('CAMERA_FPS',      C.CAMERA_FPS))
    SNAPSHOT_WIDTH  = int(os.getenv('SNAPSHOT_WIDTH',  C.SNAPSHOT_WIDTH))
    SNAPSHOT_HEIGHT = int(os.getenv('SNAPSHOT_HEIGHT', C.SNAPSHOT_HEIGHT))
    DETECTION_FPS   = int(os.getenv('DETECTION_FPS', C.DETECTION_FPS))
    STREAM_FPS      = int(os.getenv('STREAM_FPS',    C.STREAM_FPS))

    # ── Stream ──────────────────────────────────────────────────────
    STREAM_HOST     = os.getenv('STREAM_HOST', C.STREAM_HOST)
    STREAM_PORT     = int(os.getenv('STREAM_PORT', C.STREAM_PORT))

    # ── Motion Detector ─────────────────────────────────────────────
    MOTION_THRESHOLD    = int(os.getenv('MOTION_THRESHOLD', C.MOTION_THRESHOLD))
    MOTION_MIN_AREA     = int(os.getenv('MOTION_MIN_AREA',  C.MOTION_MIN_AREA))

    # ── Absence Detection ───────────────────────────────────────────
    # Số frame liên tiếp không detect người trước khi bắt đầu tính vắng
    ABSENCE_BUFFER_FRAMES   = int(os.getenv(
        'ABSENCE_BUFFER_FRAMES', C.ABSENCE_BUFFER_FRAMES
    ))
    # "Rời chỗ ngắn" — đi uống nước, vệ sinh... (mặc định 60s = 1 phút)
    ABSENCE_SHORT_THRESHOLD = int(os.getenv(
        'ABSENCE_SHORT_THRESHOLD', C.ABSENCE_SHORT_THRESHOLD
    ))
    # "Vắng mặt" chính thức — ghi nhận & cảnh báo (mặc định 300s = 5 phút)
    ABSENCE_LONG_THRESHOLD  = int(os.getenv(
        'ABSENCE_LONG_THRESHOLD', C.ABSENCE_LONG_THRESHOLD
    ))

    # ── Distraction ─────────────────────────────────────────────────
    DISTRACTION_DURATION    = int(os.getenv(
        'DISTRACTION_DURATION', C.DISTRACTION_DURATION
    ))
    ACTIVITY_SMOOTH_FRAMES  = int(os.getenv(
        'ACTIVITY_SMOOTH_FRAMES', C.ACTIVITY_SMOOTH_FRAMES
    ))

    # ── Phone Detection ─────────────────────────────────────────────
    PHONE_DETECTION_ENABLED     = _bool(
        'PHONE_DETECTION_ENABLED', C.PHONE_DETECTION_ENABLED
    )
    PHONE_SCORE_THRESHOLD       = int(os.getenv(
        'PHONE_SCORE_THRESHOLD', C.PHONE_SCORE_THRESHOLD
    ))
    PHONE_SCORE_UPPER_THRESHOLD = int(os.getenv(
        'PHONE_SCORE_UPPER_THRESHOLD', C.PHONE_SCORE_UPPER_THRESHOLD
    ))
    PHONE_MAX_HAND_SPEED        = int(os.getenv(
        'PHONE_MAX_HAND_SPEED', C.PHONE_MAX_HAND_SPEED
    ))

    # ── Phone Score Zone Weights ─────────────────────────────────────
    PHONE_SCORE_ZONE_MIDDLE  = int(os.getenv('PHONE_SCORE_ZONE_MIDDLE',  C.PHONE_SCORE_ZONE_MIDDLE))
    PHONE_SCORE_ZONE_UPPER   = int(os.getenv('PHONE_SCORE_ZONE_UPPER',   C.PHONE_SCORE_ZONE_UPPER))
    PHONE_SCORE_SPEED_STILL  = int(os.getenv('PHONE_SCORE_SPEED_STILL',  C.PHONE_SCORE_SPEED_STILL))
    PHONE_SCORE_SPEED_SLOW   = int(os.getenv('PHONE_SCORE_SPEED_SLOW',   C.PHONE_SCORE_SPEED_SLOW))
    PHONE_SCORE_SPEED_MEDIUM = int(os.getenv('PHONE_SCORE_SPEED_MEDIUM', C.PHONE_SCORE_SPEED_MEDIUM))
    PHONE_SCORE_ONE_HAND     = int(os.getenv('PHONE_SCORE_ONE_HAND',     C.PHONE_SCORE_ONE_HAND))
    PHONE_SCORE_TWO_HANDS    = int(os.getenv('PHONE_SCORE_TWO_HANDS',    C.PHONE_SCORE_TWO_HANDS))
    PHONE_SCORE_SPEED_CUTOFF = int(os.getenv('PHONE_SCORE_SPEED_CUTOFF', C.PHONE_SCORE_SPEED_CUTOFF))

    # ── ROI — Region of Interest ────────────────────────────────────
    ROI_ENABLED = _bool('ROI_ENABLED', C.ROI_ENABLED)
    ROI_X1      = float(os.getenv('ROI_X1', C.ROI_X1))
    ROI_X2      = float(os.getenv('ROI_X2', C.ROI_X2))
    ROI_Y1      = float(os.getenv('ROI_Y1', C.ROI_Y1))
    ROI_Y2      = float(os.getenv('ROI_Y2', C.ROI_Y2))

    # ── Gaze Thresholds ─────────────────────────────────────────────
    GAZE_PITCH_UP       = int(os.getenv('GAZE_PITCH_UP',       C.GAZE_PITCH_UP))
    GAZE_PITCH_DOWN     = int(os.getenv('GAZE_PITCH_DOWN',     C.GAZE_PITCH_DOWN))
    GAZE_YAW_THRESHOLD  = int(os.getenv('GAZE_YAW_THRESHOLD',  C.GAZE_YAW_THRESHOLD))
    GAZE_ROLL_THRESHOLD    = int(os.getenv('GAZE_ROLL_THRESHOLD',    C.GAZE_ROLL_THRESHOLD))
    CAMERA_YAW_OFFSET      = int(os.getenv('CAMERA_YAW_OFFSET',      C.CAMERA_YAW_OFFSET))
    GAZE_SIDE_PITCH_BOOST  = int(os.getenv('GAZE_SIDE_PITCH_BOOST',  C.GAZE_SIDE_PITCH_BOOST))
    GAZE_SIDE_YAW_SLACK    = int(os.getenv('GAZE_SIDE_YAW_SLACK',    C.GAZE_SIDE_YAW_SLACK))
    GAZE_FRONT_PITCH_BOOST = int(os.getenv('GAZE_FRONT_PITCH_BOOST', C.GAZE_FRONT_PITCH_BOOST))
    GAZE_FRONT_YAW_SLACK   = int(os.getenv('GAZE_FRONT_YAW_SLACK',   C.GAZE_FRONT_YAW_SLACK))

    # ── Hand Zone Ratios ────────────────────────────────────────────
    HAND_ZONE_UPPER_RATIO   = float(os.getenv(
        'HAND_ZONE_UPPER_RATIO',  C.HAND_ZONE_UPPER_RATIO
    ))
    HAND_ZONE_BOTTOM_RATIO  = float(os.getenv(
        'HAND_ZONE_BOTTOM_RATIO', C.HAND_ZONE_BOTTOM_RATIO
    ))

    # ── Hand Speed Thresholds ───────────────────────────────────────
    HAND_SPEED_STILL        = int(os.getenv('HAND_SPEED_STILL',       C.HAND_SPEED_STILL))
    HAND_SPEED_TYPING_MAX   = int(os.getenv('HAND_SPEED_TYPING_MAX',  C.HAND_SPEED_TYPING_MAX))
    HAND_SPEED_READING      = int(os.getenv('HAND_SPEED_READING',     C.HAND_SPEED_READING))
    HAND_SPEED_GESTURE_MAX  = int(os.getenv('HAND_SPEED_GESTURE_MAX', C.HAND_SPEED_GESTURE_MAX))
    HAND_SPEED_FACE_MAX     = int(os.getenv('HAND_SPEED_FACE_MAX',    C.HAND_SPEED_FACE_MAX))

    # ── Focus Scoring ───────────────────────────────────────────────
    SCORE_SITTING           = int(os.getenv('SCORE_SITTING',        C.SCORE_SITTING))
    SCORE_SITTING_GOOD      = int(os.getenv('SCORE_SITTING_GOOD',   C.SCORE_SITTING_GOOD))
    SCORE_STANDING          = int(os.getenv('SCORE_STANDING',       C.SCORE_STANDING))
    SCORE_GAZE_SCREEN       = int(os.getenv('SCORE_GAZE_SCREEN',    C.SCORE_GAZE_SCREEN))
    SCORE_GAZE_DOWN         = int(os.getenv('SCORE_GAZE_DOWN',      C.SCORE_GAZE_DOWN))
    SCORE_GAZE_TILT         = int(os.getenv('SCORE_GAZE_TILT',      C.SCORE_GAZE_TILT))
    SCORE_GAZE_OTHER        = int(os.getenv('SCORE_GAZE_OTHER',     C.SCORE_GAZE_OTHER))
    SCORE_HAND_TYPING       = int(os.getenv('SCORE_HAND_TYPING',        C.SCORE_HAND_TYPING))
    SCORE_HAND_WRITING      = int(os.getenv('SCORE_HAND_WRITING',       C.SCORE_HAND_WRITING))
    SCORE_HAND_TYPING_PAUSE = int(os.getenv('SCORE_HAND_TYPING_PAUSE',  C.SCORE_HAND_TYPING_PAUSE))
    SCORE_HAND_READING      = int(os.getenv('SCORE_HAND_READING',       C.SCORE_HAND_READING))
    SCORE_HAND_GESTURING    = int(os.getenv('SCORE_HAND_GESTURING',     C.SCORE_HAND_GESTURING))
    SCORE_HAND_NONE         = int(os.getenv('SCORE_HAND_NONE',          C.SCORE_HAND_NONE))
    SCORE_HAND_FACE         = int(os.getenv('SCORE_HAND_FACE',          C.SCORE_HAND_FACE))
    SCORE_HAND_ACTIVE       = int(os.getenv('SCORE_HAND_ACTIVE',        C.SCORE_HAND_ACTIVE))
    SCORE_HAND_DEFAULT      = int(os.getenv('SCORE_HAND_DEFAULT',       C.SCORE_HAND_DEFAULT))
    SCORE_PENALTY_PHONE         = int(os.getenv(
        'SCORE_PENALTY_PHONE',       C.SCORE_PENALTY_PHONE
    ))
    SCORE_PENALTY_DISTRACTION   = int(os.getenv(
        'SCORE_PENALTY_DISTRACTION', C.SCORE_PENALTY_DISTRACTION
    ))
    SCORE_PENALTY_TALKING       = int(os.getenv(
        'SCORE_PENALTY_TALKING',     C.SCORE_PENALTY_TALKING
    ))
    SCORE_PENALTY_PLAYING       = int(os.getenv(
        'SCORE_PENALTY_PLAYING',     C.SCORE_PENALTY_PLAYING
    ))
    SCORE_EATING                = int(os.getenv('SCORE_EATING',    C.SCORE_EATING))
    SCORE_SLEEPING              = int(os.getenv('SCORE_SLEEPING',  C.SCORE_SLEEPING))

    # ── AI / Tutor ──────────────────────────────────────────────────
    OPENAI_API_KEY          = os.getenv('OPENAI_API_KEY', '')
    STUDENT_NAME            = os.getenv('STUDENT_NAME',         C.STUDENT_NAME)
    DISTRACTION_THRESHOLD   = int(os.getenv(
        'DISTRACTION_THRESHOLD', C.DISTRACTION_THRESHOLD
    ))
    REMINDER_COOLDOWN       = int(os.getenv(
        'REMINDER_COOLDOWN', C.REMINDER_COOLDOWN
    ))

    # ── Multi-Person Tracking ────────────────────────────────────────
    MULTI_PERSON_ENABLED  = _bool('MULTI_PERSON_ENABLED', C.MULTI_PERSON_ENABLED)
    MAX_PERSONS           = int(os.getenv('MAX_PERSONS',           C.MAX_PERSONS))
    PERSON_MISSING_FRAMES = int(os.getenv('PERSON_MISSING_FRAMES', C.PERSON_MISSING_FRAMES))
    PERSON_MATCH_DISTANCE = int(os.getenv('PERSON_MATCH_DISTANCE', C.PERSON_MATCH_DISTANCE))
    PERSON_BODY_EXPAND_Y  = float(os.getenv('PERSON_BODY_EXPAND_Y', C.PERSON_BODY_EXPAND_Y))
    PERSON_BODY_EXPAND_X  = float(os.getenv('PERSON_BODY_EXPAND_X', C.PERSON_BODY_EXPAND_X))

    # ── YOLO Detector ────────────────────────────────────────────────
    YOLO_ENABLED        = _bool('YOLO_ENABLED',      C.YOLO_ENABLED)
    YOLO_MODEL_PATH     = os.getenv('YOLO_MODEL_PATH', C.YOLO_MODEL_PATH)
    YOLO_INPUT_SIZE     = int(os.getenv('YOLO_INPUT_SIZE',   C.YOLO_INPUT_SIZE))
    YOLO_CONFIDENCE     = float(os.getenv('YOLO_CONFIDENCE', C.YOLO_CONFIDENCE))
    YOLO_SKIP_FRAMES    = int(os.getenv('YOLO_SKIP_FRAMES',  C.YOLO_SKIP_FRAMES))
    YOLO_BBOX_MAX_STALE = int(os.getenv('YOLO_BBOX_MAX_STALE', C.YOLO_BBOX_MAX_STALE))
    YOLO_TARGET_CLASSES         = C.YOLO_TARGET_CLASSES    # list, không override qua env
    YOLO_NMS_IOU                = float(os.getenv('YOLO_NMS_IOU', C.YOLO_NMS_IOU))
    YOLO_SECONDARY_MODEL_PATH   = os.getenv('YOLO_SECONDARY_MODEL_PATH', C.YOLO_SECONDARY_MODEL_PATH)
    YOLO_SECONDARY_CLASSES      = C.YOLO_SECONDARY_CLASSES  # list, không override qua env
    YOLO_SECONDARY_CONFIDENCE   = float(os.getenv('YOLO_SECONDARY_CONFIDENCE', C.YOLO_SECONDARY_CONFIDENCE))
    YOLO_TERTIARY_MODEL_PATH    = os.getenv('YOLO_TERTIARY_MODEL_PATH', C.YOLO_TERTIARY_MODEL_PATH)
    YOLO_TERTIARY_CLASSES       = C.YOLO_TERTIARY_CLASSES   # list, không override qua env
    YOLO_TERTIARY_INPUT_SIZE    = int(os.getenv('YOLO_TERTIARY_INPUT_SIZE', C.YOLO_TERTIARY_INPUT_SIZE))
    YOLO_TERTIARY_CONFIDENCE    = float(os.getenv('YOLO_TERTIARY_CONFIDENCE', C.YOLO_TERTIARY_CONFIDENCE))
    YOLO_PREFER_ONNX            = _bool('YOLO_PREFER_ONNX', C.YOLO_PREFER_ONNX)

    # ── Image Quality ────────────────────────────────────────────────
    IMAGE_QUALITY_MIN_BLUR_SCORE = float(os.getenv(
        'IMAGE_QUALITY_MIN_BLUR_SCORE', C.IMAGE_QUALITY_MIN_BLUR_SCORE
    ))
    IMAGE_QUALITY_MIN_COVERAGE   = float(os.getenv(
        'IMAGE_QUALITY_MIN_COVERAGE',   C.IMAGE_QUALITY_MIN_COVERAGE
    ))
    IMAGE_QUALITY_MIN_BRIGHTNESS = int(os.getenv(
        'IMAGE_QUALITY_MIN_BRIGHTNESS', C.IMAGE_QUALITY_MIN_BRIGHTNESS
    ))
    IMAGE_QUALITY_MAX_BRIGHTNESS = int(os.getenv(
        'IMAGE_QUALITY_MAX_BRIGHTNESS', C.IMAGE_QUALITY_MAX_BRIGHTNESS
    ))
    JPEG_QUALITY          = int(os.getenv('JPEG_QUALITY',          C.JPEG_QUALITY))
    SNAPSHOT_JPEG_QUALITY = int(os.getenv('SNAPSHOT_JPEG_QUALITY', C.SNAPSHOT_JPEG_QUALITY))

    # ── Thermal Management ───────────────────────────────────────────
    THERMAL_WARN_TEMP        = float(os.getenv('THERMAL_WARN_TEMP',     C.THERMAL_WARN_TEMP))
    THERMAL_HIGH_TEMP        = float(os.getenv('THERMAL_HIGH_TEMP',     C.THERMAL_HIGH_TEMP))
    THERMAL_CRITICAL_TEMP    = float(os.getenv('THERMAL_CRITICAL_TEMP', C.THERMAL_CRITICAL_TEMP))
    THERMAL_WARN_EXTRA_SKIP  = int(os.getenv('THERMAL_WARN_EXTRA_SKIP',  C.THERMAL_WARN_EXTRA_SKIP))
    THERMAL_HIGH_EXTRA_SKIP  = int(os.getenv('THERMAL_HIGH_EXTRA_SKIP',  C.THERMAL_HIGH_EXTRA_SKIP))
    THERMAL_HIGH_EXTRA_SLEEP = float(os.getenv('THERMAL_HIGH_EXTRA_SLEEP', C.THERMAL_HIGH_EXTRA_SLEEP))
    THERMAL_READ_INTERVAL    = int(os.getenv('THERMAL_READ_INTERVAL',    C.THERMAL_READ_INTERVAL))

    # ── Pose-Based Gaze ──────────────────────────────────────────────
    CAMERA_SIDE           = os.getenv('CAMERA_SIDE',           C.CAMERA_SIDE)
    POSE_PITCH_SCALE      = float(os.getenv('POSE_PITCH_SCALE', C.POSE_PITCH_SCALE))
    POSE_YAW_SCALE        = float(os.getenv('POSE_YAW_SCALE',   C.POSE_YAW_SCALE))
    MAX_POSE_CACHE_FRAMES = int(os.getenv('MAX_POSE_CACHE_FRAMES', C.MAX_POSE_CACHE_FRAMES))
    MIN_POSE_CROP_H       = int(os.getenv('MIN_POSE_CROP_H',    C.MIN_POSE_CROP_H))
    MIN_POSE_CROP_W       = int(os.getenv('MIN_POSE_CROP_W',    C.MIN_POSE_CROP_W))

    # ── Drowsiness Detection ───────────────────────────────────────
    DROWSY_EYE_CLOSURE_THRESHOLD = float(os.getenv(
        'DROWSY_EYE_CLOSURE_THRESHOLD', C.DROWSY_EYE_CLOSURE_THRESHOLD
    ))
    DROWSY_EYE_CLOSURE_DURATION  = float(os.getenv(
        'DROWSY_EYE_CLOSURE_DURATION',  C.DROWSY_EYE_CLOSURE_DURATION
    ))
    DROWSY_YAWN_THRESHOLD        = float(os.getenv(
        'DROWSY_YAWN_THRESHOLD',        C.DROWSY_YAWN_THRESHOLD
    ))
    DROWSY_YAWN_DURATION         = float(os.getenv(
        'DROWSY_YAWN_DURATION',         C.DROWSY_YAWN_DURATION
    ))
    DROWSY_BLINK_RATE_HIGH       = int(os.getenv(
        'DROWSY_BLINK_RATE_HIGH',       C.DROWSY_BLINK_RATE_HIGH
    ))
    DROWSY_HEAD_TILT_DURATION    = float(os.getenv(
        'DROWSY_HEAD_TILT_DURATION',    C.DROWSY_HEAD_TILT_DURATION
    ))
    DROWSY_HEAD_NOD_PITCH        = int(os.getenv(
        'DROWSY_HEAD_NOD_PITCH',        C.DROWSY_HEAD_NOD_PITCH
    ))
    DROWSY_HEAD_NOD_COUNT        = int(os.getenv(
        'DROWSY_HEAD_NOD_COUNT',        C.DROWSY_HEAD_NOD_COUNT
    ))
    DROWSY_HEAD_NOD_WINDOW       = int(os.getenv(
        'DROWSY_HEAD_NOD_WINDOW',       C.DROWSY_HEAD_NOD_WINDOW
    ))
    DROWSY_HEAD_DROP_PITCH       = int(os.getenv(
        'DROWSY_HEAD_DROP_PITCH',       C.DROWSY_HEAD_DROP_PITCH
    ))
    DROWSY_HEAD_DROP_DURATION    = float(os.getenv(
        'DROWSY_HEAD_DROP_DURATION',    C.DROWSY_HEAD_DROP_DURATION
    ))
    DROWSY_SLEEPING_LOG_MIN      = float(os.getenv(
        'DROWSY_SLEEPING_LOG_MIN',      C.DROWSY_SLEEPING_LOG_MIN
    ))

    # ── New Activity Thresholds ─────────────────────────────────────
    TALKING_MIN_FRAMES         = int(os.getenv(
        'TALKING_MIN_FRAMES',         C.TALKING_MIN_FRAMES
    ))
    PLAYING_MIN_FRAMES         = int(os.getenv(
        'PLAYING_MIN_FRAMES',         C.PLAYING_MIN_FRAMES
    ))
    PLAYING_MIN_HAND_SPEED     = int(os.getenv(
        'PLAYING_MIN_HAND_SPEED',     C.PLAYING_MIN_HAND_SPEED
    ))
    PHONE_MIN_SUSTAINED_FRAMES = int(os.getenv(
        'PHONE_MIN_SUSTAINED_FRAMES', C.PHONE_MIN_SUSTAINED_FRAMES
    ))
    PHONE_DURATION_LOG_INTERVAL = int(os.getenv(
        'PHONE_DURATION_LOG_INTERVAL', C.PHONE_DURATION_LOG_INTERVAL
    ))
    EATING_MIN_FRAMES          = int(os.getenv(
        'EATING_MIN_FRAMES',          C.EATING_MIN_FRAMES
    ))
    EATING_MIN_HAND_SPEED      = int(os.getenv(
        'EATING_MIN_HAND_SPEED',      C.EATING_MIN_HAND_SPEED
    ))
    EATING_CUP_MAX_Y_RATIO     = float(os.getenv(
        'EATING_CUP_MAX_Y_RATIO',     C.EATING_CUP_MAX_Y_RATIO
    ))

    # ── Confidence Scoring ───────────────────────────────────────────
    CONFIDENCE_MIN_CLASSIFY       = int(os.getenv('CONFIDENCE_MIN_CLASSIFY',       C.CONFIDENCE_MIN_CLASSIFY))
    CONFIDENCE_WRITING_THRESHOLD  = int(os.getenv('CONFIDENCE_WRITING_THRESHOLD',  C.CONFIDENCE_WRITING_THRESHOLD))
    CONFIDENCE_READING_THRESHOLD  = int(os.getenv('CONFIDENCE_READING_THRESHOLD',  C.CONFIDENCE_READING_THRESHOLD))
    CONFIDENCE_COMPUTER_THRESHOLD = int(os.getenv('CONFIDENCE_COMPUTER_THRESHOLD', C.CONFIDENCE_COMPUTER_THRESHOLD))
    CONFIDENCE_PHONE_THRESHOLD    = int(os.getenv('CONFIDENCE_PHONE_THRESHOLD',     C.CONFIDENCE_PHONE_THRESHOLD))
    CONFIDENCE_FOCUSED_THRESHOLD  = int(os.getenv('CONFIDENCE_FOCUSED_THRESHOLD',  C.CONFIDENCE_FOCUSED_THRESHOLD))
    CONFIDENCE_WATCHING_THRESHOLD = int(os.getenv('CONFIDENCE_WATCHING_THRESHOLD', C.CONFIDENCE_WATCHING_THRESHOLD))
    CONFIDENCE_TALKING_THRESHOLD  = int(os.getenv('CONFIDENCE_TALKING_THRESHOLD',  C.CONFIDENCE_TALKING_THRESHOLD))
    CONFIDENCE_EATING_THRESHOLD   = int(os.getenv('CONFIDENCE_EATING_THRESHOLD',   C.CONFIDENCE_EATING_THRESHOLD))
    CONFIDENCE_PLAYING_THRESHOLD  = int(os.getenv('CONFIDENCE_PLAYING_THRESHOLD',  C.CONFIDENCE_PLAYING_THRESHOLD))
    CONFIDENCE_DISTRACTED_THRESHOLD = int(os.getenv('CONFIDENCE_DISTRACTED_THRESHOLD', C.CONFIDENCE_DISTRACTED_THRESHOLD))
    HOMEWORK_DETECT_DURATION      = int(os.getenv('HOMEWORK_DETECT_DURATION',      C.HOMEWORK_DETECT_DURATION))
    HOMEWORK_REQUEST_TIMEOUT      = int(os.getenv('HOMEWORK_REQUEST_TIMEOUT',      C.HOMEWORK_REQUEST_TIMEOUT))
    HOMEWORK_COOLDOWN             = int(os.getenv('HOMEWORK_COOLDOWN',             C.HOMEWORK_COOLDOWN))
    HOMEWORK_WRITING_MIN_SCORE    = int(os.getenv('HOMEWORK_WRITING_MIN_SCORE',    C.HOMEWORK_WRITING_MIN_SCORE))
    HOMEWORK_AUTO_CAPTURE_FRAMES  = int(os.getenv('HOMEWORK_AUTO_CAPTURE_FRAMES',  C.HOMEWORK_AUTO_CAPTURE_FRAMES))
    HOMEWORK_QUALITY_RETRIES      = int(os.getenv('HOMEWORK_QUALITY_RETRIES',      C.HOMEWORK_QUALITY_RETRIES))

    # ── TTS / Alert Service (Group 22) ───────────────────────────────
    TTS_ENABLED              = os.getenv('TTS_ENABLED', str(C.TTS_ENABLED)).lower() not in ('false', '0', 'no')
    TTS_SPEED                = int(os.getenv('TTS_SPEED',                C.TTS_SPEED))
    TTS_VOICE                = os.getenv('TTS_VOICE',                    C.TTS_VOICE)
    TTS_PHONE_ALERT_DELAY    = int(os.getenv('TTS_PHONE_ALERT_DELAY',    C.TTS_PHONE_ALERT_DELAY))
    TTS_DISTRACT_ALERT_DELAY = int(os.getenv('TTS_DISTRACT_ALERT_DELAY', C.TTS_DISTRACT_ALERT_DELAY))

    # ── IMX500 AI Camera (Group 23) ──────────────────────────────────
    # Bật True khi dùng Raspberry Pi AI Camera (Sony IMX500 12.3MP).
    # False (mặc định) → dùng Camera v2.1 (IMX219) hoặc camera tiêu chuẩn khác.
    CAMERA_IMX500_ENABLED  = _bool('CAMERA_IMX500_ENABLED', C.CAMERA_IMX500_ENABLED)
    YOLO_IMX500_MODEL_PATH = os.getenv('YOLO_IMX500_MODEL_PATH', C.YOLO_IMX500_MODEL_PATH)
    YOLO_IMX500_CONF       = float(os.getenv('YOLO_IMX500_CONF',     C.YOLO_IMX500_CONF))
    YOLO_IMX500_IOU        = float(os.getenv('YOLO_IMX500_IOU',      C.YOLO_IMX500_IOU))
    YOLO_IMX500_MAX_DETS   = int(os.getenv('YOLO_IMX500_MAX_DETS',   C.YOLO_IMX500_MAX_DETS))
    YOLO_IMX500_INPUT_SIZE = int(os.getenv('YOLO_IMX500_INPUT_SIZE', C.YOLO_IMX500_INPUT_SIZE))

    # ── Paths ────────────────────────────────────────────────────────
    BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR      = os.path.join(BASE_DIR, 'logs')
    WEB_DIR      = os.path.join(BASE_DIR, 'web')
    TEMPLATE_DIR = os.path.join(WEB_DIR, 'templates')
