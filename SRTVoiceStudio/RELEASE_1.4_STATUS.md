# SRT Voice Studio 1.4 — Release Status

Updated: 2026-09-15

## Release branch

- Branch: `srt-voice-studio/1.4.0-final-hardening`
- Base hardening started from: `bf64fba8fe1abf4c052dc647768d69f7af1cfa30`
- Target version: `1.4.0`
- Update path: `1.3.1 -> 1.4.0`
- Final package name: `SRTVoiceStudio_Update_1.3.1_to_1.4.0.zip`

Do not merge/release this branch until the final Windows workflow completes successfully and uploads the acceptance artifact.

## Feature status

### Japanese voices — implemented

Capacity when the optional Aivis pack is fully installed:

- Kokoro English US: 20
- Kokoro English UK: 8
- Kokoro Japanese: 5
- Aivis Japanese: 6
- Total speaker capacity: 39

Aivis Japanese speakers: Mao, Kohaku, Rinne El, Aida Shigeru, Mai, Nise. Voice characteristics are shown in the UI. Model assets are version/size/SHA-256 pinned and optional downloads remain local after installation.

### Existing Windows evidence for the Japanese expansion

GitHub Actions run `34871074789`, commit `b43bf89b6b9f54bbd8922935b2f47b18ba6f49bd`, completed successfully before the later version/update-packaging commits.

Diagnostics from that successful Windows run recorded:

- pytest: 110 tests, 0 failures, 0 errors
- voice benchmark: 39 speakers, technical checks passed
- Japanese 74-caption stress path: START unchanged, overlap = 0
- six Aivis speakers synthesized in the optional-voice acceptance path

This evidence validates the Japanese expansion code path, but it does not replace the final 1.4 frozen/updater acceptance run.

## ZIP updater hardening — implemented in source

The 1.4 ZIP updater now has three safety layers:

1. Complete preflight verification before writes. Payload SHA-256 and installed baseline SHA-256 must match a known state.
2. Transaction rollback if the update fails while files are being changed.
3. Persistent post-success rollback stored under `%LOCALAPPDATA%\SRTVoiceStudio\updates` and launched with `Rollback_Update.cmd`.

Persistent rollback stores the exact old bytes and exact old SHA-256 found on the user's machine. Rollback validates both the current 1.4 bytes and the saved backup before restoring anything. The rollback process itself also has a transaction backup.

## Two known 1.3.1 release variants

Release review found two valid 1.3.1 packaging lineages. One universal 1.4 ZIP is therefore required. The manifest format supports a primary old hash plus verified `old_sha256_variants`.

Primary GitHub Actions 1.3.1 package:

- Run: `34880069622`
- Head commit: `1249412252f6e3e2e15ea57f1838cf6d86698f9e`
- Inner update ZIP SHA-256: `d4a79c11ffc7b01f255540c1bfbb48e4bb9030a280b29d6c1d657c58db579741`

Known project/Library 1.3.1 package:

- Inner update ZIP SHA-256: `9e0ad6cf402b9c6766abb68b4baf331d3cdf298dd99d7316a943501fd71a411a`
- Known target hashes are recorded in `build_tools/baseline_variants/1.3.1-library-artifact.json`.

The updater still rejects unknown/modified hashes. It does not fall back to version-only matching.

## Required final Windows acceptance

Workflow: `.github/workflows/srt-voice-studio-1.4-zip-update.yml`

A release is accepted only if the workflow verifies all of the following:

- full pytest suite passes
- mandatory 1.4 voice counts/rules pass
- FFmpeg filters pass
- PyInstaller frozen app builds and `check_frozen.py` passes
- exact verified 1.3.1 primary baseline is staged
- universal manifest contains both known 1.3.1 variants
- ZIP is a delta, not a full reinstall
- exact app match after update
- installer-managed `unins*` files remain intact
- corruption is rejected before partial write
- persistent rollback snapshot is created and verified
- rollback restores exact 1.3.1 baseline
- update can be reapplied after rollback
- second apply is idempotent and keeps the valid rollback record
- registry transitions `1.3.1 -> 1.4.0 -> 1.3.1 -> 1.4.0`
- SHA256SUMS and final acceptance JSON are generated

## Current external blocker

At the time of this status file, GitHub-hosted runners are not being allocated to this repository/account. Heavy Windows build jobs fail before step 1 with `steps=[]` and `runner_id=0`.

A temporary two-job probe was run on both `ubuntu-latest` and `windows-latest` (run `34983763534`). Both jobs also failed before any step was allocated. The probe workflow was then removed from the branch.

This demonstrates that the current block is outside the 1.4 build/test steps themselves. It does not prove a specific billing, quota, policy, or GitHub service cause; account/repository Actions status must be checked separately.

## Release rule

Do not label the updater ZIP as verified/final, do not merge to the release branch, and do not distribute a newly assembled binary until a hosted or trusted Windows runner actually executes the final workflow successfully.

## Full installer retry

A fresh full-installer build was explicitly retriggered on 2026-09-15 after confirming that the previously distributed artifact was still the old 1.3.0 installer. The target artifact is `SRTVoiceStudio_Setup_1.4.0` from `.github/workflows/srt-voice-studio-windows.yml`; only that artifact should be distributed as the full 1.4 installer.

