# SRT Voice Studio 1.2.0 — Release Handoff

Ngày chốt nghiệm thu tự động: 14/09/2026.

## Trạng thái

**AUTOMATED WINDOWS ACCEPTANCE: VERIFIED.**

Bản 1.2.0 đã vượt qua build, cài sạch, nâng cấp tại chỗ từ 1.1.0, chạy offline, A/B/C, batch queue, Underfill V2, stress 74 caption, Unicode/Japanese path và uninstall trên Windows runner.

**VOICE NATURALNESS: CHƯA CHỨNG NHẬN BẰNG NGHE NGƯỜI.** Không tự gán điểm 8/10, 9/10 hoặc nhãn Đề xuất cho giọng chưa được chấm trong `ratings.csv`.

## Bản build đã xác minh

- Source code dùng để build: `18143e9844b6b9e73b737723a22f1213c07c98bc`.
- Nhánh phát triển: `srt-voice-studio/1.2.0`.
- Nhánh đóng băng release: `release/srt-voice-studio-1.2.0`.
- GitHub Actions run: `34822400144` — `Build SRT Voice Studio Windows` — SUCCESS.
- Installer: `SRTVoiceStudio_Setup_1.2.0.exe`.
- Kích thước installer: `465403067` byte.
- SHA-256 installer: `48C10CBB68B09E2458D651F6057B592DFDF88C8F6B947425761A41F9A3FBE132`.
- Baseline 1.1.0 được xác minh bằng SHA-256: `02d2cc3ef9876608713a8a43e7f795ba30051800c4e9b9de207f209195d4f2a7`.

## Kết quả test source và đóng gói

- Pytest Windows: **103/103 đạt**, 0 failures, 0 errors, 0 skipped; 69.295 giây.
- FFmpeg bundled filters: PASS (`acompressor`, `aecho`, `aresample`, `asetrate`, `asoftclip`, `atempo`, `equalizer`, `highpass`, `lowpass`, `tremolo`, `vibrato`).
- Frozen app self-test: PASS.
- Build installer: PASS.
- Upgrade từ installer 1.1.0 đã xác minh: PASS.
- Clean install: PASS.
- Offline A/B/C + render thực tế: PASS.
- Unicode/Vietnamese/Japanese path: PASS.
- Uninstall: PASS ở cả upgrade và clean scenario.

## Batch Queue

- Batch 1 file: 1/1 hoàn tất, overlap 0, START không đổi.
- Batch 5 file: 5/5 hoàn tất, overlap 0, START không đổi.
- Batch 20 file: 20/20 hoàn tất, overlap 0, START không đổi.
- Một file lỗi không dừng các mục sau: PASS.
- Retry mục lỗi/hủy: PASS.
- Mỗi SRT có output riêng và tránh ghi đè tên file.

## Timeline / Underfill V2

Nguyên tắc release vẫn giữ: **không dịch START**, **OVERLAP = 0**, tốc độ hiệu dụng trong giới hạn 0,88–1,20×.

Stress 74 caption:

| Ngôn ngữ | Hợp lệ | Overlap | Im lặng cuối TB | Lớn nhất | Underfill sau hard-min |
|---|---:|---:|---:|---:|---:|
| English US | 74/74 | 0 | 0.103272s | 0.256125s | 0 |
| Japanese | 74/74 | 0 | 0.157068s | 0.310792s | 0 |

Regression EN7 46 caption dùng cùng cached TTS giữa baseline/final: START không đổi, overlap 0, target gate PASS. Khoảng lặng trung bình giảm từ 0.267916s xuống 0.247293s. Một số câu quá ngắn vẫn có khoảng lặng lớn khi đã chạm 0,88×; ứng dụng giữ timeline thay vì kéo chậm quá giới hạn.

Bộ 30 caption/8 từ/~4,008s/gap 0,10s: khoảng lặng trung bình giảm từ 0.762792s xuống 0.438656s (42,49%); overlap 0. Còn 5 caption underfill tại hard minimum 0,88×, được báo đúng thay vì phá START.

## Voice library

- 20 giọng English US Kokoro: giữ nguyên để tương thích.
- 5 giọng Japanese Kokoro: real TTS + A/B/C PASS.
- Aivis tùy chọn: Mao + Kohaku; native style PASS, A/B/C shared fit PASS, stress 74 caption overlap 0, START không đổi.
- Tổng 27 giọng trong voice benchmark: technical checks PASS.
- `ratings.csv` hiện để trống điểm nghe; `listening_certified=false`.
- Không tính style của cùng một speaker thành giọng mới.
- Không tự tuyển thêm giọng chỉ để đạt số lượng nếu giấy phép hoặc chất lượng chưa đủ căn cứ.

## Hồ sơ bàn giao

Các artifact của run 34822400144 gồm:

- `SRTVoiceStudio_Setup_1.2.0` — installer + `SHA256SUMS.txt` + `acceptance.json` + test XML + filter validation.
- `SRTVoiceStudio_1.2_EN7_MP3` — MP3 regression thực.
- `SRTVoiceStudio_1.2_Voice_Auditions` — A/C listening pack, `index.html`, `benchmark.json`, `ratings.csv`.
- `build-diagnostics` — logs, batch/underfill/voice reports và screenshot UI.

## Điều kiện để gắn nhãn FINAL VOICE VERIFIED

Chỉ còn bước đánh giá nghe: mở bộ Voice Auditions, chấm `ratings.csv` theo 6 tiêu chí, nạp lại vào app và chốt danh sách KEEP/REJECT/RECOMMENDED. Việc này là đánh giá cảm nhận, không được thay bằng chỉ số RMS, thời lượng hoặc test kỹ thuật.

Cho đến khi có điểm nghe thật, trạng thái chính xác của 1.2.0 là: **installer và chức năng đã nghiệm thu tự động; chất lượng giọng chưa được con người chứng nhận**.
