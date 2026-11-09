# core/constants.py
# ═══════════════════════════════════════════════════════════════════
#  FILE CẤU HÌNH NGƯỠNG TRUNG TÂM
#  Thay đổi giá trị tại đây → áp dụng ngay toàn bộ hệ thống
#  Có thể override từng giá trị qua file .env (không cần sửa code)
# ═══════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────
#  NHÓM 1: CAMERA & STREAM
# ───────────────────────────────────────────────────────────────────

# Độ phân giải stream / detection (lores stream — dùng cho MJPEG + MediaPipe + YOLO)
# Giữ ở 1280×720 để đảm bảo detection FPS. Tăng lên sẽ làm chậm phân tích.
CAMERA_WIDTH    = 1280
CAMERA_HEIGHT   = 720

# Độ phân giải snapshot cao (main stream — chỉ dùng khi chụp ảnh gửi AI)
# IMX219 (Camera v2.1) tối đa 3280×2464 (8MP).
# 2560×1920 = 5MP — cân bằng tốt: rõ chữ/bài tập, file nhỏ hơn 8MP
# 3280×2464 = 8MP đầy đủ — rõ nhất nhưng file lớn (~800KB JPEG)
SNAPSHOT_WIDTH  = 2560
SNAPSHOT_HEIGHT = 1920

# Số khung hình mỗi giây camera cố gắng capture
# Benchmark RPi5: MediaPipe Hands+Pose ≈ 77ms/frame → tối đa ~13fps thực tế
# Đặt CAMERA_FPS = 30 để không bị lag capture, nhưng detection sẽ tự throttle
CAMERA_FPS      = 30

# ── FPS giới hạn xử lý MediaPipe (detection) ────────────────────
# Pipeline phân tích (MediaPipe) chạy tối đa bao nhiêu frame/giây.
# Benchmark cho thấy giới hạn vật lý ~12-13fps trên RPi5.
# Đặt DETECTION_FPS = 10 → tự ngủ giữa các frame → CPU 77% thay vì 100%
# Đặt DETECTION_FPS = 8  → CPU còn nhẹ hơn, phù hợp khi chạy nhiều app
# Đặt DETECTION_FPS = 15 → gần max vật lý, CPU cao nhưng latency thấp
DETECTION_FPS   = 10

# ── FPS giới hạn stream MJPEG ────────────────────────────────────
# Browser nhận bao nhiêu frame/giây qua MJPEG.
# 20fps là đủ mượt cho giám sát, giảm tải Flask + network.
# 30fps = smooth hơn nhưng tốn CPU encode JPEG liên tục.
STREAM_FPS      = 20

# Địa chỉ và cổng web stream (dashboard + MJPEG)
# '0.0.0.0' = lắng nghe mọi interface (truy cập từ mạng LAN)
STREAM_HOST     = '0.0.0.0'
STREAM_PORT     = 5000


# ───────────────────────────────────────────────────────────────────
#  NHÓM 2: PHÁT HIỆN VẮNG MẶT (ABSENCE DETECTION)
# ───────────────────────────────────────────────────────────────────

# Số frame camera liên tiếp không detect được người mới bắt đầu tính
# thời gian vắng mặt. Giúp tránh nhận nhầm khi có nhiều người cùng
# hàng (MediaPipe đôi khi không detect được giữa các frame).
# Tham khảo: 30 FPS × 1.5 giây = 45 frame
# Tăng lên nếu hay bị false "vắng mặt" khi ngồi đông người
# Giảm xuống nếu muốn phát hiện rời chỗ nhanh hơn (min ~10)
ABSENCE_BUFFER_FRAMES = 45

# ── Phân loại 3 mức vắng mặt ──────────────────────────────────────
#
#   [0s]──────[SHORT]──────[LONG]────────────►
#    ↑          ↑             ↑
#  Có mặt   Rời chỗ       Vắng mặt
#           ngắn hạn      chính thức
#
# Ngưỡng "rời chỗ ngắn" (đi uống nước, vệ sinh, hỏi bài...)
# Rời khỏi chỗ ngồi từ ABSENCE_SHORT_THRESHOLD giây trở lên
# → hiển thị "Rời chỗ ngắn" (cảnh báo nhẹ)
# Mặc định: 60 giây (1 phút)
# Điều chỉnh: giảm xuống 30s nếu muốn cảnh báo sớm hơn
ABSENCE_SHORT_THRESHOLD = 60

# Ngưỡng "vắng mặt" chính thức — mốc quan trọng để ghi nhận & cảnh báo
# Rời khỏi chỗ ngồi từ ABSENCE_LONG_THRESHOLD giây trở lên
# → hiển thị "Vắng mặt" (cảnh báo nghiêm trọng, ghi vào log)
# Mặc định: 300 giây (5 phút)
# Điều chỉnh: tăng lên 600s nếu cho phép nghỉ giữa giờ dài hơn
ABSENCE_LONG_THRESHOLD = 300


# ───────────────────────────────────────────────────────────────────
#  NHÓM 3: PHÁT HIỆN MẤT TẬP TRUNG (DISTRACTION)
# ───────────────────────────────────────────────────────────────────

# Số giây nhìn sang hướng khác LIÊN TIẾP mới tính là "mất tập trung"
# Tăng lên nếu hay nhận nhầm khi học sinh chỉ nhìn xung quanh thoáng
# Giảm xuống nếu muốn phát hiện mất tập trung nhanh hơn (min 2s)
DISTRACTION_DURATION = 5

# Số frame dùng để làm mượt (smooth) kết quả trạng thái hoạt động
# Lấy trạng thái phổ biến nhất trong cửa sổ này thay vì từng frame
# → tránh nhấp nháy khi chuyển trạng thái nhanh
# Tham khảo: 30 FPS × 1.5 giây = 45 frame
ACTIVITY_SMOOTH_FRAMES = 45


# ───────────────────────────────────────────────────────────────────
#  NHÓM 4: PHÁT HIỆN DÙNG ĐIỆN THOẠI (PHONE DETECTION)
# ───────────────────────────────────────────────────────────────────

# Bật / tắt tính năng phát hiện điện thoại
PHONE_DETECTION_ENABLED = True

