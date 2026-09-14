# SRT Voice Studio 1.2.0 — trạng thái đang nghiệm thu

Baseline: source và installer 1.1.0 đã xác minh, commit `33fea46f83c3ab360ece2567915412037b5ecbf3`. Mọi phần nâng cấp được tiếp tục trên nhánh `srt-voice-studio/1.2.0`.

Source đang được build/kiểm thử Windows: `8000defcbb2d35367ed72e57918c19dbe153be57`.
Lượt chạy: https://github.com/caoducanhgg2-dev/ComedyHostStudio/actions/runs/34819873200

Đã triển khai: hàng đợi nền tuần tự, cấu hình chung/riêng, hủy/thử lại, đầu ra tránh ghi đè, lưu cấu hình và yêu thích; router giữ Kokoro, gói Aivis tùy chọn có checksum và tải theo yêu cầu, Mao/Kohaku và phong cách bản địa; thư viện giọng tiếng Việt và nhập CSV điểm nghe có trọng số; Underfill V2, C Preview và render dùng chung fitting, START khóa tuyệt đối; comparator EN7 thực tế 46 caption và bộ nghe thử tám loại nội dung Anh/Nhật.

Ngày 14/09/2026, 101 test source đạt trong 372,50 giây. Kiểm tra thao tác nhập CSV và bộ lọc đề xuất trong GUI cũng đạt với dữ liệu thử tạm, không lưu điểm giả vào giọng thật. Windows đã vượt qua test, đóng gói frozen app, self-test và tạo installer. Kiểm tra nâng cấp/cài sạch/offline/render thực tế đang chạy.

Lỗi nghiệm thu ở lượt trước: đường dẫn baseline không tính thư mục lồng bên trong artifact. Đã sửa tìm đúng một installer theo tên, vẫn kiểm SHA-256 chính xác trước cài.

Chưa FINAL VERIFIED. Cần kết quả nghiệm thu Windows, installer/checksum/report và bộ nghe thử. Không tự chứng nhận độ tự nhiên hoặc tuyển đủ số lượng giọng đạt chất lượng khi chưa có điểm nghe. Phong cách bản địa không được tính thành giọng mới.
