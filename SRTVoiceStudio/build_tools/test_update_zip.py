"""Acceptance test for the ZIP delta updater against a real installed baseline."""
from __future__ import annotations

import argparse
import os
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): digest(p)
        for p in root.rglob("*")
        if p.is_file()
    }


def is_installer_managed(rel: str) -> bool:
    path = Path(rel)
    return len(path.parts) == 1 and path.name.lower().startswith("unins")


def assert_patched_install(target: Path, baseline: Path, current: Path) -> tuple[bool, int]:
    target_inv = inventory(target)
    current_inv = inventory(current)
    baseline_inv = inventory(baseline)

    for rel, wanted_hash in current_inv.items():
        if target_inv.get(rel) != wanted_hash:
            raise RuntimeError(f"Patched app mismatch: {rel}")

    preserved = {
        rel: value
        for rel, value in baseline_inv.items()
        if rel not in current_inv and is_installer_managed(rel)
    }
    unexpected = set(target_inv) - set(current_inv) - set(preserved)
    if unexpected:
        raise RuntimeError(f"Unexpected files after patch: {sorted(unexpected)[:10]}")
    for rel, wanted_hash in preserved.items():
        if target_inv.get(rel) != wanted_hash:
            raise RuntimeError(f"Installer-managed file was modified: {rel}")
    return True, len(preserved)


def run_update(package_root: Path, target: Path, expect_success: bool) -> subprocess.CompletedProcess[str]:
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(package_root / "Apply_Update.ps1"),
        "-TargetDir",
        str(target),
        "-SkipRegistry",
        "-NonInteractive",
    ]
    result = subprocess.run(command, text=True, capture_output=True, timeout=420)
    print(result.stdout)
    print(result.stderr)
    if expect_success and result.returncode != 0:
        raise RuntimeError(f"Updater failed with {result.returncode}")
    if not expect_success and result.returncode == 0:
        raise RuntimeError("Updater unexpectedly accepted a corrupted baseline")
    return result


def journal_for(target):
    key = hashlib.sha256(str(target).lower().encode('utf-8')).hexdigest().upper()
    pointer = Path(os.environ['LOCALAPPDATA']) / 'SRTVoiceStudio' / 'updates' / key / 'latest.json'
    return Path(json.loads(pointer.read_text('utf-8-sig'))['journal'])

def restore(package_root, target, success=True):
    result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
        '-File',str(package_root/'Restore_Previous.ps1'),'-TargetDir',str(target),
        '-SkipRegistry','-NonInteractive'],capture_output=True,text=True,timeout=120)
    if (result.returncode == 0) != success:
        raise RuntimeError(f'Restore unexpected result: {result.stdout} {result.stderr}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    baseline = Path(args.baseline).resolve()
    current = Path(args.current).resolve()
    package = Path(args.package).resolve()
    result_path = Path(args.result).resolve()

    with tempfile.TemporaryDirectory(prefix="srtvs-zip-update-") as tmp:
        work = Path(tmp)
        package_root = work / "package"
        with zipfile.ZipFile(package) as archive:
            archive.extractall(package_root)
        manifest = json.loads((package_root / "update_manifest.json").read_text("utf-8"))

        target = work / "LỒNG TIẾNG" / "SRT Voice Studio"
        shutil.copytree(baseline, target)
        run_update(package_root, target, expect_success=True)
        exact_app_match, preserved_installer_files = assert_patched_install(target, baseline, current)

        first_pass = inventory(target)
        run_update(package_root, target, expect_success=True)
        idempotent = inventory(target) == first_pass
        if not idempotent:
            raise RuntimeError("Second update application changed the verified result")
        assert_patched_install(target, baseline, current)
        journal = journal_for(target)
        assert journal.is_file(), 'Persistent backup is missing'
        state = json.loads(journal.read_text('utf-8-sig'))
        assert state['state'] == 'applied'
        # Prove a damaged backup is rejected before touching the working app.
        entry = next(e for e in state['entries'] if e['old_sha256'])
        saved = journal.parent / 'files' / entry['path']
        good_bytes = saved.read_bytes(); saved.write_bytes(b'corrupt backup')
        restore(package_root, target, success=False)
        assert inventory(target) == first_pass
        saved.write_bytes(good_bytes)
        restore(package_root, target)
        assert inventory(target) == inventory(baseline), 'Manual restore did not recover exact old app'
        restore(package_root, target)  # Repeat safely.
        assert inventory(target) == inventory(baseline)

        # All package hashes are valid, but the replacement EXE cannot start.
        # This exercises rollback AFTER writes, not merely preflight rejection.
        failing_package = work / 'failing-health'
        shutil.copytree(package_root, failing_package)
        failed_manifest = json.loads((failing_package/'update_manifest.json').read_text('utf-8'))
        exe_entry = next(e for e in failed_manifest['files'] if e['path']=='SRTVoiceStudio.exe')
        broken_exe = failing_package/'payload/SRTVoiceStudio.exe'
        broken_exe.write_bytes(b'not an executable: health-check failure test')
        exe_entry['sha256']=digest(broken_exe); exe_entry['size']=broken_exe.stat().st_size
        (failing_package/'update_manifest.json').write_text(json.dumps(failed_manifest),encoding='utf-8')
        run_update(failing_package,target,expect_success=False)
        assert inventory(target)==inventory(baseline), 'Failed startup did not restore old app'
        assert json.loads(journal_for(target).read_text('utf-8-sig'))['state']=='restored'

        # Simulate interruption after writes but before success journal commit.
        run_update(package_root,target,expect_success=True)
        journal=journal_for(target); state=json.loads(journal.read_text('utf-8-sig'))
        state['state']='applying'; journal.write_text(json.dumps(state),encoding='utf-8')
        run_update(package_root,target,expect_success=False)
        assert inventory(target)==inventory(baseline), 'Interrupted transaction was not recovered'

        candidates = [item for item in manifest["files"] if item.get("old_sha256")]
        if not candidates:
            raise RuntimeError("No replaceable file exists for corruption-guard test")
        corrupt = work / "corrupt-baseline"
        shutil.copytree(baseline, corrupt)
        victim = corrupt / Path(candidates[0]["path"])
        with victim.open("ab") as stream:
            stream.write(b"SRTVS-CORRUPTION-GUARD")
        before = inventory(corrupt)
        run_update(package_root, corrupt, expect_success=False)
        corruption_rejected_without_partial_write = inventory(corrupt) == before
        if not corruption_rejected_without_partial_write:
            raise RuntimeError("Updater modified files after baseline verification failure")

    result = {
        "passed": True,
        "manual_restore_exact": True,
        "corrupt_backup_rejected_before_write": True,
        "startup_failure_rollback_exact": True,
        "interrupted_update_recovery_exact": True,
        "package": package.name,
        "from_version": manifest["from_version"],
        "to_version": manifest["to_version"],
        "baseline_kind": manifest.get("baseline_kind"),
        "baseline_run": manifest.get("baseline_run"),
        "changed_files": len(manifest["files"]),
        "deleted_files": len(manifest["delete"]),
        "payload_ratio": manifest["stats"]["payload_ratio"],
        "exact_app_match": exact_app_match,
        "preserved_installer_files": preserved_installer_files,
        "idempotent": idempotent,
        "corruption_rejected_without_partial_write": corruption_rejected_without_partial_write,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

