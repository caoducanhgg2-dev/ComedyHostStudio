# SRT Voice Studio 1.1.0 — đang nghiệm thu bản cuối

- Source đang phát triển được giữ nguyên; baseline 1.0 và commit gốc xem AUDIT_1.0.md.
- Trước cập nhật: 18/18 regression gốc đạt.
- Sau Emotion, FX, Underfill: 72/72 test tại Work (Linux) đạt trong 404,43 giây.
- 12 cảm xúc / 16 lựa chọn hiệu ứng × 3 mức độ; cache A; C dùng chung fit;
  giới hạn tốc độ 0,88–1,20×; target/cảnh báo underfill; giữ pitch; Safe Trim;
  Stop and Report; silence đầu và 74 câu Anh/Nhật với tín hiệu kiểm thử: đạt.
- GUI tiếng Việt hai cột: kiểm thử thao tác A/B/C, cảnh báo thiếu lời thoại,
  mã giọng ổn định, nút TẠO MP3 và dọn preview trong RAM: đạt với backend kiểm thử.
- Đã tìm được đúng SRT và MP3 EN7 của người dùng: 30 câu, 4,008–4,009 giây/câu,
  gap 0,100 giây. Đo MP3 cũ bằng khung RMS 10 ms, ngưỡng -50 dBFS: khoảng lặng
  cuối khung trung bình 0,7152 giây, tối đa 1,349 giây; 8 câu trên 1 giây.
- Benchmark Windows dùng đúng SRT EN7 và cùng 30 audio Kokoro gốc để so sánh
  renderer 1.0 lưu nguyên trạng với renderer mới. Không suy luận giọng đọc của
  MP3 cũ từ mockup; benchmark ghi rõ voice và checksum nguồn.
- Build trước Underfill/Việt hóa đạt DSP/EXE/giọng thật nhưng bị gate dọn file
  preview Windows chặn. Đã thay file nghe thử bằng QBuffer trong RAM để sửa lỗi.

Chưa coi installer hiện tại là FINAL VERIFIED. Cần build lại đúng source mới và
đạt đầy đủ gate Windows, bao gồm EN7, 74 câu thật, nâng cấp/cài mới và gỡ cài.
Kết quả cuối được ghi trong acceptance.json của đúng run đạt.
