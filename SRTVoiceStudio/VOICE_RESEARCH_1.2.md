# Giọng và giấy phép — SRT Voice Studio 1.2

Trạng thái: ứng viên phát hành, chưa xác nhận chất lượng bằng nghe chấm. Không có điểm 8/10, 9/10 hay nhãn Đề xuất được tự tạo.

| Hệ giọng | Kết quả tích hợp | Căn cứ |
|---|---|---|
| Kokoro | Giữ 20 giọng Anh Mỹ và 5 giọng Nhật gốc; benchmark cùng văn bản | [Model Apache-2.0](https://huggingface.co/hexgrad/Kokoro-82M), [danh sách giọng](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md). Phân hạng trên model card không được coi là điểm nghe của ứng dụng. |
| Aivis | Gói tùy chọn Mao và Kohaku; phong cách nằm dưới cùng một giọng | [Engine LGPL-3.0](https://github.com/Aivis-Project/AivisSpeech-Engine), [ACML 1.0](https://github.com/Aivis-Project/ACML/blob/master/ACML-1.0.md). Có điều kiện sử dụng thương mại; không mặc định đề xuất cho nội dung phê phán người/tổ chức/sản phẩm thật. |
| Piper | Chưa tích hợp; Ryan high bị loại khỏi tập mặc định vì NC | [Engine GPL-3.0](https://github.com/OHF-Voice/piper1-gpl), [Ryan model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ryan/high/MODEL_CARD). LJSpeech high là ứng viên cần thử tiếp, không có điểm chất lượng trong bản này. |
| MeloTTS | Chưa tích hợp, chưa có benchmark tương đương để khẳng định tốt hơn | [Mã nguồn MIT](https://github.com/myshell-ai/MeloTTS), [model Nhật MIT](https://huggingface.co/myshell-ai/MeloTTS-Japanese). |
| VOICEVOX | Chưa đóng gói; giấy phép từng nhân vật phải được xét riêng | [Điều khoản chính thức](https://voicevox.hiroshiba.jp/term/). Không suy giấy phép mọi giọng từ giấy phép engine. |
| COEIROINK / MYCOEIROINK | Không tái đóng gói model/phần mềm; chưa tích hợp API local riêng | [Điều khoản chính thức](https://coeiroink.com/terms). Điều kiện từng giọng và yêu cầu ghi nguồn cần giữ nguyên. |

Aivis còn dùng BERT ONNX của tsukumijima, chuyển đổi từ ku-nlp, theo [CC-BY-SA-4.0](https://huggingface.co/tsukumijima/deberta-v2-large-japanese-char-wwm-onnx). Revision cố định: d701ec67708287b20d2063270f6b535e6eed09ab. Các tệp tải được giữ nguyên; manifest lưu nguồn và SHA-256. Ghi nguồn gợi ý cho audio: `AivisSpeech: まお` hoặc `AivisSpeech: コハク`. ACML có các giới hạn ngoài việc ghi nguồn; đọc toàn bộ giấy phép trước khi sử dụng.

## Bộ nghe thử

`VoiceBenchmarks/index.html` mở các đoạn A gốc và C sau căn mốc; mỗi giọng dùng cùng tám nhóm văn bản: đối thoại, review, hài nhẹ, kể chuyện, câu ngắn, câu dài, số/tên riêng và dấu câu. Văn bản Nhật chứa kana và kanji. `benchmark.json` ghi thời gian xử lý, khoảng lặng và kiểm tra overlap. `ratings.csv` để trống các điểm chưa nghe chấm.

Trọng số: tự nhiên 35%, phát âm 25%, biểu cảm 15%, phù hợp sau căn tốc độ 10%, chất lượng audio 10%, độ phổ biến 5%. Không suy điểm phát âm/tự nhiên từ RMS, thời lượng, độ phổ biến hoặc số lượt tải. Chỉ xét Đề xuất khi có điểm nghe đủ dữ liệu >=8; nhóm tốt nhất cần >=9. Hiện chưa có giọng nào được chấm theo quy trình này.

Mục tiêu số lượng không được dùng để thêm giọng kém hoặc giấy phép không phù hợp. Bản này bảo toàn các giọng cũ và cung cấp hai giọng Nhật thử nghiệm; chưa đạt mục tiêu thư viện Nhật 10–15 giọng đã được tuyển chọn bằng nghe.
