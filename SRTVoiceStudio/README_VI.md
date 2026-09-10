# SRT Voice Studio 1.1.0

**Trạng thái build: xem GitHub Actions trên nhánh `srt-voice-studio/1.1.0`.**
Chỉ tải bộ cài từ lần chạy đã đạt toàn bộ kiểm thử. File `acceptance.json` đi kèm artifact ghi kết quả thực thi của đúng bộ cài đó.

## Sử dụng bản đã đóng gói

1. Chạy `SRTVoiceStudio_Setup.exe`, bấm Next → Install → Finish.
2. Mở SRT Voice Studio từ Start Menu hoặc shortcut.
3. Browse/kéo vào một SRT UTF-8. Chọn English US hoặc Japanese và voice.
4. Mặc định Manual / Natural / None giữ giọng sạch. Có thể chọn Emotion / Performance, Intensity, Voice Effect và Strength. Auto dùng rule local riêng cho English và Japanese.
5. A Original nghe TTS gốc; B Processed dùng cùng audio A qua DSP. Đổi style không tổng hợp lại A. Chọn Preview Caption trong SRT để nghe C Final Timeline sau fit/trim/normalize. Sửa Preview Text sẽ trở về custom và tắt C.
6. C hiển thị slot, độ dài A/B/C, effective speed, trim và overlap. Safe Trim có thể cắt mất từ cuối câu; nghe C để kiểm tra.
7. Bấm GENERATE MP3, chọn nơi lưu. Kết quả duy nhất là `TênFile_Voice.mp3`.

Bộ cài chứa runtime, Qt, model Kokoro, toàn bộ voice, từ điển và FFmpeg/FFprobe.
Không tải Python hoặc model khi cài/chạy. Không tài khoản, không API key, không CUDA.
Windows 10/11 x64 là mục tiêu. Bản đầu dùng CPU, giới hạn tối đa 6 luồng ONNX.

## Timeline và giới hạn thực tế

- START khóa theo SRT, tính bằng mẫu tại 48 kHz; không dịch caption sau.
- END an toàn = min(END SRT, START câu kế − minimum gap).
- Gap: 0/0,05/0,10/0,15/0,20 giây; mặc định 0,10.
- TTS đọc ở tốc độ gốc, đo audio, rồi dùng FFmpeg `atempo` giữ cao độ.
- Adaptive ưu tiên tối đa 1,15x; dùng đến 1,20x khi cần. Không vượt 1,20x tổng.
- Safe Trim có thể **cắt mất từ cuối câu**; giao diện và log báo số câu đã cắt.
- Stop and Report dừng trước export nếu audio vẫn vượt slot.
- Nếu START trùng, đảo thứ tự, hoặc gap làm slot ≤ 0: báo caption lỗi, không xóa câu hay dịch timeline.
- Khoảng im lặng đầu và giữa các câu được giữ. Nếu voice ngắn hơn slot, phần còn lại là im lặng;
  Minimum Gap là khoảng nghỉ tối thiểu, không phải cam kết mọi khoảng nghỉ đúng 0,10 giây.
- Master PCM kết thúc tại END lớn nhất trong SRT. Chỉ encode MP3 192 kbps/48 kHz/mono một lần.
- Validator kiểm tra ranh giới vùng PCM, không phải độ chính xác âm học từng từ.
- MP3 có encoder delay/padding và hiệu ứng nén vài mili giây; metadata gapless được ghi.
  Không cam kết mọi phần mềm hiển thị thời lượng MP3 tuyệt đối bằng thời lượng PCM.
- Normalize dùng active-RMS và giới hạn peak từng caption, không phải chứng nhận LUFS broadcast.

## Voice thật

English nữ: af_heart, af_alloy, af_aoede, af_bella, af_jessica, af_kore,
af_nicole, af_nova, af_river, af_sarah, af_sky.

English nam: am_adam, am_echo, am_eric, am_fenrir, am_liam, am_michael,
am_onyx, am_puck, am_santa.

Japanese nữ: jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro.
Japanese nam: jm_kumo.

Giữ tên model thật, không gán nhãn giả như “comedy voice”. Kokoro không cung cấp điều khiển
diễn xuất comedy/reviewer riêng; hãy dùng Preview để chọn chất giọng hợp với lời thoại.
Tiếng Nhật dùng Misaki/Cutlet + fugashi + UniDic Lite để tạo âm vị Nhật, không dùng phonemizer Anh.
Tiếng Anh dùng phonemizer eSpeak-ng do kokoro-onnx hỗ trợ. Chất lượng giọng cần nghe nghiệm thu thực tế.

## Cấu trúc kỹ thuật

