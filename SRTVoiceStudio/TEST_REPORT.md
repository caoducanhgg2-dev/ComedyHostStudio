# SRT Voice Studio 1.1.0 — Báo cáo nghiệm thu

Ngày: 10/09/2026. Trạng thái: **ĐẠT toàn bộ nghiệm thu tự động trên Windows**. Chưa chứng nhận chất lượng giọng bằng nghe thử của con người.

## Bản bàn giao

- Installer: `SRTVoiceStudio_Setup_1.1.0.exe` — 460.817.533 byte.
- SHA-256: `02d2cc3ef9876608713a8a43e7f795ba30051800c4e9b9de207f209195d4f2a7`.
- Source dùng để build: [commit 33fea46](https://github.com/caoducanhgg2-dev/ComedyHostStudio/tree/33fea46f83c3ab360ece2567915412037b5ecbf3/SRTVoiceStudio).
- [Lượt build và nghiệm thu thành công](https://github.com/caoducanhgg2-dev/ComedyHostStudio/actions/runs/34472581469).
- File được chuyển theo từng phần rồi ghép nguyên trạng; SHA-256 toàn bộ EXE khớp checksum của lượt build. Không dùng binary từ lần build lỗi.

## Nâng cấp đã tích hợp

Giữ baseline 1.0.0, Kokoro/ONNX CPU, Japanese G2P và nguyên tắc timeline. Ảnh mockup chỉ được dùng làm tham chiếu giao diện.

Pipeline: SRT → Kokoro TTS → Emotion → Voice Effect → đo duration → Underfill/Overflow Fit và Adaptive Speed → Safe Trim nếu cần → Timeline Validator → Master PCM → một MP3.

- 12 Emotion Presets, 3 mức; 16 lựa chọn Voice Effects (gồm không hiệu ứng), 3 mức. Emotion là xử lý DSP, không phải mô hình cảm xúc gốc mới.
- Auto Emotion có quy tắc riêng cho Anh/Nhật; không viết lại lời thoại.
- A giữ audio TTS gốc; B xử lý từ cùng A; C và Generate dùng chung engine fit.
- Underfill giảm tốc thích ứng, giới hạn tốc độ hiệu dụng 0,88–1,20×; ưu tiên tối đa 1,15× khi tăng tốc thông thường. Không dịch START hoặc caption sau lên trước.
- Mục tiêu im lặng cuối khung khoảng 0,20s khi khả thi; cảnh báo khi trên 0,40s. Khoảng lặng còn lại tại 0,88× được chấp nhận và không tính thành overlap.
- UI tiếng Việt, nền navy, hai cột, tên giọng thân thiện, nút TẠO MP3, chỉ số A/B/C và báo cáo Underfill. Cửa sổ theo kích thước màn hình, nội dung dài cuộn được.
- Nghe thử trong RAM; output cuối là một MP3 48 kHz, mono, 192 kbps.

## Kết quả Windows

| Kiểm tra | Kết quả |
|---|---|
| Pytest toàn bộ | 74/74 đạt, 0 lỗi, 0 bỏ qua; 55,94s |
| FFmpeg thực tế | Đủ các filter DSP yêu cầu |
| EXE đã đóng gói | Self-test đạt trước tạo installer |
| Emotion / FX | 12 × 3 / 16 × 3 đạt |
| A/B/C thực tế trên app đã cài | Đạt; dùng lại A, C fit, cảnh báo Underfill và Generate |
| 5 giọng Nhật | TTS thật và A/B/C đạt |
| Chạy offline | App, FFmpeg, FFprobe bị chặn mạng; không dựa Python hệ thống |
| Nâng cấp từ installer 1.0.0 đã xác minh | Đạt; giữ AppId và thư mục D:\LỒNG TIẾNG\SRT Voice Studio |
| Cài mới | Đạt; version 1.1.0, tên SRT Voice Studio |
| Đường dẫn tiếng Việt / tên file Nhật | Đạt |
| Gỡ cài cả hai trường hợp | Xóa EXE và mục uninstall thành công |
| Dọn file tạm | Đạt |

Các lượt build trước từng bị chặn bởi tên uninstall, file preview còn lại và một lần kiểm thử UI thất bại ở chuyển A sang B. Chỉ lượt build thành công nêu trên là căn cứ nghiệm thu bản bàn giao; không suy diễn rằng một lần chạy đạt loại trừ mọi lỗi thời điểm trong tương lai.

## EN7 — regression với đúng SRT thực tế

Nguồn: `EN7_US_Comedy_Reviewer_V2.srt`, SHA-256 `2b9dde758c241d0dfa506ace134556d095d77a15e49bd7acd3281fb61ba9204f`.
30 caption; 4,008–4,009s/khung; 8,033 từ/caption; gap đúng 0,100s.

So sánh renderer 1.0 nguyên trạng với engine 1.1.0, dùng **cùng 30 audio Kokoro gốc**, voice `am_michael`. Đây là so sánh có kiểm soát; không giả định voice của MP3 cũ người dùng gửi.

| Chỉ số | Renderer 1.0 | Renderer 1.1.0 |
|---|---:|---:|
| Im lặng cuối khung trung bình | 0,762792s | 0,450707s |
| Im lặng cuối khung tối đa | 1,561750s | 1,233875s |
| Giảm trung bình | — | 40,91% |
| Caption giảm tốc | — | 25 |
| Caption tăng tốc | — | 2 |
| Caption Safe Trim | — | 1 |
| Caption còn underfill ở giới hạn 0,88× | — | 14 |
| Overlap | 0 | 0 |

Toàn bộ START không đổi, không đẩy caption sớm, tốc độ giữ trong giới hạn. Mỗi lần render chỉ có một MP3 cuối. Khoảng lặng đo ở đây là từ cuối audio đã fit đến cuối slot, không cộng gap SRT 0,10s.

**Không đạt mục tiêu 0,10–0,30s cho mọi câu**: vẫn còn 14 câu trên 0,40s tại tốc độ tối thiểu. Ví dụ 2,80s / 0,88 ≈ 3,18s, vẫn còn khoảng 0,82s trong khung 4s. Không ép giọng chậm thêm hoặc di chuyển START để làm đẹp chỉ số.

Đo riêng MP3 cũ người dùng gửi bằng khung RMS 10ms, ngưỡng -50 dBFS: im lặng cuối slot trung bình 0,7152s, tối đa 1,349s; 8/30 câu trên 1s. Đây là ước lượng theo tín hiệu, không đồng nhất với số đo duration của benchmark hoặc đánh giá cảm nhận bằng tai.

## Stress test TTS thật

74 câu mỗi ngôn ngữ, Auto Emotion + Cave mạnh, timeline dài 227s. Các con số có Safe Trim nhằm kiểm tra giới hạn; không dùng làm chứng nhận chất lượng nội dung khi cắt lời thoại.

| Chỉ số | English US | Japanese |
|---|---:|---:|
| Caption hợp lệ | 74/74 | 74/74 |
| Overlap | 0 | 0 |
| Im lặng cuối khung trung bình | 0,113272s | 0,164394s |
| Tối đa | 0,256125s | 0,310792s |
| Tăng tốc / giảm tốc | 37 / 25 | 25 / 13 |
| Safe Trim | 37 | 0 |

## Giới hạn nghiệm thu

Kiểm thử trên Windows runner của GitHub Actions, không thay thế thử nghiệm trên mọi máy Windows 10/11. Giữ pitch bằng atempo và giới hạn tốc độ đã được kiểm tra; độ tự nhiên, sắc thái cảm xúc và mức chấp nhận khi Safe Trim cần nghe đánh giá. Không ghi nhận chất lượng nghe là đã được con người chứng nhận.

Cài đặt: chạy EXE, cài đè bản 1.0.0 nếu có; mở SRT Voice Studio, chọn SRT và giọng, nghe A/B/C, sau đó TẠO MP3. Cảnh báo thiếu lời thoại có thể còn xuất hiện với câu ngắn dù timeline vẫn hợp lệ.
