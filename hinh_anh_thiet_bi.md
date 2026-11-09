# BỘ ẢNH THỰC TẾ & HƯỚNG DẪN NHẬN DIỆN PHẦN CỨNG DỰ ÁN

> [!NOTE]
> Toàn bộ ảnh bên dưới là **ảnh chụp cận cảnh thực tế** của các linh kiện phần cứng được sử dụng trong đề tài Robot Học Tập. Hãy xem kỹ từng bộ phận để khi nhận thiết bị từ Thầy không bị bỡ ngỡ và cắm nhầm dây nhé!

---

## 1. Bo Mạch Raspberry Pi 5 (Thân máy Robot)

Đây là "bộ não" trung tâm xử lý cục bộ toàn bộ thuật toán AI (MediaPipe Pose, FaceMesh, cắt trang, Cổng riêng tư).

![Bo mạch Raspberry Pi 5 nhìn từ trên xuống](/home/nguyenquoc/.gemini/antigravity/brain/2a8299d9-63dd-4a52-8a9e-78bdd6cbabab/hardware_img/raspberry_pi_5_thumb.jpg)

### Các vị trí quan trọng trên bo mạch cần nhớ:
1. **CAM/DISP 0 và CAM/DISP 1 (Gần cổng Ethernet & Cổng âm thanh cũ):** Đây là 2 cổng dẹp nhỏ để cắm cáp camera. Trên Pi 5, cả 2 cổng này đều hỗ trợ cắm camera!
2. **Cổng USB-C (Góc dưới bên trái):** Cổng cắm nguồn điện (yêu cầu nguồn chuẩn 27W).
3. **Nút nguồn (Power button - cạnh cổng USB-C):** Pi 5 lần đầu tiên có nút nguồn cứng để bật/tắt an toàn.
4. **Khe cắm quạt FAN (4 chân nhỏ màu trắng):** Dùng để cắm giắc cắm quạt Active Cooler.
5. **2 lỗ có vòng kim loại chéo góc chip CPU:** Dùng để ấn 2 chân lò xo cố định cụm tản nhiệt.
6. **Mặt dưới bo mạch:** Có khe cắm thẻ nhớ microSD.

![Góc nhìn nghiêng các cổng kết nối của Raspberry Pi 5](/home/nguyenquoc/.gemini/antigravity/brain/2a8299d9-63dd-4a52-8a9e-78bdd6cbabab/hardware_img/raspberry_pi_5_side_thumb.jpg)

---

## 2. Quạt Tản Nhiệt Active Cooler (Lắp trên lưng Pi 5)

Khi Pi 5 chạy mô hình AI nhận diện khung xương, chip CPU sẽ rất nóng. **Active Cooler** gồm 1 phiến nhôm tản nhiệt nguyên khối gắn quạt thông minh (tự động điều tốc).

![Raspberry Pi 5 khi đã lắp hoàn chỉnh Active Cooler](/home/nguyenquoc/.gemini/antigravity/brain/2a8299d9-63dd-4a52-8a9e-78bdd6cbabab/hardware_img/pi5_active_cooler_thumb.jpg)

### Cách lắp đặt Active Cooler:
- Bóc miếng nilon bảo vệ trên 3 miếng dán tản nhiệt màu xám (thermal pad) ở mặt đáy tản nhiệt.
- Đặt cụm tản nhiệt ốp khít lên lưng chip CPU và chip quản lý nguồn.
- Ấn nhẹ 2 chốt lò xo nhựa màu trắng vào 2 lỗ trên bo mạch cho đến khi nghe tiếng "tách" (chốt khóa chặt).
- Cắm giắc cắm quạt vào cổng 4-pin FAN trên bo mạch.

---

## 3. Cáp Camera Chuyên Dụng Cho Pi 5 (FPC 22-pin Pitch 0.5mm)

> [!WARNING]
> **ĐIỂM DỄ CẮM SAI NHẤT:** Cổng camera trên Pi 5 là chuẩn **22 chân siêu nhỏ (pitch 0.5mm)**, KHÔNG PHẢI chuẩn 15 chân của Pi 4/Pi 3. Cáp camera cho Pi 5 có 1 đầu nhỏ 22-pin cắm vào bo mạch Pi 5, và 1 đầu 22-pin hoặc 15-pin cắm vào mắt camera.

![Cáp dẹp kết nối Camera cho Raspberry Pi 5](/home/nguyenquoc/.gemini/antigravity/brain/2a8299d9-63dd-4a52-8a9e-78bdd6cbabab/hardware_img/pi5_camera_cable_thumb.jpg)

---

## 4. Mắt Camera & Mô Hình Kết Nối Thực Tế

Đây là mắt camera nhỏ xíu (sử dụng cảm biến Sony IMX708 12MP có Autofocus) được kết nối với Pi 5 thông qua sợi cáp dẹp.

![Mắt Camera Raspberry Pi và cách kết nối cáp](/home/nguyenquoc/.gemini/antigravity/brain/2a8299d9-63dd-4a52-8a9e-78bdd6cbabab/hardware_img/pi_ai_camera_thumb.jpg)

### Hình ảnh toàn bộ hệ thống khi kết nối hoạt động:
Cáp dẹp được cắm thẳng từ cổng camera của Pi 5 dẫn ra mắt camera đặt trên bàn học:

![Toàn cảnh Raspberry Pi kết nối với Camera qua cáp dẹp](/home/nguyenquoc/.gemini/antigravity/brain/2a8299d9-63dd-4a52-8a9e-78bdd6cbabab/hardware_img/pi_with_camera_thumb.jpg)

---

## 5. Củ Nguồn USB-C 27W & Thẻ Nhớ microSD

```
 ┌──────────────────────────────────────┐        ┌─────────────────────────┐
 │   CỦ NGUỒN CHUẨN 27W USB-C           │        │   THẺ NHỚ microSD       │
 │   • Điện áp: 5.1V - 5.0A             │        │   • Chuẩn: A2 / V30     │
 │   • Đầu cắm: USB Type-C              │        │   • Dung lượng: ≥ 32GB  │
 │   • Tác dụng: Cấp đủ dòng khi tải AI │        │   • Cài HĐH Pi OS 64-bit│
 └──────────────────────────────────────┘        └─────────────────────────┘
```

---

## 6. Sơ Đồ Đặt Vị Trí Camera Trên Bàn Học (Khảo sát Tuần 1)

```
                     [ MẮT CAMERA ]
                  (Gắn cao 30-35cm, chếch 35°)
                       /           \
                      /             \
                     /  FOV = 75°    \
                    /                 \
                   v                   v
           [ VÙNG ĐẦU & VAI ]    [ TRANG VỞ HỌC SINH ]
           (Đo góc gập cổ,       (Cắt trang, kiểm tra da tay
            đo độ nghiêng vai)    gửi AI đọc đề bài)
```

> [!TIP]
> Bạn có thể mở trực tiếp các file ảnh này trong thư mục `RobotHocTap/hardware_img/` trên máy tính để zoom to xem chi tiết từng linh kiện nhé!
