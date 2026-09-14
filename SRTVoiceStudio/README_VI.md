# SRT Voice Studio 1.1.0

Nâng cấp trực tiếp từ bản 1.0.0: giữ Kokoro/ONNX, âm vị tiếng Nhật, 20 giọng Mỹ,
5 giọng Nhật và mốc SRT cố định. Một MP3 mono 48 kHz / 192 kbps duy nhất.
Không cần API, mạng, Python, FFmpeg hay CUDA trên máy người dùng.

## Sử dụng

1. Chọn hoặc kéo thả SRT UTF-8/UTF-8 BOM.
2. Chọn ngôn ngữ và giọng đọc. Tên thân thiện được ánh xạ tới đúng mã giọng cũ.
3. Tùy chọn cảm xúc và hiệu ứng. Mặc định Thủ công / Tự nhiên / Không hiệu ứng.
4. Nghe A (giọng gốc), B (cùng giọng gốc qua xử lý), hoặc chọn câu SRT rồi nghe C
   (âm thanh sau căn thời gian, cắt và cân bằng âm lượng, dùng chung hàm với bản xuất).
5. Bấm TẠO MP3. Tên đề xuất: TênSRT_Voice.mp3.

Giao diện tiếng Việt, hai cột màu navy. Cấu hình ở trái, nghe thử và chọn câu ở phải.
Vùng nội dung có thể cuộn trên màn hình nhỏ; nút tạo, hủy và khu vực kết quả luôn hiện.

## Căn câu ngắn và dài

Khi bật **Tự căn câu ngắn / dài**, app đo audio sau cảm xúc và hiệu ứng:

- Câu ngắn: giảm tốc nhẹ để nhắm khoảng lặng cuối khung 0,20 giây.
- Tốc độ tổng (người dùng × cảm xúc × căn thời gian) không dưới 0,88× và không quá 1,20×.
- Câu dài: ưu tiên tăng tới 1,15×, tối đa 1,20×; nếu vẫn quá dài thì cắt an toàn
  và làm nhỏ dần 5 ms cuối, hoặc dừng/báo lỗi theo lựa chọn.
- Không dịch START của bất kỳ câu nào. Không kéo câu sau lên trước.
- Nếu còn dư hơn 0,40 giây, app báo **LỜI THOẠI NGẮN / CHƯA LẤP ĐẦY KHUNG**.
  Đây là cảnh báo độ phủ lời thoại, không phải lỗi chồng tiếng.
- Ví dụ 2,80 giây / 0,88 = khoảng 3,18 giây: trong khung 4 giây vẫn còn khoảng
  0,82 giây im lặng. App chấp nhận khoảng dư này để giữ giới hạn tốc độ.

“Im lặng cuối khung” là khoảng từ cuối audio đã căn đến mốc kết thúc cho phép,
không bao gồm gap SRT tiếp theo. Mục tiêu 0,20 giây không được bảo đảm cho script quá ngắn.
Báo cáo có trung bình/lớn nhất, câu chưa lấp đầy, câu ở giới hạn 0,88×, tăng/giảm tốc,
cắt và chồng tiếng. Tăng/giảm tốc được đếm so với tốc độ người dùng cộng preset trước căn.
Tắt tự căn để giữ tốc độ đã chọn; cảnh báo thiếu lời thoại vẫn hiển thị.

## Cảm xúc và hiệu ứng

12 preset cảm xúc với 3 mức độ; 16 lựa chọn hiệu ứng (tính cả Không hiệu ứng) với 3 mức độ.
Kokoro không có tham số emotion native. Đây là xử lý pitch/EQ/dynamics/tempo local.
“Mô phỏng thì thầm” không phải một model thì thầm thật.
Tự động chọn cảm xúc dùng quy tắc từ khóa/dấu câu riêng cho Anh và Nhật, không sửa SRT.
Chế độ Tự động bỏ qua lựa chọn cảm xúc thủ công và tự chọn cho từng câu.

Echo/vang phòng/vang hang động chạy **trước** khi đo và căn khung.
Đuôi vang không được phép vượt mốc. Tự nhiên + Không hiệu ứng không áp thêm màu giọng;
việc căn câu ngắn vẫn hoạt động khi bật tự căn.

A được lưu trong RAM theo ngôn ngữ/giọng/nội dung. Đổi style chỉ tính lại B/C.
Nghe thử dùng QMediaPlayer với bộ đệm WAV trong RAM, không tạo file nghe thử.
Thay giọng/nội dung, tạo xong hoặc đóng app sẽ giải phóng bộ đệm.
Không xuất WAV, MP3 từng câu, A/B/C riêng hay báo cáo cạnh MP3.

## Cài đặt và kiểm thử

SRTVoiceStudio_Setup_1.1.0.exe giữ AppId `{68F0C1C1-17CB-4CED-8261-5C18EB92571A}`,
nâng cấp vào đúng thư mục bản 1.0.0. Có shortcut và trình gỡ cài.
Xem AUDIT_1.0.md, CHANGELOG.md, TEST_REPORT.md và acceptance.json của đúng build.

Workflow chính ở `.github/workflows/srt-voice-studio-windows.yml` trong root repository.
Windows runner dùng Python 3.12.10, dependency lock cũ, model và FFmpeg đi kèm.
Chỉ công bố installer khi unit/DSP, frozen EXE, nâng cấp/cài mới, A/B/C, 74 câu Anh + Nhật,
EN7 30 câu với Underfill, Unicode và gỡ cài đều đạt.

Bài so sánh EN7 dùng cùng 30 audio Kokoro gốc cho renderer 1.0 được lưu nguyên trạng
và renderer mới. `acceptance_baseline_1_0.py` chỉ phục vụ benchmark này; giao diện,
Preview C và xuất bản mới đều dùng `fitting.py` duy nhất.

Kết quả Windows runner không thay thế kiểm tra bằng tai và nghiệm thu trên máy
Windows 10/11 cụ thể của người dùng. Hiệu quả cảm xúc là DSP, có giới hạn tự nhiên.

## Nâng cấp 1.2.0 — ứng viên đang kiểm thử

- Tab **Hàng đợi xử lý**: thêm nhiều SRT hoặc thư mục, dùng cấu hình chung hoặc sửa từng hàng, hủy một/toàn bộ, thử lại tệp lỗi. Một tệp lỗi không dừng các tệp sau. Mỗi SRT xuất một MP3; tên trùng được thêm số.
- Tab **Thư viện giọng**: lọc Anh/Nhật/đã cài/yêu thích. Chọn Dùng giọng này để trở về cấu hình và nghe A/B/C.
- Gói Aivis tải tùy chọn khoảng 1,4 GB; cần mạng khi cài lần đầu, sau đó tổng hợp trên máy. Đọc điều kiện ACML trước khi tải. Các phong cách bản địa nằm dưới cùng một giọng; đổi phong cách làm mới A, B, C.
- Menu **Cấu hình** lưu/nạp tùy chọn. Dữ liệu và voice pack nằm ngoài thư mục cài để giữ qua nâng cấp.
- Underfill V2 đo sau cảm xúc/hiệu ứng, giữ START và giới hạn 0.88–1.20x. Khoảng lặng còn lại trên 0,80 giây ở tốc độ tối thiểu hiện cảnh báo, không đổi thành lỗi overlap.
- Không có điểm chất lượng cảm nhận tự tạo. Xem VOICE_RESEARCH_1.2.md và bộ nghe thử trước khi coi một giọng là đề xuất.