# Điểm tối thiểu (0-100) từ hand detector để xét là "có thể dùng phone"
# Tăng lên (65-75) nếu hay nhận nhầm đồ vật khác là điện thoại
# Giảm xuống (45-50) nếu khó detect điện thoại hơn
PHONE_SCORE_THRESHOLD = 55

# Điểm tối thiểu khi tay ở vùng upper (cầm phone lên cao gần mặt)
# Thấp hơn PHONE_SCORE_THRESHOLD vì upper zone đã là dấu hiệu rõ
PHONE_SCORE_UPPER_THRESHOLD = 40

# Tốc độ tay tối đa (px/frame) khi xét là đang dùng điện thoại
# Tay di chuyển nhanh hơn → thường là typing/viết, không phải phone
# Tăng lên nếu muốn detect cả khi đang gõ nhanh trên điện thoại
# 20px: bao gồm scroll nhanh, gõ nhẹ trên phone (trước đây 15 quá chặt)
PHONE_MAX_HAND_SPEED = 20


# ───────────────────────────────────────────────────────────────────
#  NHÓM 5: ROI — VÙNG PHÂN TÍCH (CHO PHÒNG NHIỀU NGƯỜI)
# ───────────────────────────────────────────────────────────────────

# Bật ROI để chỉ phân tích vùng giữa frame
# Dùng khi camera thấy nhiều học sinh trong cùng một hàng
# → loại bỏ người ngồi hai bên, chỉ phân tích người ở trung tâm
ROI_ENABLED = False

# Tọa độ ROI theo tỷ lệ (0.0 = trái/trên, 1.0 = phải/dưới)
# Ví dụ: X1=0.15, X2=0.85 → phân tích 70% giữa frame theo chiều ngang
# Điều chỉnh theo vị trí học sinh trong frame thực tế
ROI_X1 = 0.15   # Bắt đầu từ 15% chiều ngang
ROI_X2 = 0.85   # Kết thúc tại 85% chiều ngang
ROI_Y1 = 0.0    # Bắt đầu từ trên cùng (thường không cần crop dọc)
ROI_Y2 = 1.0    # Kết thúc tại dưới cùng


# ───────────────────────────────────────────────────────────────────
#  NHÓM 6: MOTION DETECTOR
# ───────────────────────────────────────────────────────────────────

# Độ nhạy phát hiện chuyển động (0-255)
# Thấp (5-15)  = rất nhạy, phát hiện cả dao động nhỏ (ánh sáng thay đổi)
# Cao  (30-50) = ít nhạy, chỉ phát hiện chuyển động lớn rõ ràng
MOTION_THRESHOLD = 20

# Diện tích tối thiểu (pixel²) của vùng chuyển động để tính là "có motion"
# Tăng lên để loại bỏ nhiễu nhỏ (bóng đèn nhấp nháy, côn trùng...)
# Giảm xuống nếu muốn phát hiện cử động tay rất nhỏ
MOTION_MIN_AREA = 500


# ───────────────────────────────────────────────────────────────────
#  NHÓM 7: GAZE DETECTOR — NGƯỠNG GÓC ĐẦU
# ───────────────────────────────────────────────────────────────────
# Các góc được tính từ MediaPipe FaceMesh (đơn vị: độ)

# Góc pitch (cúi/ngửa đầu)
# Ngửa đầu lên: pitch > GAZE_PITCH_UP → "nhìn lên / mơ màng"
# Tăng lên (25-30) nếu camera đặt thấp làm pitch tự nhiên cao hơn
GAZE_PITCH_UP = 20

# Cúi đầu xuống: pitch < GAZE_PITCH_DOWN → "nhìn xuống sách/điện thoại"
# Giá trị âm. Giảm xuống (-20, -25) nếu camera đặt cao và học sinh
# hay nhìn xuống bàn nhiều → tránh nhận nhầm là "mất tập trung"
GAZE_PITCH_DOWN = -15

# Góc yaw (quay trái/phải)
# Quay trái:  yaw >  GAZE_YAW_THRESHOLD → "nhìn sang trái"
# Quay phải:  yaw < -GAZE_YAW_THRESHOLD → "nhìn sang phải"
# Tăng lên (25-30) nếu học sinh hay nhìn sang màn hình phụ bên cạnh
GAZE_YAW_THRESHOLD = 28   # Tăng từ 20→28: màn hình hơi lệch sang phải/trái
# vẫn tính là "looking_screen" thay vì bị classify là looking_left/right

# Góc roll (nghiêng đầu sang trái/phải)
# |roll| > GAZE_ROLL_THRESHOLD → "nghiêng đầu / có thể buồn ngủ"
# Tăng lên nếu học sinh có thói quen nghiêng đầu khi đọc bình thường
GAZE_ROLL_THRESHOLD = 20

# Bù góc camera bên cạnh: nhìn xuống bàn = pitch thấp hơn + yaw lệch
# Khi cam_side=left/right, nới rộng ngưỡng pitch xuống BOOST độ để bắt
# trường hợp nhìn xuống vở/điện thoại bên cạnh (không cần cúi nhiều).
# GAZE_SIDE_PITCH_BOOST = 7 → ngưỡng hiệu dụng = -15 + 7 = -8°
GAZE_SIDE_PITCH_BOOST = 7

# Giới hạn yaw tối đa cho "nhìn xuống bàn" (side camera):
# Nếu yaw vượt quá GAZE_YAW_THRESHOLD + GAZE_SIDE_YAW_SLACK → vẫn là distraction
# 28 + 15 = 43°: đủ để bắt phone/vở bên phải nhưng không bắt nhìn tường xa
GAZE_SIDE_YAW_SLACK = 15

# Bù góc camera phía trước nhưng lệch nhẹ (front_left / front_right):
# Nhỏ hơn camera cạnh vì góc lệch ít → chỉ cần boost nhẹ
# GAZE_FRONT_PITCH_BOOST = 4 → ngưỡng hiệu dụng = -15 + 4 = -11°
GAZE_FRONT_PITCH_BOOST = 4
# 28 + 8 = 36°: đủ để bắt nhìn xuống bàn khi camera lệch nhẹ
GAZE_FRONT_YAW_SLACK   = 8

