# Baseline audit — 10 September 2026

- Original installer build commit: `78fc14ffd4569906284584171f76894077310789`.
- Successful Windows run: https://github.com/caoducanhgg2-dev/ComedyHostStudio/actions/runs/34382171196
- Branch baseline: `9745decd226a2ba7f6d9d069ace8a5aae6d1583d`; its only changes after the build commit are README and test-report documentation.
- Existing version: 1.0.0. New version: 1.1.0.
- AppId unchanged: `{68F0C1C1-17CB-4CED-8261-5C18EB92571A}`.
- AppName unchanged: SRT Voice Studio. Default install path unchanged: LocalAppData/Programs/SRTVoiceStudio.
- Kokoro ONNX 0.6.1; model v1.0; ONNX Runtime 1.29.0; FFmpeg 7.1.1; PySide6 6.8.3; Python build 3.12.10; PyInstaller 6.16.0.
- Windows wheel lock and model preparation unchanged; no new runtime dependencies.
- Matched local Git blob hashes against baseline: UI, renderer, timeline, backend, installer, dependency lock.
- Before editing app code: 18 existing regression tests passed in 7.65 s on Linux. Includes Japanese G2P, real FFmpeg with synthetic test audio, SRT parsing, gaps, atomic publishing, cancellation, Unicode paths, 74-caption timing.
- Linux baseline dependencies: numpy 2.3.5, pytest 8.3.5, misaki 0.9.4, fugashi 1.4.0, mojimoji 0.0.13, jaconv 0.4.1, UniDic-Lite 1.0.8. Windows tests use the exact original Windows lock.
- Existing branch `srt-voice-studio/clean-build` retained; 1.1 work uses a separate branch. A local pre-edit source copy was also made.
- Verified original installer SHA256 recorded by successful Windows run: `108d022d41ddc53fd089b01ce0bfb6edeced385504829f73655cf3ca8c13f31a` (460942537 bytes).
- Local restored installer copy is truncated (406869504 bytes) and cannot serve as an acceptance baseline. CI must download the original run artifact and verify the exact SHA256 before installing it. Do not distribute that truncated local copy.
