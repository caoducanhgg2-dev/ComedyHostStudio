# SRT Voice Studio 1.4.1 — Voice Expansion

## Mục tiêu

Bản 1.4.1 là hotfix mở rộng thư viện giọng trên nền 1.4.0 Final. Không thay đổi engine timeline, fitting, emotion/FX hay quy tắc xuất MP3 đã ổn định ở 1.4.0.

## Thay đổi chính

- Thêm chú thích chọn nhanh cho toàn bộ 20 giọng Kokoro English US.
- Thêm chú thích chọn nhanh cho toàn bộ 8 giọng Kokoro English UK.
- Giữ 5 giọng Kokoro Japanese và chú thích hiện có.
- Thư viện giọng luôn hiển thị trước 6 giọng Aivis Japanese tùy chọn, kể cả khi model chưa tải:
  - Mao
  - Kohaku
  - Rinne El
  - Aida Shigeru
  - Mai
  - Nise
- Giọng Aivis chưa tải được đánh dấu rõ `Chưa cài`; không thể chọn render cho đến khi backend thật được cài và đăng ký.
- Sau khi tải gói Aivis và xác minh checksum, 6 giọng xuất hiện trong dropdown Tiếng Nhật và dùng local/offline.
- Bộ lọc `Đã cài` giờ chỉ hiển thị giọng thực sự sẵn sàng sử dụng.
- Thư viện Tiếng Nhật hiển thị số giọng đã cài và số giọng đang chờ tải model.
- Giữ nguyên kiểm tra license ACML trước khi tải Aivis.

## Tổng khả năng giọng

- English US: 20
- English UK: 8
- Japanese Kokoro: 5
- Japanese Aivis tùy chọn: 6
- Tổng speaker khả dụng sau khi cài đầy đủ Aivis: 39

## Cập nhật

Phát hành dưới dạng ZIP delta `1.4.0 -> 1.4.1`, giữ checksum preflight, transactional write, persistent rollback và khả năng reapply như 1.4.0.
