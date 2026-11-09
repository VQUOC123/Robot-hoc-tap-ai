# 06. Tiêu chí nghiệm thu và checklist

Các ngưỡng là **mục tiêu đề xuất**; sau khi đo baseline ở tuần 2-3, nhóm đề xuất điều chỉnh có lý do và giảng viên duyệt.

## 1. Tiêu chí định lượng
| Mã | Tiêu chí | Mục tiêu | Cách đo |
|---|---|---|---|
| Q1 | Tốc độ pose trên Pi 5 (CPU) | >= 5 fps ổn định | Log fps trung bình/phút, 10 phút |
| Q2 | Độ trễ từ tư thế xấu đủ ngưỡng đến lúc nhắc | <= 3 giây | Quay màn hình/đồng hồ, >= 20 lần |
| Q3 | Phát hiện tư thế xấu | F1 >= 0.85 | >= 200 clip ngắn có nhãn, >= 5 người lớn tình nguyện, đa dạng ánh sáng |
| Q4 | Tỷ lệ báo nhầm | <= 1 lần/10 phút học bình thường | Phiên học 30 phút x >= 3 người |
| Q5 | Cắt trang đúng | >= 90% trên >= 50 ảnh đa dạng (vở kẻ ô, sách, nền bàn khác nhau, ánh sáng khác nhau) | Chấm thủ công đúng/sai |
| Q6 | Độ chính xác đọc chữ in (qua LLM) | >= 90% ký tự | >= 30 trang, so với văn bản gốc |
| Q7 | Chữ viết tay (chỉ báo cáo) | Báo cáo số đo, không ép ngưỡng | >= 30 mẫu chữ viết tay người lớn mô phỏng chữ trẻ em |
| Q8 | Thời gian từ chụp trang đến có phản hồi (trung vị) | <= 8 giây | Log latency, >= 30 lần |
| Q9 | Cổng riêng tư chặn đúng | >= 98% trên >= 50 ảnh đối kháng (có mặt/tay/da trong khung) | Bộ ảnh đối kháng tự dựng |
| Q10 | Ảnh ghi ra đĩa | **0** | Test tự động theo dõi thư mục/syscall trong 1 giờ chạy |
| Q11 | Payload server chứa ảnh | **0** chấp nhận | Test gửi ảnh -> phải bị 422 |
| Q12 | Ổn định | 2 giờ liên tục không crash, nhiệt CPU < 80°C | Soak test, log nhiệt |
| Q13 | Chi phí LLM mỗi giờ học điển hình | Báo cáo số đo; đề xuất nếu > ngưỡng giảng viên đặt | Log token x đơn giá |

## 2. Checklist theo mốc
### M1 (tuần 3)
- [ ] Camera chạy ổn, AF cấu hình được, báo cáo thí nghiệm AF
- [ ] Vị trí lắp camera được chốt kèm ảnh
- [ ] Hiển thị chỉ số tư thế realtime; nhắc khi vi phạm ngưỡng
- [ ] Debounce/cooldown hoạt động; log hiệu năng (Q1)
### M2 (tuần 5)
- [ ] Phát hiện + cắt + deskew trang (Q5 sơ bộ)
- [ ] Cổng riêng tư hoạt động, có bộ ảnh đối kháng (Q9 sơ bộ)
- [ ] Luồng trang -> LLM -> phản hồi chạy end-to-end (Q8 sơ bộ)
- [ ] Server nhận sự kiện, từ chối ảnh (Q11)
- [ ] Bộ >= 20 tình huống đánh giá prompt, có kết quả
### M3 (tuần 8)
- [ ] Tất cả yêu cầu Must (file 03) đạt; Q1-Q12 có số đo
- [ ] Soak test 2 giờ đạt (Q12)
- [ ] Review code xác nhận không có nhận diện danh tính (G2)
- [ ] Không còn API key/ảnh/dữ liệu cá nhân trong repo; dữ liệu thử nghiệm đã xóa hoặc mã hóa
- [ ] README chạy lại được từ máy sạch trong <= 30 phút
- [ ] Báo cáo cuối: kết quả, hạn chế, đề xuất bước tiếp (Hailo, 2 camera, pan-tilt, vỏ robot, DPIA/đồng ý phụ huynh)
- [ ] Demo trực tiếp 10 phút

## 3. Cách chấm
Must đạt đủ = đạt đề tài. Should/Could là điểm cộng. Mọi số đo phải kèm điều kiện (ánh sáng, người, thiết bị, phiên bản code).
