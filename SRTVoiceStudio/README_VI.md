# SRT Voice Studio 1.2.0

Nâng cấp từ 1.1.0, giữ nền Kokoro và mốc START của SRT. Mỗi SRT tạo một MP3 48 kHz, 192 kbps. Giao diện tiếng Việt gồm tạo MP3, xử lý hàng loạt và thư viện giọng.

## Tạo MP3 và nghe thử

1. Chọn SRT, ngôn ngữ, giọng và thư mục kết quả.
2. Chọn cảm xúc, hiệu ứng và mức độ nếu cần. Các xử lý này chạy sau TTS; phong cách bản địa của Aivis chạy trong bộ tạo giọng.
3. Nghe A — giọng gốc, B — đã xử lý, C — đã khớp timeline. C dùng cùng bộ khớp thời gian với xuất MP3.
4. Bấm TẠO MP3. Mở báo cáo để xem tốc độ, khoảng lặng, số câu cắt và kiểm tra chồng tiếng.

Không ghi đè đầu ra đã có: ứng dụng chọn tên mới. START không dịch chuyển để giảm khoảng lặng. MP3 được mã hóa một lần từ master PCM.

## Khớp thời gian Underfill V2

Thời lượng được đo sau cảm xúc và hiệu ứng. Câu ngắn được làm chậm nhẹ, giới hạn thấp nhất 0,88×; câu dài được tăng tốc, ưu tiên tối đa 1,15× và giới hạn cứng 1,20×. Safe Trim xử lý phần quá dài nếu bật. Mục tiêu khoảng lặng cuối slot là khoảng 0,15 giây khi giới hạn tốc độ cho phép. Câu vẫn ngắn khi đã chạm giới hạn được giữ khoảng lặng còn lại, không tiếp tục kéo chậm.

Cảnh báo V2 xuất hiện khi khoảng lặng còn trên 0,80 giây sau mức chậm tối thiểu. Báo cáo có trung bình, trung vị, tối đa, số câu tăng/giảm tốc, cắt, thiếu thời lượng và overlap. Khoảng lặng theo độ dài PCM không đồng nghĩa hoàn toàn với khoảng lặng cảm nhận khi nghe.

## Xử lý hàng loạt

Thêm nhiều SRT hoặc thư mục, dùng cấu hình chung hay cấu hình riêng từng tệp. Hàng đợi xử lý tuần tự trong luồng nền. Có thể hủy công việc hiện tại hoặc cả hàng đợi, thử lại mục lỗi/hủy. Một tệp lỗi không ngăn các mục sau chạy. Mỗi SRT có MP3 và kết quả riêng.

## Giọng và gói tùy chọn

Giữ 25 giọng Kokoro gốc. Bộ lọc gồm đã cài, Anh, Nhật, tất cả, yêu thích và đề xuất. Phong cách bản địa không tính là giọng mới.

Gói thử nghiệm Aivis thêm Mao và Kohaku với nhiều phong cách bản địa. Lần cài đầu cần mạng và tải khoảng 1,38 GB; sau cài đủ và kiểm tra checksum, gói dùng cục bộ. Gói lớn được lưu riêng với bộ cài chính. Aivis sử dụng thư mục chuẩn AppData/Roaming/AivisSpeech-Engine cho model và bộ nhớ đệm; nếu đã có tệp khác phiên bản, ứng dụng giữ nguyên và báo xung đột thay vì ghi đè. Đọc điều kiện ACML trước khi cài: giấy phép có hạn chế nội dung, không phải mọi tình huống thương mại đều được phép. Xem VOICE_RESEARCH_1.2.md và third_party/NOTICE.md.

Giọng chưa có đánh giá nghe không được gán điểm giả. Bộ nghe thử có A_original.mp3, C_final.mp3, index.html và ratings.csv. Điền sáu điểm 0–10 và người chấm rồi dùng “Nạp điểm nghe từ ratings.csv”. Trọng số: tự nhiên 35%, phát âm 25%, biểu cảm 15%, khớp tốc độ 10%, chất lượng âm thanh 10%, độ phổ biến 5%. Bộ lọc đề xuất dùng điểm nhập đạt từ 8/10; đây là đánh giá do người dùng cung cấp.

## Nâng cấp

Chạy SRTVoiceStudio_Setup_1.2.0.exe. Bộ cài dùng cùng AppId để nhận vị trí cài 1.1.0, giữ tùy chọn và gói giọng trong dữ liệu người dùng. Không cần tìm một source 1.2.0 có sẵn.

Bản phát hành chỉ được gắn FINAL VERIFIED sau khi các bước nghiệm thu tương ứng hoàn tất. Test timeline và cài đặt không thay thế việc nghe xác nhận độ tự nhiên.