# Hiệu chỉnh camera đặt nghiêng/bên cạnh (đơn vị: độ)
# Camera đặt thẳng trước mặt  → CAMERA_YAW_OFFSET = 0
# Camera đặt bên trái người   → CAMERA_YAW_OFFSET = +70  (yaw khi nhìn thẳng ≈ +70)
# Camera đặt bên phải người   → CAMERA_YAW_OFFSET = -70
# Cách xác định: nhìn vào log góc Y (yaw) khi người đang nhìn thẳng màn hình
# rồi đặt CAMERA_YAW_OFFSET bằng giá trị đó
CAMERA_YAW_OFFSET = 0


# ───────────────────────────────────────────────────────────────────
#  NHÓM 8: HAND DETECTOR — PHÂN VÙNG VÀ TỐC ĐỘ TAY
# ───────────────────────────────────────────────────────────────────
# Frame được chia 3 vùng dọc theo chiều Y (tỷ lệ so với chiều cao frame)
#
#   ┌─────────────────────────────────┐
#   │  UPPER ZONE (y < 0.30)          │ ← vùng đầu/mặt
#   ├─────────────────────────────────┤ ← HAND_ZONE_UPPER_RATIO
#   │  MIDDLE ZONE (0.30 < y < 0.60)  │ ← vùng ngực/lòng (điện thoại)
#   ├─────────────────────────────────┤ ← HAND_ZONE_BOTTOM_RATIO
#   │  BOTTOM ZONE (y > 0.60)         │ ← vùng bàn/bàn phím
#   └─────────────────────────────────┘
#
# Điều chỉnh nếu camera đặt ở góc khác (cao hơn/thấp hơn bình thường)
HAND_ZONE_UPPER_RATIO  = 0.30   # Ranh giới upper/middle (30% từ trên)
HAND_ZONE_BOTTOM_RATIO = 0.52   # Ranh giới middle/bottom (52% từ trên)
# Lý do 0.52 thay vì 0.60: tay trên bàn phím thường nằm ở y=0.50-0.65
# trong frame → 0.60 khiến nhiều tư thế gõ phím bị rơi vào middle zone

# Ngưỡng tốc độ tay theo vùng (px/frame)
# Vùng bottom (bàn phím/bàn):
HAND_SPEED_STILL       = 5     # Tốc độ < 5: tay đặt yên trên bàn phím
HAND_SPEED_TYPING_MAX  = 20    # Tốc độ 5-20: đang gõ phím
# Tốc độ > 20: đang viết bài bằng bút (cử động nhanh hơn gõ phím)

# Vùng middle:
HAND_SPEED_READING     = 8     # Tốc độ < 8: tay nghỉ, có thể đang đọc
HAND_SPEED_GESTURE_MAX = 25    # Tốc độ 8-25: đang cử động / giải thích
# Tốc độ > 25: tay chuyển động nhiều bất thường

# Vùng upper (gần mặt):
HAND_SPEED_FACE_MAX    = 10    # Tốc độ < 10: tay chạm/gần mặt (mệt/buồn ngủ)
# Tốc độ > 10: tay chuyển động bất thường vùng trên

# Phone score thresholds (0-100, tính trong hand detector)
PHONE_SCORE_ZONE_MIDDLE   = 40   # Điểm zone nếu tay ở vùng middle
PHONE_SCORE_ZONE_UPPER    = 30   # Điểm zone nếu tay ở vùng upper
PHONE_SCORE_SPEED_STILL   = 25   # Tay đứng yên (đọc phone)
PHONE_SCORE_SPEED_SLOW    = 20   # Tay chuyển động chậm (scroll phone)
PHONE_SCORE_SPEED_MEDIUM  = 10   # Tay chuyển động trung bình
PHONE_SCORE_ONE_HAND      = 15   # Thêm điểm nếu chỉ 1 tay (cầm phone)
PHONE_SCORE_TWO_HANDS     = 5    # Thêm điểm nếu 2 tay (ít gặp hơn)
PHONE_SCORE_SPEED_CUTOFF  = 20   # Tốc độ > giá trị này → không xét phone


# ───────────────────────────────────────────────────────────────────
#  NHÓM 9: FOCUS SCORING — ĐIỂM TẬP TRUNG (0-100)
# ───────────────────────────────────────────────────────────────────
# Điểm tập trung = tổng từ 3 nguồn: tư thế + hướng nhìn + hoạt động tay
# Tổng tối đa = 100 điểm

# Điểm từ tư thế (pose)
SCORE_SITTING       = 30    # Đang ngồi (có mặt tại chỗ)
SCORE_SITTING_GOOD  = 10    # Bonus: ngồi thẳng, đúng tư thế
SCORE_STANDING      = 10    # Đứng nhưng vẫn có mặt (thuyết trình...)

# Điểm từ hướng nhìn (gaze) — cộng vào score nếu đang ngồi
SCORE_GAZE_SCREEN   = 40    # Nhìn vào màn hình
SCORE_GAZE_DOWN     = 30    # Nhìn xuống (đọc sách / ghi chép / làm bài)
SCORE_GAZE_TILT     = 10    # Nghiêng đầu (buồn ngủ, cần xem xét thêm)
SCORE_GAZE_OTHER    = 5     # Nhìn sang hướng khác (lên/trái/phải)

# Điểm từ hoạt động tay
SCORE_HAND_TYPING       = 20    # Đang gõ phím
SCORE_HAND_WRITING      = 20    # Đang viết bài bằng bút
SCORE_HAND_TYPING_PAUSE = 15    # Tay trên bàn phím (đang nghĩ)
SCORE_HAND_READING      = 15    # Tay nghỉ khi đang đọc
SCORE_HAND_GESTURING    = 10    # Cử động tay (hỏi/giải thích)
SCORE_HAND_NONE         = 10    # Không thấy tay trong frame
SCORE_HAND_FACE         = 5     # Tay gần mặt (mệt mỏi?)
SCORE_HAND_ACTIVE       = 5     # Tay chuyển động nhiều không rõ nguyên do
SCORE_HAND_DEFAULT      = 5     # Mặc định cho các trạng thái khác

