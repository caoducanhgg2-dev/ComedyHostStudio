# SRT Voice Studio 1.3.1

- Chuyển cơ chế cập nhật từ chạy lại installer EXE sang **ZIP delta**.
- Gói cập nhật chỉ chứa file mới/thay đổi so với bản 1.3.0 đã phát hành; workflow từ chối nếu vô tình đóng gói toàn bộ app.
- `Apply_Update.cmd` gọi PowerShell updater, tự tìm thư mục cài, yêu cầu đóng app, kiểm tra SHA-256 baseline trước khi ghi đè và cập nhật `DisplayVersion` sau khi thành công.
- Có rollback file trong phiên cập nhật nếu bước ghi/verify thất bại.
- CI tải đúng artifact installer 1.3.0 từ run đã nghiệm thu, kiểm tra checksum, cài im lặng vào staging rồi dùng chính các byte đã cài làm baseline cho ZIP delta.
- Acceptance kiểm tra thư mục Unicode, kết quả app sau patch khớp byte-for-byte với build 1.3.1, chạy patch lần hai không đổi kết quả, baseline bị sửa phải bị từ chối trước khi ghi đè, và file uninstall do Inno Setup quản lý vẫn được giữ nguyên.
- Không chạy Inno Setup trong luồng phát hành update 1.3.1; installer 1.3.0 chỉ giữ vai trò bản cài đầy đủ ban đầu.

# SRT Voice Studio 1.3.0

- Thêm 8 speaker British English Kokoro chạy local/offline: Alice, Emma, Isabella, Lily, Daniel, Fable, George, Lewis.
- Thêm ngôn ngữ `English UK` / `Tiếng Anh (Anh)` và dùng G2P `en-gb`; voice US/UK không được chọn chéo vùng.
- Tổng Kokoro tích hợp sẵn tăng từ 25 lên 33 speaker: 20 US + 8 UK + 5 Japanese.
- Voice library lọc Tiếng Anh bao gồm cả US và UK; Favorites/ratings giữ nguyên ID cũ.
- Voice Auditions thêm bộ văn bản British English riêng và benchmark tối thiểu 35 speaker khi Aivis Mao/Kohaku đã cài.
- Self-test mới bắt buộc tạo audio thật cho toàn bộ 8 British voices và một render British theo timeline.
- Installer dùng cùng AppId để nhận vị trí cài cũ và giữ dữ liệu người dùng.
- Piper LJSpeech High chưa đóng gói vì Piper runtime hiện GPLv3; giữ ở trạng thái nghiên cứu cho đến khi hoàn tất phương án phân phối/giấy phép.

# SRT Voice Studio 1.2.0

Trạng thái: **AUTOMATED WINDOWS ACCEPTANCE VERIFIED** tại source commit `18143e9844b6b9e73b737723a22f1213c07c98bc`, GitHub Actions run `34822400144`.

- Xử lý SRT hàng loạt, cấu hình riêng, hủy/thử lại và tên đầu ra tránh ghi đè.
- Batch 1/5/20 file đã nghiệm thu; một file lỗi không dừng hàng đợi; retry PASS.
- Underfill V2 dùng chung với C Preview và render; giữ START, giới hạn 0,88–1,20×, overlap 0.
- Stress 74 caption English US/Japanese đạt 74/74 hợp lệ, overlap 0.
- Gói Aivis tùy chọn có checksum, Mao/Kohaku và phong cách bản địa; giữ model hiện có nếu xung đột thay vì ghi đè.
- Thư viện giọng, yêu thích, bảng điểm nghe có trọng số và bộ nghe thử A/C.
- 27 giọng có technical benchmark PASS; chưa tự chứng nhận naturalness vì `ratings.csv` chưa được người nghe chấm.
- Nâng cấp tại chỗ từ 1.1.0, bảo toàn dữ liệu người dùng; clean install và uninstall đều PASS.
- Installer: `SRTVoiceStudio_Setup_1.2.0.exe`, SHA-256 `48C10CBB68B09E2458D651F6057B592DFDF88C8F6B947425761A41F9A3FBE132`.
- Xem `RELEASE_1.2.0.md` để biết toàn bộ bằng chứng nghiệm thu và giới hạn chứng nhận chất lượng giọng.

# SRT Voice Studio 1.1.0

- Added 12 local Emotion / Performance presets with three intensities. Natural stays clean. Whisper-like is DSP, not a native whisper model.
- Added offline English/Japanese rule-based Auto Emotion without changing SRT text.
- Added 16 FX choices (including None) with three strengths, using existing bundled FFmpeg; no new runtime dependencies.
- Added immutable original-audio cache and A Original / B Processed / C Final Timeline previews. Style changes reuse A. C shares production fitting, overflow handling and validation.
- Effects run before fitting. Echo/Reverb/Cave tails cannot cross allowed end. Effective emotion + user + fit speed is capped at 1.20x.
- Added actual preset, cache, tail, preview, UI, 74-caption and upgrade acceptance gates.
- Retained app identity, install path, all 20 US and 5 Japanese voices, CPU/offline operation and a single final 48 kHz / 192 kbps MP3.

## Bổ sung trước bản cuối

- Underfill Voice Fit: nhắm im lặng cuối khung 0,20 giây; tốc độ tổng 0,88–1,20×,
  không thay START hoặc đẩy câu sau sớm hơn. Cảnh báo khi còn thiếu trên 0,40 giây.
- Thêm thống kê khoảng lặng trung bình/lớn nhất, câu giảm/tăng tốc, thiếu lời thoại
  sau giới hạn tối thiểu, cắt và chồng tiếng trong Preview C / kết quả.
- Thêm regression thực trên chính EN7_US_Comedy_Reviewer_V2.srt, dùng cùng audio gốc
  để so sánh renderer 1.0 và 1.1; giữ riêng mẫu mô phỏng 30 câu/8 từ/4 giây/gap 0,10.
- Việt hóa giao diện và tên lựa chọn; hai cột navy theo mockup, tên giọng thân thiện,
  nút TẠO MP3 và kết quả dễ đọc. Mã backend/voice không đổi.
- Nghe thử từ RAM để tránh file bị Qt giữ khóa trên Windows và còn sót thư mục tạm.
