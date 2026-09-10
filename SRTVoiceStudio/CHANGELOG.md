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