# Điểm trừ (penalty)
SCORE_PENALTY_PHONE       = -30   # Đang dùng điện thoại
SCORE_PENALTY_DISTRACTION = -20   # Mất tập trung kéo dài


# ───────────────────────────────────────────────────────────────────
#  NHÓM 10: TUTOR & AI
# ───────────────────────────────────────────────────────────────────

# Tên mặc định của học sinh / nhân viên được quan sát
STUDENT_NAME = 'bạn'

# Ngưỡng % thời gian mất tập trung trong phiên để gửi cảnh báo AI
# Ví dụ: 10 = nếu mất tập trung hơn 10% thời gian → AI nhắc nhở
DISTRACTION_THRESHOLD = 10

# Thời gian tối thiểu (giây) giữa 2 lần AI nhắc nhở
# Tránh việc nhắc nhở liên tục gây phiền
REMINDER_COOLDOWN = 60


# ───────────────────────────────────────────────────────────────────
#  NHÓM 11: MULTI-PERSON TRACKING
# ───────────────────────────────────────────────────────────────────
# Chế độ theo dõi nhiều người trong cùng một khung hình.
# Mỗi người được đặt nhãn theo alphabet: A, B, C, D, E...
# (sắp xếp từ trái sang phải theo vị trí X trong frame)
#
# LƯU Ý KỸ THUẬT:
# - Dùng FaceMesh (max_num_faces=MAX_PERSONS) làm detector chính
# - Mỗi người có phiên (PersonSession) riêng với detector độc lập
# - Vùng body ước tính từ bounding box khuôn mặt (nhân hệ số)
# - Tracking giữa các frame dựa trên khoảng cách X gần nhất

# Bật/tắt chế độ nhiều người
# false = chế độ 1 người (mặc định, nhẹ hơn, dùng khi chỉ có 1 học sinh)
# true  = chế độ nhiều người (phát hiện và phân loại A/B/C...)
MULTI_PERSON_ENABLED = True

# Số người tối đa theo dõi đồng thời (A-E)
# Benchmark: FaceMesh max_faces=5 vẫn nhanh (~5ms), bottleneck là HandDetector
# Tăng nếu lớp đông. Giảm xuống 2-3 để tiết kiệm RAM và FaceMesh detection time
MAX_PERSONS = 2

# Số frame liên tiếp không detect được khuôn mặt trước khi xóa phiên
# (khác với ABSENCE_BUFFER_FRAMES — cái kia cho pose trong phiên,
#  cái này cho việc track-loss giữa các người)
# 30 FPS × 1.5 giây = 45 frame
PERSON_MISSING_FRAMES = 45

# Khoảng cách pixel tối đa giữa 2 frame để xem là cùng 1 người
# Dùng để match face giữa các frame liên tiếp (gán đúng nhãn A/B/C)
# Tăng nếu người hay di chuyển, giảm nếu nhiễu cross-assignment
PERSON_MATCH_DISTANCE = 150

# Hệ số mở rộng vùng body từ face bounding box
# Body ước tính = face bbox mở rộng xuống dưới và ra hai bên
# 3.0 = vùng body cao gấp 3 lần chiều cao khuôn mặt
PERSON_BODY_EXPAND_Y = 3.0   # Chiều dọc (xuống dưới)
PERSON_BODY_EXPAND_X = 1.5   # Chiều ngang (ra hai bên)


# ───────────────────────────────────────────────────────────────────
#  NHÓM 12: YOLO DETECTOR
# ───────────────────────────────────────────────────────────────────
# YOLO chạy trong background thread, detect người và vật thể.
# Benchmark RPi5: YOLO26n 320px ≈ 39ms/inference → background thread không ảnh hưởng main loop.

# Bật/tắt YOLO object detection
# false = chỉ dùng MediaPipe (nhẹ hơn), true = bật YOLO background thread
YOLO_ENABLED = True

# Đường dẫn model chính (COCO 80 lớp — phone, mouse, keyboard, person... đáng tin cậy hơn)
# yolo26n.pt = nano COCO (~5MB, khuyên dùng)
# yolo26s.pt = small COCO (chính xác hơn, ~20MB)
YOLO_MODEL_PATH = "yolo26n.pt"

# Model phụ cho pen/notepaper — Object365 365 lớp (~6MB)
# Chạy song song trong cùng background thread, chỉ detect các lớp YOLO_SECONDARY_CLASSES
# Đặt "" để tắt secondary model
YOLO_SECONDARY_MODEL_PATH = "yolo26n-objv1-150.pt"

# Kích thước ảnh đầu vào YOLO (pixel, hình vuông)
# 320 = nhanh ~80ms, 416 = cân bằng ~137ms, 640 = chính xác ~282ms
YOLO_INPUT_SIZE = 320

# Ngưỡng confidence tối thiểu (0.0-1.0)
# 0.35 = cân bằng giữa nhạy và ít false positive
YOLO_CONFIDENCE = 0.35

# Số frame bỏ qua giữa 2 lần inference trong background thread
# 2 = chạy 1 lần sau mỗi 3 frame → YOLO ≈ 3fps ở 10fps detection
# Tăng lên khi nhiệt độ cao (ThermalManager tự điều chỉnh)
YOLO_SKIP_FRAMES = 2

# Số frame tối đa dùng YOLO cached result cũ (khi YOLO chưa có kết quả mới)
YOLO_BBOX_MAX_STALE = 15

# COCO class IDs cần detect (primary model, verified từ COCO):
# person=0, bottle=39, cup=41, tv/monitor=62, laptop=63, mouse=64, keyboard=66,
# cell phone=67, book=73
YOLO_TARGET_CLASSES = [0, 39, 41, 62, 63, 64, 66, 67, 73]

# Object365 class IDs cho secondary model (pen/notepaper only, verified từ model.names):
# pen=51, notepaper=233
YOLO_SECONDARY_CLASSES = [51, 233]

