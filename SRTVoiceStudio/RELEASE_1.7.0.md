# SRT Voice Studio 1.7.0 — Production Workspace

Base: exact released SRT Voice Studio 1.6.1.

## User-facing scope

- Unified Workspace remains the only file-processing workspace: one or many SRT files, one shared voice/timing/emotion configuration.
- Extended multi-selection with Select All, bulk removal, retry, and direct Open MP3.
- Render Cache stores raw TTS only, keyed by language + voice + native style + caption text.
- Retry one caption regenerates only that caption's raw TTS in the background; the final master is rebuilt safely while other captions reuse cache.
- Smart Fit 3.0 smooths avoidable speed jumps between neighboring captions without allowing known overflow.
- Automatic QC runs on the master and decodes the staged final MP3 before publication.
- QC severe failures are fail-closed: the staged MP3 is deleted and is not published.
- Visual QC dashboard reports PASS/WARN/FAIL per file and can jump directly to affected captions.
- SFX Editor 1.7 stores edits per file: enable/disable cue, replace SFX type, shift ±1500 ms, and use per-cue level.
- Manual SFX edits on completed files requeue that file while preserving the old MP3 until a new render succeeds.

## Safety / compatibility invariants

- Auto SFX remains opt-in.
- Existing 1.6.1 SFX anti-click/DC/high-frequency/clipping QA remains active.
- Voice is never attenuated to make room for SFX.
- Minimum SRT gap and no-overlap constraints remain authoritative.
- Render Cache cannot reuse processed Emotion/FX/SFX output; only backend raw TTS is cached.
- Queue recovery stays outside the install directory.
- Update must be a small 1.6.1 -> 1.7.0 ZIP delta with baseline SHA checks, rollback, corruption rejection, and exact-final-tree verification.

## Release gates

Do not publish unless all are true:

1. Full source regression suite PASS.
2. Dedicated 1.7 core/UI/SFX/QC/cache tests PASS.
3. Existing 1.6.1 multifile and SFX regression gates PASS.
4. Cache stress PASS.
5. Final MP3 decode-QC integration PASS.
6. Frozen Windows app PASS.
7. Frozen SFX self-test PASS.
8. Exact released 1.6.1 baseline is reconstructed and verified.
9. Delta is small and exact-tree verification PASS.
10. Rollback -> corruption rejection -> reapply PASS.
