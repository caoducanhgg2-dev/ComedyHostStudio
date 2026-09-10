# SRT Voice Studio 1.1.0

- Added 12 local Emotion / Performance presets with three intensities. Natural stays clean. Whisper-like is DSP, not a native whisper model.
- Added offline English/Japanese rule-based Auto Emotion without changing SRT text.
- Added 16 FX choices (including None) with three strengths, using existing bundled FFmpeg; no new runtime dependencies.
- Added immutable original-audio cache and A Original / B Processed / C Final Timeline previews. Style changes reuse A. C shares production fitting, overflow handling and validation.
- Effects run before fitting. Echo/Reverb/Cave tails cannot cross allowed end. Effective emotion + user + fit speed is capped at 1.20x.
- Added actual preset, cache, tail, preview, UI, 74-caption and upgrade acceptance gates.
- Retained app identity, install path, all 20 US and 5 Japanese voices, CPU/offline operation and a single final 48 kHz / 192 kbps MP3.
