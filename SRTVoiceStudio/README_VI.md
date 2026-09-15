# SRT Voice Studio 1.4.0

Bản 1.4 giữ nguyên engine timeline/Underfill V2 ổn định của 1.3.x, mở rộng thư viện giọng Nhật và chuyển phát hành nhỏ sang **ZIP delta update**. Mỗi SRT tạo một MP3 48 kHz, 192 kbps; START của caption không bị dịch chuyển và mục tiêu bắt buộc vẫn là overlap = 0.

## Tạo MP3 và nghe thử

1. Chọn SRT, ngôn ngữ, giọng và thư mục kết quả.
2. Ngôn ngữ Kokoro tích hợp sẵn: Tiếng Anh (Mỹ), Tiếng Anh (Anh) và Tiếng Nhật.
3. Chọn cảm xúc, hiệu ứng và mức độ nếu cần. Các xử lý này chạy sau TTS; phong cách bản địa của Aivis chạy trong bộ tạo giọng.
4. Nghe A — giọng gốc, B — đã xử lý, C — đã khớp timeline. C dùng cùng bộ khớp thời gian với xuất MP3.
5. Bấm TẠO MP3. Mở báo cáo để xem tốc độ, khoảng lặng, số câu cắt và kiểm tra chồng tiếng.

Không ghi đè đầu ra đã có: ứng dụng chọn tên mới. START không dịch chuyển để giảm khoảng lặng. MP3 được mã hóa một lần từ master PCM.

## Khớp thời gian Underfill V2

Thời lượng được đo sau cảm xúc và hiệu ứng. Câu ngắn được làm chậm nhẹ, giới hạn thấp nhất 0,88×; câu dài được tăng tốc, ưu tiên tối đa 1,15× và giới hạn cứng 1,20×. Safe Trim xử lý phần quá dài nếu bật. Mục tiêu khoảng lặng cuối slot là khoảng 0,15 giây khi giới hạn tốc độ cho phép. Câu vẫn ngắn khi đã chạm giới hạn được giữ khoảng lặng còn lại, không tiếp tục kéo chậm.

Cảnh báo V2 xuất hiện khi khoảng lặng còn trên 0,80 giây sau mức chậm tối thiểu. Báo cáo có trung bình, trung vị, tối đa, số câu tăng/giảm tốc, cắt, thiếu thời lượng và overlap. Khoảng lặng theo độ dài PCM không đồng nghĩa hoàn toàn với khoảng lặng cảm nhận khi nghe.

## Xử lý hàng loạt

Thêm nhiều SRT hoặc thư mục, dùng cấu hình chung hay cấu hình riêng từng tệp. Hàng đợi xử lý tuần tự trong luồng nền. Có thể hủy công việc hiện tại hoặc cả hàng đợi, thử lại mục lỗi/hủy. Một tệp lỗi không ngăn các mục sau chạy. Mỗi SRT có MP3 và kết quả riêng.

## Thư viện giọng 1.4

Kokoro tích hợp sẵn có **33 speaker thật**: 20 English US, 8 English UK và 5 Japanese. Gói Aivis Nhật là tùy chọn, bổ sung tối đa **6 speaker Nhật**, đưa tổng dung lượng thư viện lên ít nhất **39 speaker** khi cài đủ. Style/phong cách không được tính thành speaker riêng.

### 5 giọng Nhật Kokoro có sẵn

- `jf_alpha` — Nữ · sáng, trẻ trung, linh hoạt.
- `jf_gongitsune` — Nữ · mềm, dịu, hợp kể chuyện.
- `jf_nezumi` — Nữ · nhẹ, đáng yêu, thiên hoạt hình.
- `jf_tebukuro` — Nữ · ấm, điềm tĩnh, tự nhiên.
- `jm_kumo` — Nam · trầm vừa, bình tĩnh, hợp thuyết minh.

### 6 giọng Nhật Aivis tùy chọn