`studio/timeline.py`: parser, slot và validator độc lập.
`studio/backend.py`: model singleton dùng lại giữa các caption/tác vụ, voice và G2P.
`studio/render.py`: disk-backed master PCM, adaptive fit, staging MP3 và publish nguyên tử.
`studio/audio.py`: subprocess dạng argument list, cancel FFmpeg, resample, atempo, normalize.
`studio/ui.py`: PySide6 + worker thread, preview, progress, cancel, báo lỗi.
`studio/diagnostics.py`: sinh audio thật để kiểm tra English/Japanese và encoder.

Dữ liệu làm việc: `%LOCALAPPDATA%\SRTVoiceStudio\Temp`.
Log: `%LOCALAPPDATA%\SRTVoiceStudio\logs\latest.log`.
Model nằm trong thư mục runtime của app, đọc offline; không cần cache tải về lần đầu.
Chỉ cho mở một instance để tránh dọn temp của tác vụ đang chạy.
Cancel đợi lượt inference đang chạy kết thúc; FFmpeg có thể được dừng ngay.
Khi đóng cửa sổ trong lúc render, app yêu cầu chờ hủy xong rồi đóng lại.

## Build Windows tự động (dành cho người phát triển)

Workflow: `.github/workflows/windows-build.yml`, runner `windows-latest`, Python 3.12.10 x64.

1. Cài wheel từ `requirements-windows.lock` với hash SHA-256 và version cố định.
2. Cài UniDic Lite 1.0.8: package dữ liệu thuần, wheel được tạo ở máy build, không cần C/C++.
3. `prepare_assets.py` tải model và FFmpeg release cố định vào project, có retry/resume.
4. Chạy pytest (synth giả nhưng ghép PCM/mã hóa/giải mã FFmpeg thật).
5. PyInstaller one-folder: đóng gói runtime riêng, không lệ thuộc Python hệ thống.
6. Inno Setup: một file `SRTVoiceStudio_Setup.exe`, cài theo user, có uninstaller.
7. Cài ở đường dẫn Unicode; chạy executable với PATH bỏ Python và chặn mạng bằng firewall.
8. Self-test English/Japanese thật, preview qua cùng đường synth, thời lượng, silence, GUI smoke;
   sau đó uninstall và kiểm tra executable đã bị gỡ.
9. Chỉ upload installer khi mọi gate đạt; luôn lưu log build để sửa lỗi nếu có.

Repo phải có Actions được bật và công cụ kết nối phải có quyền ghi workflow.
Workflow đã được chạy trên GitHub Actions. Xem kết quả của từng lần chạy, không suy luận trạng thái chỉ từ mã nguồn.
Runner là Windows Server của GitHub; gate này không thay thế thử nghiệm trên Windows 10/11 máy sạch.
Test GUI tự động không kiểm tra âm thanh qua loa hay chất lượng giọng bằng tai.

## Kiểm thử đã chạy tại Work

Xem `TEST_REPORT.md`. Không đánh đồng test timeline dùng synth giả với test mô hình TTS thật.

## Nguồn kỹ thuật

- https://github.com/thewh1teagle/kokoro-onnx
- https://github.com/hexgrad/misaki
- https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- https://pypi.org/project/fugashi/1.4.0/
- https://pypi.org/project/PySide6/6.8.3/
- https://github.com/GyanD/codexffmpeg/releases/tag/7.1.1
- https://pyinstaller.org/en/stable/operating-mode.html

Không đưa API key, token hoặc thông tin riêng vào repo.

## Emotion và FX 1.1.0

Kokoro không có tham số emotion native. Các Performance preset là DSP pitch, EQ, dynamics và tempo; Whisper-like chỉ mô phỏng timbre. Auto Emotion dùng từ khóa/dấu câu, có thể chọn sai ngữ cảnh; Manual cho phép kiểm soát trực tiếp.

FX được áp trước khi đo độ dài và căn slot, gồm cả đuôi Echo/Reverb/Cave. Tổng effective speed (emotion, user speed, fit) không vượt 1.20x. Khi slot quá ngắn, Safe Trim ưu tiên timeline và fade cuối 5 ms; Stop and Report dừng và giữ nguyên MP3 cũ.

A/B/C chỉ phát audio tạm, không xuất thêm file. Một file MP3 mono 48 kHz / 192 kbps được encode một lần từ master PCM. Không có API, cloud, GPU bắt buộc hay phụ thuộc cài ngoài.

Giao diện có vùng cuộn cấu hình; Generate, Cancel và báo cáo luôn nằm phía dưới. Xem `CHANGELOG.md`, `AUDIT_1.0.md` và kết quả acceptance của đúng build trước khi phát hành.
