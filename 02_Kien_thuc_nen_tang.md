# 02. Kiến thức nền tảng (đã nghiên cứu)

Các số liệu giá/spec lấy tháng 10/2026; kiểm tra lại trước khi mua thêm.

## 1. Phần cứng
- **Raspberry Pi 5**: board 85 x 58 mm, có 2 cổng camera CSI (CAM0/CAM1, đầu nối 22 chân 0.5mm; cáp cho Pi 4/3 cần adapter). Có các bản RAM 1/2/4/8/16GB. Với pipeline này nên dùng >= 4GB.
- **AI HAT+ (Hailo)**: tùy chọn, 13-26 TOPS, giúp chạy pose/detection real-time. Chưa dùng ở giai đoạn này.
- **Pi Camera Module 3** (IMX708, 12MP): autofocus theo pha (PDAF), lấy nét từ ~5cm đến vô cực, có bản 75° và 120°, có bản NoIR.

## 2. Camera và lấy nét (quan trọng)
- PDAF chỉ là cơ chế *đo* nét. **Vùng lấy nét do cấu hình quyết định.** Mặc định (`AfMetering=Auto`) camera có thể bắt nét vào tay/bút gần ống kính hơn trang giấy.
- Cách làm đúng: `AfMetering = Windows` + `AfWindows` = bounding box của trang giấy (lấy từ bước phát hiện trang), và dùng `AfMode = Auto` + `AfTrigger` ngay trước khi chụp ảnh gửi cloud, thay vì Continuous (continuous sẽ "dò nét" liên tục mỗi khi tay lướt qua khung). `AfRange = Macro/Normal` nếu khoảng cách gần.
- Chọn FOV: 75° giữ mật độ điểm ảnh tốt cho OCR, ít méo mép; 120° thấy được nhiều hơn nhưng méo thùng ở rìa và chữ nhỏ hơn. Không dùng bản NoIR (ảnh bị ám màu, hại OCR) trừ khi cần học trong bóng tối kèm đèn IR.
- Phương án nâng cấp khi 1 camera không vừa cả tư thế lẫn đọc chữ: **2 camera cố định** (75° chĩa xuống vở để đọc; 120° chĩa lên trẻ để quan sát tư thế) – Pi 5 hỗ trợ sẵn.
- Thư viện: `picamera2` (libcamera). Nhớ lệnh kiểm tra: `rpicam-hello --list-cameras`.

## 3. Pipeline AI cục bộ
| Việc | Gợi ý kỹ thuật | Ghi chú |
|---|---|---|
| Tư thế ngồi | MediaPipe Pose (BlazePose) hoặc MoveNet; tính góc gập cổ, nghiêng vai, nghiêng lưng, khoảng cách mắt-vở (ước lượng) | Chạy 5-10 fps là đủ, tư thế thay đổi chậm |
| Mất tập trung/buồn ngủ | MediaPipe FaceMesh: EAR (Eye Aspect Ratio), yaw/pitch đầu bằng solvePnP | Chỉ đo, không định danh |
| Tìm trang sách/vở | OpenCV: grayscale -> blur -> Canny -> contour tứ giác lớn nhất -> `getPerspectiveTransform` (deskew) | Cổ điển, nhẹ, không cần train |
| Cổng riêng tư | Face detector nhẹ (chỉ để chặn) + lọc vùng da (HSV) trên ảnh đã cắt | Chặn nếu có mặt/da vượt ngưỡng |

Lưu ý: "FaceMesh/landmark để đo trạng thái" khác "nhận diện khuôn mặt (định danh)". Luật định nghĩa dữ liệu sinh trắc học nhạy cảm là dữ liệu dùng để nhận diện cá nhân; thiết kế của dự án tránh việc định danh. Đây là cách hiểu kỹ thuật, không phải tư vấn pháp lý chính thức.

## 4. LLM đám mây (Claude/OpenAI)
- Ảnh được tính theo token như văn bản. Một ảnh ~1000x1000 px ≈ 1.300 token đầu vào; chi phí mỗi ảnh thường vài phần nghìn USD tùy model (kiểm tra bảng giá hiện hành). Thu nhỏ ảnh về đủ nét để đọc chữ giúp giảm chi phí và độ trễ.
- Không gửi video stream. Chỉ gửi ảnh trang đã cắt khi có sự kiện (trang ổn định trong khung, hoặc trẻ hỏi).
- Prompt hệ thống cần: giọng điệu phù hợp 6-12 tuổi, không đưa đáp án thẳng mà gợi ý từng bước, từ chối nội dung không phù hợp, nhận biết khi chữ viết tay không đọc được thì nói "không chắc" thay vì đoán, báo hiệu khi cần người lớn can thiệp.
- Chữ viết tay trẻ em là điểm yếu: phải đo riêng độ chính xác.

## 5. Khung pháp lý tóm tắt
- Luật BVDLCN 2025 (91/2025/QH15) có hiệu lực 01/01/2026; NĐ 356/2025/NĐ-CP hướng dẫn. Dữ liệu trẻ em cần sự đồng ý của người đại diện hợp pháp. Hệ thống camera AI nhận diện khuôn mặt có yêu cầu đánh giá tác động (DPIA) nặng hơn; dự án tránh nhận diện danh tính.
- Trước thương mại hóa phải tham vấn luật sư; giai đoạn này chỉ dùng dữ liệu người lớn có đồng ý.

## 6. Tài liệu nên đọc
- Picamera2 manual (Raspberry Pi) – phần Autofocus controls
- MediaPipe Pose / Face Landmarker docs
- OpenCV tutorial: document scanner với perspective transform
- Tài liệu API vision của Claude/OpenAI