# ── Tertiary model: Open Images V7 — pen detection chất lượng cao ────
# yolov8n-oiv7.pt (7.2 MB, 601 lớp) — OIV7 có class Pen riêng biệt (không
# merge với pencil như Object365), train trên ~9M annotations → chính xác hơn.
# Chạy cùng background thread với primary+secondary (tuần tự).
# Performance: +~40ms/inference, vẫn trong window 300ms (YOLO_SKIP_FRAMES=2).
# Đặt "" để tắt.
YOLO_TERTIARY_MODEL_PATH = "yolov8n-oiv7.pt"

# Open Images V7 class IDs cần detect (verified từ OIV7 label map):
# Pen=376, Book=54
# "pen" → tự merge với Object365 pen qua cls_name trong multi_person_tracker
# "book" → tự merge với COCO book, bổ sung thêm signal cho notebook detection
YOLO_TERTIARY_CLASSES = [376, 54]

# Input size riêng cho tertiary model: lớn hơn để detect vật nhỏ (bút ~2-3px ở 320px)
# 320px: bút ≈ 2-3px rộng → dưới ngưỡng YOLO. 416px: ≈ 3-4px → detect được.
# Benchmark RPi5: OIV7 ONNX tăng từ ~63ms → ~106ms (+43ms). Tổng ~226ms < 300ms window. OK.
YOLO_TERTIARY_INPUT_SIZE = 416

# Confidence threshold riêng cho tertiary (bút mỏng → thường score thấp hơn YOLO_CONFIDENCE)
# 0.25 → nhạy hơn với pen detection, combined với temporal smoothing để giảm false positive
YOLO_TERTIARY_CONFIDENCE = 0.25

# Confidence threshold riêng cho secondary (Object365 — pen/notepaper).
# Thấp hơn primary (0.35) vì bút là vật nhỏ, model ít confident hơn.
YOLO_SECONDARY_CONFIDENCE = 0.20

# IoU threshold cho Non-Maximum Suppression
YOLO_NMS_IOU = 0.45


# ───────────────────────────────────────────────────────────────────
#  NHÓM 13: THERMAL MANAGEMENT
# ───────────────────────────────────────────────────────────────────
# RPi5 trong robot enclosure kín có thể nóng. Giới hạn nhiệt độ CPU
# bằng cách giảm tần suất YOLO và thêm sleep vào main loop.
# Nhiệt độ đọc từ /sys/class/thermal/thermal_zone0/temp (sysfs).

# Nhiệt độ (°C) bắt đầu tăng YOLO skip nhẹ
THERMAL_WARN_TEMP = 75.0

# Nhiệt độ (°C) throttle mạnh: tăng skip nhiều + thêm sleep main loop
THERMAL_HIGH_TEMP = 82.0

# Nhiệt độ (°C) tắt YOLO hoàn toàn để bảo vệ phần cứng
THERMAL_CRITICAL_TEMP = 88.0

# Số frame thêm vào YOLO_SKIP_FRAMES khi WARN (75-82°C)
THERMAL_WARN_EXTRA_SKIP = 2

# Số frame thêm vào YOLO_SKIP_FRAMES khi HIGH (82-88°C)
THERMAL_HIGH_EXTRA_SKIP = 5

# Sleep thêm (giây) vào main loop khi nhiệt độ HIGH
THERMAL_HIGH_EXTRA_SLEEP = 0.015

# Chu kỳ đọc nhiệt độ (frame). 30 frame ≈ 3 giây ở 10fps
THERMAL_READ_INTERVAL = 30


# ───────────────────────────────────────────────────────────────────
#  NHÓM 15: ACTIVITY STATES — MÃ TRẠNG THÁI & VĂN BẢN HIỂN THỊ
# ───────────────────────────────────────────────────────────────────
#
# Tách thành 2 phần:
#   A. Activity codes   — mã nội bộ, dùng trong logic/database/API
#   B. Status strings   — văn bản hiển thị, có thể điều chỉnh tự do
#      (strings có {biến} là format template, dùng .format() khi render)
#
# Để thêm trạng thái mới:
#   1. Thêm ACTIVITY_* và STATUS_* ở đây
#   2. Thêm logic điều kiện trong activity_analyzer.py::_determine_raw_activity()
#   3. Cập nhật docs/business/activity-states.md
# ───────────────────────────────────────────────────────────────────

# ── A. Activity codes (không thay đổi — dùng làm key trong log/API) ─

ACTIVITY_WORKING_COMPUTER  = "working_computer"   # Làm việc tích cực trên máy tính
ACTIVITY_FOCUSED_STUDYING  = "focused_studying"   # Tập trung học (gesture + màn hình)
ACTIVITY_WRITING_NOTES     = "writing_notes"      # Viết tay / Ghi chép
ACTIVITY_READING           = "reading"            # Đọc sách / tài liệu giấy
ACTIVITY_WATCHING_SCREEN   = "watching_screen"    # Nhìn màn hình, chưa tương tác
ACTIVITY_USING_PHONE       = "using_phone"        # Đang dùng điện thoại
ACTIVITY_DISTRACTED        = "distracted"         # Mất tập trung kéo dài
ACTIVITY_DROWSY            = "drowsy"             # Buồn ngủ / Mệt mỏi
ACTIVITY_TALKING           = "talking"            # Đang nói chuyện
ACTIVITY_EATING_DRINKING   = "eating_drinking"    # Đang ăn/uống
ACTIVITY_PLAYING           = "playing"            # Đang chơi đùa
ACTIVITY_SLEEPING          = "sleeping"           # Đang ngủ gật
ACTIVITY_PRESENT           = "present"            # Có mặt, chưa xác định rõ
ACTIVITY_BRIEFLY_AWAY      = "briefly_away"       # Rời chỗ tạm thời (< 5 phút)
ACTIVITY_ABSENT            = "absent"             # Vắng mặt chính thức (≥ 5 phút)

# ── B. Status strings tĩnh (thay đổi văn bản tại đây, không cần sửa logic) ──

