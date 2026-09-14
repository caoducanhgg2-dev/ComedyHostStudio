# SRT Voice Studio 1.2.0 — nghiệm thu tự động đã hoàn tất

Baseline: source và installer 1.1.0 đã xác minh, commit `33fea46f83c3ab360ece2567915412037b5ecbf3`.

Source code 1.2.0 đã được build/kiểm thử Windows tại commit `18143e9844b6b9e73b737723a22f1213c07c98bc`.
Lượt chạy xác minh: `34822400144` — SUCCESS.
Nhánh đóng băng hồ sơ release: `release/srt-voice-studio-1.2.0`.

## Kết quả cuối của nghiệm thu tự động

- 103/103 pytest đạt, 0 lỗi, 0 bỏ qua; 69.295 giây.
- Frozen app, self-test, FFmpeg filters và build installer: PASS.
- Nâng cấp tại chỗ từ 1.1.0: PASS.
- Cài sạch: PASS.
- Offline A/B/C + render English US/Japanese: PASS.
- Unicode/Vietnamese/Japanese path: PASS.
- Batch 1/5/20 file: PASS; file lỗi không dừng hàng đợi; retry PASS.
- Underfill V2: PASS; START không đổi; overlap 0.
- Stress 74 caption English US/Japanese: 74/74 hợp lệ, overlap 0.
- 5 giọng Nhật Kokoro: real TTS + A/B/C PASS.
- Aivis Mao/Kohaku optional pack: native style + shared A/B/C fit PASS; stress overlap 0; START không đổi.
- Upgrade/uninstall và clean/uninstall: PASS.

Installer đã xác minh: `SRTVoiceStudio_Setup_1.2.0.exe`, 465403067 byte.
SHA-256: `48C10CBB68B09E2458D651F6057B592DFDF88C8F6B947425761A41F9A3FBE132`.

## Phần không được tự chứng nhận

Bộ benchmark hiện có 27 giọng kỹ thuật đạt nhưng `ratings.csv` chưa có điểm nghe của con người. Vì vậy không tự gán 8/10, 9/10, KEEP/REJECT theo chất lượng cảm nhận hoặc nhãn Đề xuất. Phong cách bản địa của cùng một speaker không được tính thành giọng mới.

Trạng thái chính xác: **AUTOMATED WINDOWS ACCEPTANCE VERIFIED**; **VOICE NATURALNESS NOT HUMAN-CERTIFIED**.

Chi tiết đầy đủ nằm trong `RELEASE_1.2.0.md`, `VOICE_RESEARCH_1.2.md` và artifact của run `34822400144`.
