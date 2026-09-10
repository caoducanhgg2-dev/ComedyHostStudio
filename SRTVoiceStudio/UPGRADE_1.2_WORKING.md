# SRT Voice Studio 1.2 — working checkpoint, not a verified release

The baseline remains the verified 1.1.0 source (`33fea46`) and installer. The
current working branch is `srt-voice-studio/1.2.0`. The installer version has not
yet been changed; no 1.2 installer is certified by this checkpoint.

Implemented in the working source:

- Sequential background batch queue, common/per-file settings, cancellation,
  retry, unique output names, Unicode paths, and one MP3 per successful SRT.
- Explicit configuration save/load and persistent favorite voices.
- Voice catalogue with installed/English/Japanese/all/favorites filters. The
  recommended filter is intentionally empty until listening ratings exist.
- Backend router preserving the original Kokoro implementation, plus a local
  VOICEVOX-compatible PCM adapter. External engines are not registered in the
  production UI yet. Native-style selection is still pending.
- Optional pack installation primitives: fixed SHA-256/size, staging, retry,
  cancellation cleanup, version isolation, archive path validation, and local
  integrity validation. Download controls and curated manifests are pending.
- Underfill V2 classifies measured B before extra user speed, targets 0.15 s
  residual where reachable, keeps the 0.88 floor and 1.20 ceiling, and warns
  above 0.80 s at the hard floor. START/slot calculation is unchanged.
- Median trailing silence and transitions above 0.80 s in render reports.
- A controlled 46-caption EN7 comparator using the exact archived 1.1 fitting
  implementation and identical cached original TTS. One final MP3 is emitted.

Local validation on 2026-09-10:

- Full collected suite: **96 passed in 129.31 s**. This includes prior tests,
  batch, API contract, pack installation and catalogue checks.
- Subsequently added actual 46-caption SRT structure / synthetic PCM test:
  **1 passed in 14.02 s**. This is timing evidence, not real speech quality.
- Actual speech benchmark and Windows upgrade/frozen/offline regression remain
  required. No naturalness score or final-verification status is asserted.

Remaining release gates: real Kokoro EN7 comparison, candidate EN/JP listening
samples and license audit, curated pack/user interface integration, native
styles, installed offline tests, 74-caption stress, Windows in-place upgrade
from the verified 1.1 installer, and final installer/checksum/report delivery.