STATUS_WORKING_COMPUTER    = "💻 Đang làm việc / Làm bài tập"
STATUS_FOCUSED_STUDYING    = "📚 Tập trung học / Làm việc (màn hình)"
STATUS_WRITING_NOTES       = "✍️  Đang viết / Ghi chép"
STATUS_READING             = "📖 Đang đọc sách / tài liệu"
STATUS_WATCHING_SCREEN     = "🖥️  Đang xem màn hình / Suy nghĩ"
STATUS_USING_PHONE         = "📱 Đang dùng điện thoại"
STATUS_FMT_USING_PHONE     = "📱 Đang dùng điện thoại ({duration})"
# {duration}: chuỗi thời gian đã dùng, ví dụ "30 giây", "2 phút", "1 phút 30s"
STATUS_DROWSY              = "😴 Có vẻ buồn ngủ / Mệt mỏi"
STATUS_TALKING             = "💬 Đang nói chuyện"
STATUS_EATING_DRINKING     = "🥤 Đang ăn/uống"
STATUS_PLAYING             = "🎭 Đang chơi đùa"
STATUS_DROWSY_MILD         = "😪 Có dấu hiệu mệt mỏi"
STATUS_DROWSY_MODERATE     = "😴 Buồn ngủ"
STATUS_PRESENT             = "✅ Đang ngồi tại vị trí"
STATUS_LOOKING_AROUND      = "👀 Đang nhìn quanh..."

# ── B. Status format strings động (dùng .format() với biến khi render) ──
# Biến khả dụng ghi chú trong ngoặc

STATUS_FMT_DISTRACTED      = "😵 Mất tập trung {seconds}s — Nhìn sang {direction}"
# {seconds}: số giây mất tập trung, {direction}: trái/phải/trên

STATUS_FMT_DISTRACTED_SHORT = "😵 Đang nhìn sang nơi khác ({seconds}s)"
# {seconds}: số giây nhìn sang nơi khác

STATUS_FMT_ABSENT          = "❌ Vắng mặt {mins} phút {secs}s — quá {threshold} phút"
# {mins}: phút, {secs}: giây, {threshold}: ngưỡng vắng mặt (phút)

STATUS_FMT_BRIEFLY_AWAY_MED   = "🚶 Rời chỗ ngắn {mins:02d}:{secs:02d} (ngưỡng: {threshold} phút)"
# {mins}: phút, {secs}: giây, {threshold}: ABSENCE_LONG_THRESHOLD // 60

STATUS_FMT_BRIEFLY_AWAY_SHORT = "⚠️ Rời khỏi vị trí {secs}s"
# {secs}: số giây vắng mặt

STATUS_FMT_SLEEPING        = "😴 Đang ngủ gật ({seconds}s)"
# {seconds}: số giây ngủ gật


# ───────────────────────────────────────────────────────────────────
#  NHÓM 14: POSE-BASED GAZE (thay FaceMesh cho camera đặt bên cạnh)
# ───────────────────────────────────────────────────────────────────
# Khi camera đặt bên cạnh, mặt người nghiêng 60-90° → FaceMesh thất bại.
# Dùng MediaPipe Pose (nose + shoulder landmarks) để tính hướng nhìn.
# Pose hoạt động tốt với profile view.

# Vị trí camera so với người ngồi
# "right" = camera bên PHẢI người (người nhìn sang trái trong frame)
# "left"  = camera bên TRÁI  người (người nhìn sang phải trong frame)
# "front" = camera phía trước (FaceMesh hiệu quả hơn ở góc này)
CAMERA_SIDE = "right"

# Hệ số scale góc pitch từ Pose → điều chỉnh theo môi trường thực tế
# Nếu detect "looking_down" quá nhạy → giảm xuống 1.2-1.5
# Nếu không nhạy đủ → tăng lên 2.0-2.5
POSE_PITCH_SCALE = 1.8

# Hệ số scale góc yaw từ Pose
POSE_YAW_SCALE = 2.0

# Số frame tối đa dùng Pose cached result (round-robin: 3 người = mỗi người được update mỗi 3 frame)
# 6 = cho phép dùng 2 vòng round-robin trước khi coi là stale
MAX_POSE_CACHE_FRAMES = 6

# Kích thước crop tối thiểu (pixel) để chạy Pose trên person bbox
# Crop nhỏ hơn → Pose không chính xác, bỏ qua
MIN_POSE_CROP_H = 80
MIN_POSE_CROP_W = 40


# ───────────────────────────────────────────────────────────────────
#  NHÓM 16: DROWSINESS DETECTION
# ───────────────────────────────────────────────────────────────────
# Phát hiện buồn ngủ / ngủ gật qua nhiều tín hiệu khuôn mặt + đầu.
# Dùng blendshapes từ MediaPipe Face Landmarker (eyeBlinkL/R, jawOpen).

# Ngưỡng avg(eyeBlinkL, eyeBlinkR) để coi là nhắm mắt
DROWSY_EYE_CLOSURE_THRESHOLD = 0.65

# Giây nhắm mắt liên tục → buồn ngủ
DROWSY_EYE_CLOSURE_DURATION  = 2.0

# Ngưỡng jawOpen cho ngáp (cao hơn talking 0.20)
DROWSY_YAWN_THRESHOLD        = 0.50

# Giây miệng mở rộng liên tục → ngáp
DROWSY_YAWN_DURATION         = 1.5

# Chớp mắt/phút → dấu hiệu mệt
DROWSY_BLINK_RATE_HIGH       = 25      # blinks/min (bình thường 15-20, mệt >25)

# Giây nghiêng đầu liên tục → buồn ngủ
DROWSY_HEAD_TILT_DURATION    = 3.0

# Độ pitch thấp → đầu gật xuống
DROWSY_HEAD_NOD_PITCH        = -25

# Số lần gật trong window → buồn ngủ
DROWSY_HEAD_NOD_COUNT        = 3

# Giây theo dõi head nod
DROWSY_HEAD_NOD_WINDOW       = 30

# Độ pitch rất thấp → gục đầu (cúi làm việc ≈ -20° đến -35°, ngủ gật thật ≈ -45°+)
DROWSY_HEAD_DROP_PITCH       = -40

# Giây gục đầu liên tục → đang ngủ (tăng từ 5s lên 8s để giảm false positive)
DROWSY_HEAD_DROP_DURATION    = 8.0

