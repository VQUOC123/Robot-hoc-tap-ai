# 01. Brief và phạm vi

## 1. Ý tưởng sản phẩm (tầm nhìn dài hạn)
Một robot để bàn dáng nhân vật hoạt hình dành cho trẻ 6-12 tuổi. Robot quan sát bàn học bằng camera để: (a) nhắc tư thế ngồi và mất tập trung, (b) đọc nội dung sách vở/bài làm, tư vấn, giảng giải, hướng dẫn, (c) báo cáo cho phụ huynh/giáo viên và cho phép họ can thiệp ngoài giao diện AI. LLM đám mây (Claude/OpenAI) là "bộ não" hội thoại và hiểu nội dung bài.

## 2. Phạm vi giai đoạn này (8 tuần): Proof of Concept
Chứng minh vòng lặp lõi chạy được trên Raspberry Pi 5 với **camera cố định (không pan-tilt)**:

```
Camera -> [LOCAL] phát hiện tư thế + mất tập trung -> nhắc nhở
       -> [LOCAL] tìm & cắt trang sách/vở -> cổng riêng tư -> [CLOUD LLM] hiểu nội dung -> giảng giải
       -> ghi sự kiện (chỉ văn bản/số liệu) -> dashboard phụ huynh tối giản
```

**Trong phạm vi:** pipeline thị giác cục bộ, đọc trang bằng LLM, cổng riêng tư, log sự kiện + dashboard web tối giản, đo đạc và báo cáo.
**Ngoài phạm vi:** vỏ robot/mô hình 3D, pan-tilt, nhận diện danh tính, ứng dụng di động, video call giáo viên, thử nghiệm với trẻ em thật.

## 3. Nguyên tắc bắt buộc (không thương lượng)
1. **Không nhận diện khuôn mặt/danh tính.** Không tính embedding khuôn mặt, không so khớp ai với ai. Landmark chỉ dùng để đo trạng thái (góc đầu, mở mắt).
2. **Không lưu ảnh/video xuống đĩa** trong luồng vận hành. Khung hình chỉ nằm trong RAM (ring buffer vài giây). Chỉ ghi dữ liệu dẫn xuất: góc, cờ, thời điểm.
3. **Chỉ ảnh trang sách/vở đã cắt mới được gửi lên cloud**, và phải qua cổng riêng tư (xem 04). Không bao giờ gửi ảnh có mặt/thân người.
4. **Dashboard chỉ nhận dữ liệu dẫn xuất** (văn bản/số), không nhận ảnh.
5. **Không dùng dữ liệu của trẻ em thật trong đợt thực tập.** Dữ liệu thử nghiệm lấy từ chính sinh viên/người lớn tình nguyện đã đồng ý bằng văn bản. Ảnh tập dữ liệu để đánh giá lưu riêng, mã hóa, xóa khi kết thúc đề tài.
6. API key lưu trong biến môi trường/file .env không commit.

Lý do: Luật Bảo vệ dữ liệu cá nhân 2025 (số 91/2025/QH15, hiệu lực 01/01/2026) và Nghị định 356/2025/NĐ-CP siết chặt xử lý dữ liệu trẻ em; thiết kế "privacy by design" là điểm cốt lõi của sản phẩm.

## 4. Phần cứng được cấp và giả định
- Raspberry Pi 5 (nên 4GB hoặc 8GB), nguồn USB-C 27W, thẻ nhớ/SSD, tản nhiệt chủ động.
- Camera có autofocus (Pi Camera Module 3 Standard 75°, bản có IR-cut).
- Chưa có Hailo AI HAT+: mặc định chạy mô hình nhẹ trên CPU. Nếu sau này có HAT thì chuyển, nhưng **thiết kế code phải tách lớp suy luận** để thay được backend.
- Micro/loa: tùy chọn, chỉ cần cho yêu cầu mức "Could".
