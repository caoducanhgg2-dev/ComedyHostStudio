# SRT 1.4 safe-update continuation — NOT A BINARY RELEASE

Source checkpoint based on `dd6972de9aa66bcdcb739d80ddfa1e87354d9fb4`.
The existing release branches must not be overwritten or labeled verified by this work.

Implemented in this continuation:

- Selectively download one Aivis Japanese model or all six; keep existing models.
- Display per-model source-backed gender/age/style notes before downloading.
- Keep both known 1.3.1 baseline hash variants in the delta builder.
- Format 4 update: preflight, persistent journal, verified backup of actual old bytes,
  automatic rollback on startup failure, and recovery after an interrupted update.
- `Restore_Previous.cmd` remains available both in the update ZIP and the retained backup.
- New app startup and a Japanese MP3 are checked with isolated settings before success.
- Windows acceptance includes manual restore, corrupt-backup rejection, failed-executable
  automatic restore, interrupted-transaction recovery, registry restore and old app self-test.

The previous `Rollback_Update` scripts are retained in source history but are not shipped
by the format 4 builder; `Restore_Previous` owns this new journal layout.

Local evidence (Linux, 2026-09-15): full collected suite 113 passed; the subsequently
extended packaging test file also passed 3 tests, including alternate-baseline inclusion.
The actual Qt catalogue was opened and visually inspected. Python compile checks and
git whitespace checks passed. These are not Windows or real Aivis voice acceptance.

Release gate: build and execute the final Windows workflow. Linux unit checks alone
cannot certify a Windows binary, actual new Aivis synthesis or PowerShell rollback.
Do not distribute a source ZIP as if it were the requested binary delta update.

Known external issue from the preceding release status: GitHub-hosted jobs stopped
before step 1 and received no runner. No billing or Actions policy was changed here.

No update script can guarantee recovery after loss of the disk or backup. If restore
cannot finish because of locked files, permissions or damaged backup bytes, preserve
the backup and report the failure instead of deleting recovery data.
