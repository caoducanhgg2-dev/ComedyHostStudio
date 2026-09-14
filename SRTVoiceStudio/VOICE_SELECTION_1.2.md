# Voice Selection — SRT Voice Studio 1.2.0

Mục tiêu của tài liệu này là tách rõ **giữ vì tương thích/kỹ thuật** và **đề xuất vì chất lượng nghe**. Không dùng số lượng giọng để thay cho chất lượng.

## KEEP — baseline tương thích

Giữ 20 giọng English US Kokoro và 5 giọng Japanese Kokoro đã có từ baseline. Lý do: bảo toàn tương thích 1.1.0, technical benchmark đạt, real TTS/A-B-C đạt. Đây **không** phải chứng nhận rằng tất cả đều đạt 8/10 hoặc 9/10 về naturalness.

English US: Heart, Alloy, Aoede, Bella, Jessica, Kore, Nicole, Nova, River, Sarah, Sky, Adam, Echo, Eric, Fenrir, Liam, Michael, Onyx, Puck, Santa.

Japanese: Alpha, Gongitsune, Nezumi, Tebukuro, Kumo.

## EXPERIMENTAL KEEP — gói tùy chọn

Aivis Mao và Kohaku được giữ dưới dạng gói tùy chọn. Technical acceptance: native style PASS, A/B/C shared fit PASS, stress 74 caption overlap 0, START không đổi. Việc sử dụng phải tuân theo ACML và yêu cầu ghi nguồn tương ứng.

Hai speaker này chưa được gắn nhãn Recommended vì chưa có điểm nghe người dùng.

## REJECT / DEFER trong 1.2.0

- Piper Ryan high: không đưa vào mặc định do giấy phép NC của model cụ thể.
- Piper LJSpeech high: DEFER; chưa có benchmark nghe tương đương.
- MeloTTS: DEFER; chưa tích hợp/baseline benchmark đủ để kết luận tốt hơn.
- VOICEVOX: DEFER; giấy phép phải xét theo từng nhân vật, không suy từ engine.
- COEIROINK / MYCOEIROINK: DEFER; không tái đóng gói trong 1.2.0, điều khoản từng giọng cần giữ riêng.

## Trạng thái quality recommendation

Artifact Voice Auditions có 27 giọng, `benchmark.json`, A/C audio, `index.html` và `ratings.csv`. `ratings.csv` hiện chưa có điểm; `listening_certified=false`.

Trọng số chấm: naturalness 35%, pronunciation 25%, expression 15%, speed-fit 10%, audio quality 10%, popularity 5%.

- Recommended: chỉ khi điểm nghe đủ dữ liệu >= 8/10.
- Top tier: chỉ khi >= 9/10.
- Hiện tại: **không có giọng nào được tự gắn Recommended/Top tier**.

Sau khi người dùng nghe và điền `ratings.csv`, app sẽ nạp điểm để chốt KEEP/REJECT/RECOMMENDED theo chất lượng thật. Technical PASS không được dùng thay cho nghe thử.
