# SRT Voice Studio 1.4.0

Bổ sung 4 giọng Nhật Aivis, ghi chú đặc điểm, tải riêng từng model và cập nhật ZIP có khôi phục bản cũ. Giữ timeline, A/B/C và hàng đợi hiện tại.

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

## Giọng nền được giữ nguyên

Kokoro tích hợp sẵn có **33 speaker thật**:

- 20 giọng English US giữ nguyên từ 1.2.
- 8 giọng English UK mới: `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`.
- 5 giọng Japanese giữ nguyên.

Các giọng UK dùng chung model Kokoro/ONNX và `voices-v1.0.bin`, nên không cần tải engine mới và không làm thay đổi pipeline offline. Backend dùng `en-gb` cho British English và chặn chọn nhầm voice US/UK chéo vùng.

Gói thử nghiệm Aivis vẫn thêm Mao và Kohaku với nhiều phong cách bản địa. Khi Aivis đã cài, thư viện có tối thiểu 35 speaker (không tính style thành giọng mới). Lần cài Aivis đầu cần mạng và tải khoảng 1,38 GB; sau cài đủ và kiểm tra checksum, gói dùng cục bộ. Nếu Aivis đã có model khác phiên bản, ứng dụng giữ nguyên và báo xung đột thay vì ghi đè. Đọc điều kiện ACML trước khi dùng.

Piper LJSpeech High vẫn là ứng viên nghiên cứu, chưa được đóng gói trong 1.3.0. Piper engine hiện dùng GPLv3 nên cần tách rõ nghĩa vụ phân phối/runtime trước khi đưa vào installer; không thêm chỉ để tăng số lượng giọng.

## Đánh giá nghe

Giọng chưa có đánh giá nghe không được gán điểm giả. Bộ Voice Auditions 1.3 tạo A_original.mp3 và C_final.mp3 cho cả US/UK/JP/Aivis, cùng `index.html`, `benchmark.json` và `ratings.csv`. Trọng số: tự nhiên 35%, phát âm 25%, biểu cảm 15%, khớp tốc độ 10%, chất lượng âm thanh 10%, độ phổ biến 5%. Bộ lọc Đề xuất chỉ dùng điểm người dùng nhập đạt từ 8/10.

## Cập nhật ZIP nhỏ và khôi phục

Gói cập nhật từ nền 1.3.1 được kiểm tra checksum chính xác, hỗ trợ hai biến thể
1.3.1 đã xác minh (GitHub và gói đã bàn giao). Nếu máy đang ở 1.3.0 hoặc bản
khác, updater từ chối thay file; cần gói đúng phiên bản nền.
Không chạy lại installer EXE. ZIP vẫn có thể chứa EXE chương trình mới.

1. Giải nén ZIP và đóng app.
2. Chạy Apply_Update.cmd. Updater xác minh toàn bộ file và sao lưu trước khi thay đổi.
3. App mới được kiểm tra mở giao diện và tạo MP3 tiếng Nhật trong vùng dữ liệu thử riêng.
4. Nếu kiểm tra thất bại, updater tự khôi phục các file cũ và thông tin phiên bản.
5. Nếu phát hiện lỗi sau đó, đóng app và chạy Restore_Previous.cmd trong ZIP.

Bản sao lưu nằm trong dữ liệu người dùng SRTVoiceStudio/updates, không bị xóa
khi cập nhật thành công. Thư mục sao lưu cũng chứa script khôi phục để dùng khi
đã xóa ZIP. Cập nhật bị gián đoạn được nhận diện bằng nhật ký; chạy updater hoặc
script khôi phục để đưa các file về phiên bản cũ. Nếu khôi phục gặp lỗi khóa file,
quyền ghi hoặc checksum, bản sao lưu được giữ nguyên và lỗi được báo rõ.
Không thể bảo đảm khôi phục nếu ổ đĩa hoặc bản sao lưu đã bị mất/hỏng.

## Giọng Nhật bổ sung và ghi chú

| Giọng | Đặc điểm theo trang model | Style bản địa |
|---|---|---|
| Rinne El | Giọng nữ trẻ | Normal, Angry, Fear, Happy, Sad |
| Aida Shigeru | Nam trung niên, baritone | Normal, Calm, Far, Heavy, Mid, Shout, Surprise |
| Mai | Giọng nữ trẻ | Normal |
| Nise | Giọng nam trẻ | Normal |

Đã đối chiếu trang AivisHub ngày 15/09/2026. UUID, SHA-256 và nguồn của từng
model được ghim trong studio/aivis_pack.py. Mô tả không phải điểm chất lượng nghe.
Mao, Kohaku và 5 giọng Nhật Kokoro hiện có vẫn được giữ. Tổng khả năng: 11 speaker
Nhật, trong đó 6 speaker Aivis tùy chọn; không tính style thành speaker mới.

Trong thư viện giọng, chọn model muốn tải rồi chấp nhận điều kiện của model.
Engine/BERT dùng chung tải một lần; model khoảng 250–258 MB mỗi giọng. Có thể
chọn tải tất cả nhưng không bắt buộc. File tải lỗi không ghi đè model đang có.
A/B/C hiện có dùng để nghe thử giọng sau khi cài. Chất lượng nghe cần người dùng
đánh giá; không gắn nhãn tự nhiên hoặc điểm nghe đã kiểm chứng khi chưa chấm.
