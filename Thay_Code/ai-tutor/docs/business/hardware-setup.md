# Hướng dẫn lắp đặt phần cứng & vị trí camera

## Phần cứng cần thiết

| Thiết bị | Model | Ghi chú |
|---|---|---|
| Board | Raspberry Pi 5 (4GB/8GB) | 8GB khuyến nghị |
| Camera | Raspberry Pi Camera Module v2.1 (IMX219) | Kết nối qua CSI ribbon cable |
| Cable camera | Official RPi Camera Cable (15-pin) | Không dùng cable bên thứ 3 |
| Nguồn | Official RPi 5 Power Supply (5V/5A USB-C) | Nguồn yếu → camera không ổn định |
| Storage | microSD 32GB+ Class 10 / A1 | Hoặc NVMe SSD qua PCIe |
| Case | Tùy chọn | Nên có tản nhiệt / quạt RPi5 |
| Mount camera | Giá đỡ camera / tripod mini | Giữ camera cố định, không rung |

---

## Vị trí đặt camera — Nguyên tắc chung

### Khoảng cách
```
Khoảng cách lý tưởng: 60–120 cm tính từ học sinh
        ┌──────────┐
        │  Camera  │
        └────┬─────┘
             │ 60–120 cm
             ▼
        ┌──────────┐
        │ Học sinh │
        └──────────┘
```
- **Quá gần (< 50cm)**: Frame bị crop, không thấy toàn bộ người
- **Quá xa (> 150cm)**: MediaPipe khó detect khuôn mặt và tư thế
- **Tối ưu**: 80–100 cm

### Góc đặt camera
```
          ✅ Lý tưởng          ⚠️ Chấp nhận được
     Camera ngang tầm mắt    Camera hơi cao (15-30°)
          ┌───┐
          │cam│ ← ngang mặt           [cam]
          └─┬─┘                         \ 30°
            │                            \
        [học sinh]                    [học sinh]
```
- **Ngang tầm mắt**: Góc pitch/yaw chính xác nhất
- **Camera cao hơn (15–30°)**: Chấp nhận được, cần điều chỉnh `GAZE_PITCH_DOWN` xuống -20
- **Camera thấp hơn mặt**: Không khuyến nghị (pitch tự nhiên sẽ cao)

### Ánh sáng
- **Tốt nhất**: Ánh sáng tự nhiên từ phía trước hoặc trên
- **Tránh**: Ánh sáng mạnh từ phía sau học sinh (backlight) → khuôn mặt tối
- **Tránh**: Ánh đèn nhấp nháy → ảnh hưởng motion detector
- **Khuyến nghị**: Đèn LED trần phòng, ánh sáng đều

---

## Cấu hình cho các kịch bản phòng học

### Kịch bản A: 1 học sinh, camera phía trước

```
     [Camera trên màn hình hoặc giá đỡ]
               │
               │ 80–100 cm
               │
         [Học sinh]
         [  Bàn   ]
         [Máy tính]
```

**Cấu hình:**
```bash
ROI_ENABLED=false
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
```

**Điều chỉnh gaze nếu camera đặt trên màn hình (cao hơn mặt ~20cm):**
```bash
GAZE_PITCH_DOWN=-20   # Tăng ngưỡng cúi đầu
GAZE_PITCH_UP=25      # Tăng ngưỡng ngửa đầu
```

---

### Kịch bản B: Nhiều học sinh cùng hàng, 1 camera

```
[Camera ở đầu bàn, nhìn dọc hàng]
        │
        │ 80 cm
        │
  [HS1][HS2][HS3][HS4]
  [bàn bàn bàn bàn]
```

**Vấn đề**: Camera thấy cả 4 học sinh → MediaPipe detect nhầm người.

**Giải pháp 1: 1 camera / 1 học sinh** (tốt nhất)
- Mỗi vị trí ngồi có camera riêng trên màn hình
- Không cần ROI

**Giải pháp 2: ROI crop** (khi dùng 1 camera nhìn thẳng vào 1 học sinh cụ thể)
```bash
ROI_ENABLED=true
ROI_X1=0.15   # Cắt bớt hai bên
ROI_X2=0.85
```

**Tăng buffer để tránh false positive:**
```bash
ABSENCE_BUFFER_FRAMES=60   # Buffer 2 giây thay vì 1.5 giây
```

---

### Kịch bản C: Camera gắn trên trần/cao (giám sát phòng)

```
        [Camera trên trần]
              /
             / ~120-150cm, góc 45°
            /
      [Học sinh nhìn xuống bàn]
```