- **Mao** — Nữ · tự nhiên, mềm, hội thoại đời thường. Style: Tự nhiên, Đời thường, Ngọt ngào, Điềm tĩnh, Trêu đùa, Man mác buồn.
- **Kohaku** — Nữ · nhẹ, ngọt, thư giãn. Style: Tự nhiên, Ngọt ngào, Man mác buồn, Buồn ngủ.
- **Rinne El** — Nữ · trẻ, sáng, giàu cảm xúc. Style: Tự nhiên, Giận dữ, Lo lắng, Vui vẻ, Buồn.
- **Aida Shigeru** — Nam · baritone, trung niên, hợp kể chuyện. Style: Tự nhiên, Điềm tĩnh, Xa mic, Nặng/dày, Trung tính, Hô lớn, Ngạc nhiên.
- **Mai** — Nữ · trẻ, mềm, biểu cảm. Style hiện dùng: Tự nhiên.
- **Nise** — Nam · trẻ, tự nhiên, hội thoại. Style hiện dùng: Tự nhiên.

Các mô tả trên chỉ giúp chọn nhanh, **không phải điểm chất lượng nghe**. Bộ Voice Auditions và ratings.csv vẫn là nguồn quyết định khi gắn nhãn Recommended.

Gói Aivis tải theo yêu cầu, không tự tải khi chưa chọn. Model được pin phiên bản, kích thước và SHA-256. Lần cài mới đầy đủ tải khoảng 2,4 GB; máy đã có Mao/Kohaku chỉ tải phần còn thiếu. Sau khi cài đủ, engine/model chạy local. Nếu thư mục Aivis đã có file khác checksum, ứng dụng giữ nguyên và báo xung đột thay vì ghi đè.

Aivis model trong gói dùng ACML 1.0; engine AivisSpeech dùng LGPL-3.0; BERT đi kèm dùng CC-BY-SA-4.0. Cần đọc điều kiện giấy phép hiển thị trong ứng dụng trước khi dùng thương mại/review/comedy.

## Cập nhật 1.3.1 → 1.4.0 bằng ZIP nhỏ

Bản 1.4 ưu tiên **không chạy lại installer EXE**. Gói phát hành là `SRTVoiceStudio_Update_1.3.1_to_1.4.0.zip` và chỉ chứa các file thực sự thay đổi cùng manifest/checksum.

1. Đóng SRT Voice Studio.
2. Giải nén toàn bộ ZIP vào một thư mục tạm.
3. Chạy `Apply_Update.cmd`.
4. Updater tự tìm vị trí cài đặt, kiểm tra SHA-256 của payload và kiểm tra checksum baseline **trước khi ghi đè**.
5. Nếu baseline không đúng hoặc patch lỗi giữa chừng, updater dừng và transaction rollback trả các file đã động vào về trạng thái trước khi chạy.
6. Khi update thành công, ứng dụng giữ thêm một **persistent rollback snapshot** trong `%LOCALAPPDATA%\SRTVoiceStudio\updates`.

Chạy lại cùng patch trên 1.4 đã cập nhật là idempotent: không thay đổi app và không ghi đè snapshot rollback hợp lệ.

## Quay lại 1.3.1 nếu 1.4 có vấn đề

Giữ thư mục ZIP đã giải nén và chạy `Rollback_Update.cmd`. Rollback sẽ:

- đọc snapshot gần nhất;
- kiểm tra checksum các file 1.4 hiện tại trước khi phục hồi;
- khôi phục chính xác file cũ hoặc xóa file mới được thêm bởi patch;
- trả `DisplayVersion` về 1.3.1 khi registry installer còn tồn tại;
- tự rollback chính quá trình phục hồi nếu có lỗi giữa chừng.

Sau khi quay về 1.3.1, có thể chạy `Apply_Update.cmd` lần nữa để cài lại 1.4. Snapshot rollback không thay đổi dữ liệu người dùng, Favorites hay gói giọng trong `%LOCALAPPDATA%\SRTVoiceStudio` ngoài thư mục audit/update riêng.

## Nghiệm thu bắt buộc 1.4

Build phát hành chỉ được coi là đạt khi đồng thời qua các kiểm tra: unit tests; 20 US + 8 UK + 5 Japanese Kokoro; 6 Aivis Japanese khi cài đủ; mapping style động; frozen-app check; delta từ đúng artifact 1.3.1; exact patched-app match; corruption guard không ghi dở; idempotency; persistent rollback về đúng baseline; reapply sau rollback; registry 1.3.1 → 1.4.0 → 1.3.1 → 1.4.0; và timeline vẫn overlap = 0.