# Chỉ hiện status "ngủ gật" khi đã ngủ >= Ns (tránh log từ 0s)
DROWSY_SLEEPING_LOG_MIN      = 5.0


# ───────────────────────────────────────────────────────────────────
#  NHÓM 18: HOMEWORK MONITORING
# ───────────────────────────────────────────────────────────────────
# Phát hiện học sinh làm bài tập và hỏi xem bài.
#
# Flow:
#   [Làm bài >= 30s] → Hỏi "Cho thầy xem bài?" → Đợi 20s
#   [Thấy vở rõ]    → Chụp ảnh → Hiện nút "Phân tích AI"
#   [User bấm nút]  → Gửi AI → Hiện kết quả → Cooldown 120s
#

# Số giây liên tục làm bài tập trước khi hỏi xem bài
# Tăng lên (60s) nếu muốn chắc chắn hơn trước khi hỏi
# Giảm xuống (15s) nếu muốn phát hiện nhanh hơn
HOMEWORK_DETECT_DURATION = 30

# Số giây đợi học sinh cho xem bài sau khi hỏi
# Sau timeout → bỏ qua, tiếp tục tracking
HOMEWORK_REQUEST_TIMEOUT = 20

# Số giây cooldown sau khi đã phân tích bài xong
# Tránh hỏi liên tục sau mỗi lần xem bài
HOMEWORK_COOLDOWN = 120

# Ngưỡng confidence tối thiểu của YOLO khi detect sách/vở
# Phải đạt ngưỡng này mới tính là "thấy rõ bài tập"
HOMEWORK_BOOK_MIN_CONF = 0.45

# Tỷ lệ diện tích tối thiểu sách/vở so với frame (0.0-1.0)
# 0.04 = sách/vở phải chiếm ít nhất 4% frame
# Tăng lên nếu muốn đảm bảo ảnh chụp đủ rõ chữ
HOMEWORK_BOOK_MIN_AREA = 0.04

# Thông điệp hiển thị khi yêu cầu học sinh cho xem bài
HOMEWORK_REQUEST_MSG = "Bạn đang làm bài tập phải không? Cho thầy xem bài với nhé! 📖"

# Số frame homework_visible=True liên tiếp trước khi auto-capture (~3s @ 10fps)
HOMEWORK_AUTO_CAPTURE_FRAMES = 30

# Số lần thử lại khi ảnh không đạt chất lượng (auto-capture)
# Sau max retries → chụp dù chất lượng không tốt
HOMEWORK_QUALITY_RETRIES = 3


# ───────────────────────────────────────────────────────────────────
#  NHÓM 19: IMAGE QUALITY — ĐÁNH GIÁ CHẤT LƯỢNG ẢNH
# ───────────────────────────────────────────────────────────────────
# Ngưỡng chất lượng ảnh trước khi gửi AI phân tích.
# Dùng bởi assess_image_quality() trong utils/image_utils.py.

# Laplacian variance tối thiểu — ảnh sắc nét
# 80.0 = nét vừa phải (ảnh bàn học thường 100-800, phòng tối ~30-60)
# Giảm xuống 30 nếu ảnh hay bị reject do ánh sáng yếu
IMAGE_QUALITY_MIN_BLUR_SCORE = 80.0

# Tỷ lệ diện tích ROI tối thiểu (0.0-1.0)
# 0.08 = sách/vở phải chiếm ít nhất 8% frame
# Giảm xuống 0.04 nếu sách nhỏ hoặc camera đặt xa
IMAGE_QUALITY_MIN_COVERAGE = 0.08

# Độ sáng tối thiểu (0-255) — tránh ảnh quá tối
IMAGE_QUALITY_MIN_BRIGHTNESS = 40

# Độ sáng tối đa (0-255) — tránh ảnh overexposed
IMAGE_QUALITY_MAX_BRIGHTNESS = 220

# Chất lượng JPEG cho stream MJPEG / ảnh thường (1-100)
# 85 = cân bằng tốt giữa chất lượng và tốc độ encode
JPEG_QUALITY = 85

# Chất lượng JPEG cho snapshot gửi AI (cao hơn để AI đọc rõ chữ)
# 95 = gần lossless, rõ chữ hơn (file ~300KB vs ~80KB ở quality=85)
SNAPSHOT_JPEG_QUALITY = 95


# ───────────────────────────────────────────────────────────────────
#  NHÓM 20: YOLO — ONNX RUNTIME
# ───────────────────────────────────────────────────────────────────
# ONNX Runtime tăng tốc YOLO inference ~2.75× so với PyTorch.
# Benchmark RPi5: PyTorch .pt ~110ms → ONNX ~40ms/inference.
#
# Để xuất ONNX: cd /home/pi/ai-tutor && python3 scripts/export_onnx.py
# Sau khi xuất, file .onnx nằm cạnh .pt → YOLO_PREFER_ONNX tự dùng.

# Ưu tiên dùng .onnx nếu tồn tại bên cạnh .pt
# True  = dùng ONNX (~40ms) nếu .onnx tồn tại, fallback về .pt nếu không
# False = luôn dùng .pt (~110ms), không cần export trước
YOLO_PREFER_ONNX = True


# ───────────────────────────────────────────────────────────────────
#  NHÓM 21: CONFIDENCE SCORING — WEIGHTED MULTI-SIGNAL
# ───────────────────────────────────────────────────────────────────
# Ngưỡng điểm tối thiểu của mỗi classifier để được chọn là activity.
# Điểm 0-100 từ mỗi ActivityClassifier; hoạt động có điểm cao nhất
# và vượt ngưỡng tương ứng sẽ được chọn.
# Override qua .env để tinh chỉnh không cần sửa code.

# Ngưỡng tối thiểu chung (nếu không có ngưỡng riêng)
CONFIDENCE_MIN_CLASSIFY       = 30

# Ngưỡng từng activity
CONFIDENCE_WRITING_THRESHOLD  = 50   # Cần nhiều tín hiệu để tránh false positive
CONFIDENCE_READING_THRESHOLD  = 40
CONFIDENCE_COMPUTER_THRESHOLD = 45
CONFIDENCE_PHONE_THRESHOLD    = 40   # Raw score → feed vào temporal filter
                                      # Giảm 45→40: đủ buffer khi phone_in_hand=False
                                      # (YOLO phone + zone + gaze = ~40, temporal filter bảo vệ false positive)
