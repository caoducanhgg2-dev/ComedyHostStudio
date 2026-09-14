# SRT Voice Studio 1.3.0 — đang nghiệm thu

- Thêm 8 speaker British English Kokoro chạy local/offline: Alice, Emma, Isabella, Lily, Daniel, Fable, George, Lewis.
- Thêm ngôn ngữ `English UK` / `Tiếng Anh (Anh)` và dùng G2P `en-gb`; voice US/UK không được chọn chéo vùng.
- Tổng Kokoro tích hợp sẵn tăng từ 25 lên 33 speaker: 20 US + 8 UK + 5 Japanese.
- Voice library lọc Tiếng Anh bao gồm cả US và UK; Favorites/ratings giữ nguyên ID cũ.
- Voice Auditions thêm bộ văn bản British English riêng và benchmark tối thiểu 35 speaker khi Aivis Mao/Kohaku đã cài.
- Self-test mới bắt buộc tạo audio thật cho toàn bộ 8 British voices và một render British theo timeline.
- Installer nâng version lên `1.3.0`; nghiệm thu upgrade bắt đầu từ đúng installer 1.2.0 đã xác minh bằng SHA-256.
- Piper LJSpeech High chưa đóng gói trong 1.3.0 vì Piper runtime hiện GPLv3; giữ ở trạng thái nghiên cứu cho đến khi hoàn tất phương án phân phối/giấy phép.
- Chưa gắn FINAL VERIFIED cho 1.3.0 cho tới khi GitHub Actions Windows hoàn tất toàn bộ clean install, upgrade, offline, benchmark và checksum.

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