**Lưu ý:**
- MediaPipe Pose hoạt động tốt ở góc nhìn từ trên
- GazeDetector sẽ kém chính xác hơn (mặt không hướng về camera)
- Chỉ nên dùng cho phát hiện có mặt/vắng mặt, không nên dùng gaze detection

**Cấu hình:**
```bash
GAZE_PITCH_DOWN=-30   # Camera cao → học sinh hay "nhìn xuống" về hướng camera
GAZE_YAW_THRESHOLD=30  # Góc yaw ít chính xác hơn từ trên cao
```

---

## Cài đặt camera trên Raspberry Pi OS

### Bước 1: Kết nối phần cứng
1. Tắt nguồn RPi5
2. Mở khóa connector CSI (nhấn nhẹ lên tab nhựa)
3. Cắm ribbon cable (mặt tiếp điểm hướng vào board)
4. Khóa lại connector
5. Bật nguồn

### Bước 2: Kiểm tra camera nhận diện
```bash
# Liệt kê camera devices
libcamera-hello --list-cameras

# Test capture ảnh
libcamera-jpeg -o test.jpg

# Hoặc kiểm tra qua picamera2
python3 -c "from picamera2 import Picamera2; cam = Picamera2(); print(cam.camera_properties)"
```

### Bước 3: Cài đặt dependencies
```bash
cd /home/pi/ai-tutor
pip install -r requirements.txt

# MediaPipe (cài thêm nếu chưa có)
pip install mediapipe

# Kiểm tra mediapipe
python3 -c "import mediapipe; print('MediaPipe OK:', mediapipe.__version__)"
```

### Bước 4: Khởi động hệ thống
```bash
cd /home/pi/ai-tutor
python3 main.py
```

Truy cập dashboard: `http://<địa-chỉ-IP-RPi>:5000`

Tìm IP của RPi:
```bash
hostname -I
```

---

## Hiệu chỉnh (Calibration) sau khi lắp đặt

### 1. Kiểm tra gaze detection
Mở dashboard, quan sát mũi tên hướng nhìn:
- Nhìn thẳng vào camera → mũi tên chỉ thẳng → nếu không, điều chỉnh `GAZE_PITCH_UP/DOWN`
- Nhìn xuống bàn → phải hiện `looking_down` → nếu không, giảm `GAZE_PITCH_DOWN` xuống -20

### 2. Kiểm tra hand zone
Quan sát đường phân vùng trên stream:
- Đặt tay trên bàn phím → phải hiện `VUNG BAN/BAN PHIM`
- Nếu tay bàn phím bị nhận là `middle` → giảm `HAND_ZONE_BOTTOM_RATIO` xuống 0.55

### 3. Kiểm tra ROI (nếu bật)
- Vùng được phân tích hiện viền vàng trên stream
- Điều chỉnh `ROI_X1/X2` sao cho vùng vàng bao trọn học sinh cần giám sát
- Không bao gồm học sinh bên cạnh

### 4. Test absence detection
- Rời khỏi vị trí 10 giây → phải hiện "Rời khỏi vị trí Xs"
- Rời 70 giây → phải hiện "Rời chỗ ngắn 01:10"
- Rời 310 giây → phải hiện "Vắng mặt 5 phút..."

---

## Troubleshooting phổ biến

### Camera không nhận
```bash
# Kiểm tra service camera
sudo systemctl status picamera2

# Reload config
sudo raspi-config  # → Interface Options → Camera → Enable
sudo reboot
```

### Hay bị "vắng mặt" ảo khi người vẫn ngồi
- Tăng `ABSENCE_BUFFER_FRAMES` lên 60–90
- Bật ROI để loại bỏ nhiễu từ người xung quanh
- Kiểm tra ánh sáng (backlight làm khó detect)

### Gaze detection không chính xác
- Điều chỉnh `GAZE_PITCH_DOWN` và `GAZE_PITCH_UP` theo vị trí camera
- Đảm bảo ánh sáng đủ sáng để thấy khuôn mặt rõ

### FPS thấp (< 10 FPS)
```bash
# Giảm độ phân giải
CAMERA_WIDTH=960
CAMERA_HEIGHT=540

# Giảm FPS target
CAMERA_FPS=15

# Tắt phone detection nếu không cần
PHONE_DETECTION_ENABLED=false
```

### Phone detection sai (hay nhận nhầm)
- Tăng `PHONE_SCORE_THRESHOLD` lên 65
- Tắt hoàn toàn: `PHONE_DETECTION_ENABLED=false`