CONFIDENCE_FOCUSED_THRESHOLD  = 45
CONFIDENCE_WATCHING_THRESHOLD = 40
CONFIDENCE_TALKING_THRESHOLD  = 40
CONFIDENCE_EATING_THRESHOLD   = 40
CONFIDENCE_PLAYING_THRESHOLD  = 40
CONFIDENCE_DISTRACTED_THRESHOLD = 30

# Bài tập visible: writing_score đủ cao + có sách/vở → chụp hình
HOMEWORK_WRITING_MIN_SCORE    = 60   # Writing classifier >= này + book/notepaper → homework_visible


# ───────────────────────────────────────────────────────────────────
#  NHÓM 17: NEW ACTIVITY THRESHOLDS
# ───────────────────────────────────────────────────────────────────
# Ngưỡng thời gian và tốc độ cho các activity mới (talking, playing, phone).

# Frame liên tục để confirm talking (2s ở 10fps)
TALKING_MIN_FRAMES       = 20

# Frame liên tục để confirm playing (2.5s)
PLAYING_MIN_FRAMES       = 25

# Tốc độ tay tối thiểu (px/frame) cho playing
PLAYING_MIN_HAND_SPEED   = 15

# Frame liên tục để confirm phone (~4 giây ở 9fps; decrement -3 → clear sau ~12 frame)
PHONE_MIN_SUSTAINED_FRAMES = 36

# Khoảng thời gian (giây) giữa các mốc log/cảnh báo thời gian dùng phone
# Ví dụ: 30 → log tại 30s, 60s, 90s, ... (có thể override qua .env)
PHONE_DURATION_LOG_INTERVAL = 30

# Frame liên tục để confirm eating/drinking (1s ở 10fps)
# Cần sustained để tránh bottle trên bàn gây false positive
EATING_MIN_FRAMES = 10

# Tốc độ tay TỐI THIỂU (px/frame) để tính là đang ăn/uống.
# Khi uống nước: tay đưa ly lên → tay phải di chuyển.
# Cup đứng yên trên bàn + tay đứng yên → KHÔNG phải đang uống.
# Tăng lên nếu vẫn còn false positive; giảm xuống 1 nếu quá chặt.
EATING_MIN_HAND_SPEED = 3

# Ngưỡng vị trí dọc của cup/bottle trong person bbox (0.0 = đỉnh đầu, 1.0 = cuối bbox).
# Cup phải nằm trong phần trên của person bbox mới tính là "đang cầm".
# Cup ở dưới ngưỡng này → còn đang để trên bàn, chưa cầm.
# 0.75 = cup phải trong 75% phần trên của person height.
EATING_CUP_MAX_Y_RATIO = 0.75

# Focus score cho activity mới
SCORE_PENALTY_TALKING    = -10    # Nói chuyện (nhẹ)
SCORE_PENALTY_PLAYING    = -25    # Chơi đùa (nặng)
SCORE_EATING             = 5      # Ăn/uống (trung tính)
SCORE_SLEEPING           = 0      # Ngủ gật (không điểm)


# ───────────────────────────────────────────────────────────────────
#  NHÓM 22: TTS / ALERT SERVICE
# ───────────────────────────────────────────────────────────────────
# Bật/tắt toàn bộ TTS. False nếu không có speaker hoặc chạy headless.
TTS_ENABLED           = True

# Tốc độ đọc espeak-ng (từ/phút). 140 = rõ ràng, tự nhiên.
# Khoảng hợp lệ: 80 (chậm) → 300 (rất nhanh).
TTS_SPEED             = 140

# Giọng đọc espeak-ng. 'vi' = tiếng Việt.
TTS_VOICE             = "vi"

# Giây giữa 2 lần alert phone liên tiếp (tránh spam).
TTS_PHONE_ALERT_DELAY    = 30

# Giây giữa 2 lần alert distracted liên tiếp.
TTS_DISTRACT_ALERT_DELAY = 20


# ───────────────────────────────────────────────────────────────────
#  NHÓM 23: IMX500 AI CAMERA (Sony IMX500 12.3MP)
# ───────────────────────────────────────────────────────────────────
# Bật chế độ IMX500 — camera chạy YOLO primary trực tiếp trên chip.
# Giải phóng ~40ms CPU cho primary YOLO, tổng pipeline ~100ms thay vì 143ms.
# Yêu cầu: sudo apt install imx500-all + export model (xem scripts/export_imx500.py)
CAMERA_IMX500_ENABLED    = False

# Đường dẫn file .rpk (neural network firmware cho IMX500)
# Tạo bằng: python3 scripts/export_imx500.py
YOLO_IMX500_MODEL_PATH   = "models/yolov8n_imx500.rpk"

# Confidence threshold cho IMX500 inference (INT8 quantization → có thể cần điều chỉnh)
# Thấp hơn YOLO_CONFIDENCE (0.35) nếu INT8 làm giảm score confidence
YOLO_IMX500_CONF         = 0.25   # INT8 quantized → scores thấp hơn FP32, dùng 0.25

# IoU threshold cho NMS của IMX500 postprocessing
YOLO_IMX500_IOU          = 0.65

# Số detection tối đa từ IMX500 mỗi frame
YOLO_IMX500_MAX_DETS     = 10

# Input size dùng khi export model (phải khớp với --imgsz khi export)
# Dùng để normalize box coords từ pixel → [0,1] trước convert_inference_coords
YOLO_IMX500_INPUT_SIZE   = 320

# Snapshot resolution tối đa IMX500 (12.3MP = 4056×3040)
# IMX219 (Camera v2.1) tối đa 3280×2464 (8MP)
# Override trong .env: SNAPSHOT_WIDTH=4056, SNAPSHOT_HEIGHT=3040
SNAPSHOT_IMX500_WIDTH    = 4056
SNAPSHOT_IMX500_HEIGHT   = 3040
