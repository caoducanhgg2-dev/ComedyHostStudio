# Windows build đã xác minh — 09/09/2026

- GitHub Actions run: https://github.com/caoducanhgg2-dev/ComedyHostStudio/actions/runs/34382171196
- Commit build: 78fc14ffd4569906284584171f76894077310789
- Kết quả workflow: SUCCESS.
- 18 test parser/timeline/FFmpeg đạt trên Windows runner.
- Frozen app: English và tất cả 5 voice Japanese tạo audio thật thành công.
- Đường dẫn cài có dấu tiếng Việt, PATH không có Python, PYTHONHOME/PYTHONPATH giả, TEMP không tồn tại: đạt.
- Installer: cài, mở UI, sinh MP3 khi chặn mạng, gỡ cài: đạt.
- MP3 English/Japanese test: 9,420 giây, 0 overlap; giữ silence đầu file.
- SHA-256 installer: 108d022d41ddc53fd089b01ce0bfb6edeced385504829f73655cf3ca8c13f31a
- Kích thước installer: 460942537 byte.

Đã sửa lỗi native phonemizer khi cài ở đường dẫn Unicode bằng đường dẫn ngắn Windows
và manifest UTF-8. Không yêu cầu thay đổi thiết lập ngôn ngữ hệ thống.

Đây là kiểm thử tự động trên Windows runner, chưa thay thế nghiệm thu trên máy Windows 10/11
của người dùng và đánh giá giọng bằng tai. 74 caption dùng synth thử trong unit test;
không tuyên bố đã kiểm tra 74 caption bằng giọng thật.

---

## Nhật ký ban đầu trước khi build Windows

# Báo cáo kiểm tra — 09/09/2026

## Đã thực thi tại Work (Linux x86_64, Python 3.12)

`python -m pytest -q --junitxml=test-results.xml`

**18 passed in 27.05s.** Chi tiết máy đọc được trong `test-results.xml`.

| Hạng mục | Kết quả / phạm vi |
| --- | --- |
| UTF-8 BOM, CRLF, multiline Japanese | Đạt |
| Timestamp, index, cấu trúc SRT lỗi | Báo lỗi caption; 7 trường hợp đạt |
| Slot âm/0 do minimum gap | Báo lỗi trước TTS |
| SRT có END chồng START kế | Thu hẹp slot đúng công thức |
| Validator vùng PCM vượt ranh giới | Từ chối export |
| 10 và 74 caption | Đạt, overlap = 0; nguồn synth giả 440 Hz |
| MP3 encode/decode | FFmpeg thật, 48 kHz, mono, 192 kbps |
| Bắt đầu ở 5 giây | Kiểm tra silence của MP3 giải mã đến 4,97 giây |
| Thời lượng toàn cục | MP3 giải mã lệch dưới 50 ms so với master |
| Tăng tốc / Safe Trim | Đạt với nguồn synth giả quá dài |
| Stop and Report | Đạt; không ghi đè MP3 cũ khi render lỗi |
| Cancel | Không tạo output khi hủy trước render |
| Tên Nhật / thư mục tiếng Việt có khoảng trắng | Đạt trên Linux |
| Dọn audio tạm sau thành công | Đạt |
| Japanese G2P thực | Misaki/Cutlet tạo âm vị Nhật; không dùng âm vị Anh |

Đã import thực `kokoro_onnx.Kokoro`, `PySide6` và `misaki.cutlet.Cutlet`.
Đã mở giao diện bằng `QT_QPA_PLATFORM=offscreen python main.py --ui-smoke`, exit code 0.
Đã chụp và kiểm tra bố cục giao diện ở kích thước 760 × 970.
Linux này không có thiết bị phát âm thanh khả dụng; chưa kiểm tra playback qua loa.

## Dependency audit

Đã dùng pip resolver với target `win_amd64`, CPython 3.12 và `--only-binary=:all:`.
33 package đã phân giải thành version cố định và hash wheel trong `requirements-windows.lock`.
Package dữ liệu thuần UniDic Lite 1.0.8 được xây wheel riêng ở máy build, không cần compiler C/C++.
Không cài `pyopenjtalk`, không có `tkinter`, không có Torch trong kiến trúc chọn.

## Chưa thực thi / không được tuyên bố đã đạt

- Tải/nạp model và sinh giọng Kokoro English/Japanese thật.
- Nghe thử và đánh giá giọng natural/deep/energetic/comedy theo cảm nhận.
- Build PyInstaller Windows và chạy installer Inno Setup.
- Cài và gỡ trên Windows 10/11 sạch.
- Chạy với nhiều bản Python có sẵn, mất mạng và TEMP không tồn tại trên Windows.
- Chứng nhận không trùng voice bằng nghe/nhận dạng từ trong MP3 cuối.

Môi trường Work chạy Linux; tải trực tiếp release model GitHub bị timeout.
Connector GitHub hiện đọc/ghi repository nhưng không có thao tác tạo repository mới.
Đã xác minh kết nối GitHub và các repository hiện có; chưa chọn nơi ghi code nên chưa push/dispatch.
**Chưa tạo `SRTVoiceStudio_Setup.exe`. Không có Windows build nào được báo thành công.**

## Các gate đã viết để chạy trên GitHub Actions

Windows wheels → bundle models/FFmpeg → pytest → PyInstaller → Inno Setup → install tại
đường dẫn có dấu → chặn mạng cho app → self-test synth English/Japanese và tất cả 5 voice Nhật →
MP3 timeline/silence → GUI smoke → uninstall → upload installer chỉ khi thành công.

Các gate là mã kiểm thử đã chuẩn bị, không phải bằng chứng đã chạy.
Windows-latest là runner Windows Server; vẫn cần nghiệm thu trên máy Windows 10/11 thật.
