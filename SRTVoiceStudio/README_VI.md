# SRT Voice Studio 1.3.1

Bản 1.3.1 giữ nguyên engine timeline/Underfill V2 và bộ giọng của 1.3.0, nhưng đổi cơ chế phát hành cập nhật: **không chạy lại bộ cài EXE**. Từ nền 1.3.0, bản cập nhật được đóng thành **ZIP delta chỉ chứa các file thay đổi**.

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

## Thư viện giọng

Kokoro tích hợp sẵn có **33 speaker thật**:

- 20 giọng English US.
- 8 giọng English UK: `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`.
- 5 giọng Japanese.

Các giọng UK dùng chung model Kokoro/ONNX và `voices-v1.0.bin`, nên không cần tải engine mới. Backend dùng `en-gb` cho British English và chặn chọn nhầm voice US/UK chéo vùng.

Gói thử nghiệm Aivis vẫn thêm Mao và Kohaku với nhiều phong cách bản địa. Khi Aivis đã cài, thư viện có tối thiểu 35 speaker (không tính style thành giọng mới). Lần cài Aivis đầu cần mạng và tải khoảng 1,38 GB; sau cài đủ và kiểm tra checksum, gói dùng cục bộ. Nếu Aivis đã có model khác phiên bản, ứng dụng giữ nguyên và báo xung đột thay vì ghi đè. Đọc điều kiện ACML trước khi dùng.

Piper LJSpeech High vẫn là ứng viên nghiên cứu, chưa được đóng gói. Piper engine hiện dùng GPLv3 nên cần tách rõ nghĩa vụ phân phối/runtime trước khi đưa vào bản phát hành.

## Đánh giá nghe

Giọng chưa có đánh giá nghe không được gán điểm giả. Bộ Voice Auditions tạo A_original.mp3 và C_final.mp3 cho cả US/UK/JP/Aivis, cùng `index.html`, `benchmark.json` và `ratings.csv`. Trọng số: tự nhiên 35%, phát âm 25%, biểu cảm 15%, khớp tốc độ 10%, chất lượng âm thanh 10%, độ phổ biến 5%. Bộ lọc Đề xuất chỉ dùng điểm người dùng nhập đạt từ 8/10.

## Cập nhật bằng ZIP — không chạy lại installer EXE

Bản cài đầy đủ 1.3.0 chỉ dùng làm **nền ban đầu**. Từ 1.3.1, cập nhật theo dạng:

`SRTVoiceStudio_Update_1.3.0_to_1.3.1.zip`

Cách dùng:

1. Giải nén ZIP ra một thư mục tạm bất kỳ.
2. Đóng SRT Voice Studio.
3. Chạy `Apply_Update.cmd`.
4. Script tự tìm thư mục cài từ Windows, kiểm tra đúng phiên bản nền và SHA-256 từng file trước khi ghi đè.
5. Chỉ các file thay đổi mới được thay thế; dữ liệu trong `%LOCALAPPDATA%\SRTVoiceStudio` được giữ nguyên.
6. Nếu checksum nền không đúng, updater dừng trước khi ghi file. Nếu lỗi trong lúc cập nhật, các file đã thay được rollback từ bản sao tạm.
7. Sau khi thành công, `DisplayVersion` trong Windows được cập nhật lên 1.3.1.

CI phải dựng lại đúng frozen app của commit 1.3.0, so hash với frozen app mới, đóng gói **delta thật**, rồi kiểm tra: kết quả sau patch phải byte-for-byte tương đương build mới, chạy patch lần hai không thay đổi kết quả, và baseline bị sửa phải bị từ chối trước khi ghi đè.
