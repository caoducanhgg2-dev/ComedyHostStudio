"""Acceptance test for the ZIP delta updater against a real installed baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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


def run_ps1(script: Path, target: Path, local_appdata: Path, expect_success: bool) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(local_appdata)
    local_appdata.mkdir(parents=True, exist_ok=True)
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-TargetDir",
        str(target),
        "-SkipRegistry",
        "-NonInteractive",
    ]
    result = subprocess.run(command, text=True, capture_output=True, timeout=300, env=env)
    print(result.stdout)
    print(result.stderr)
    if expect_success and result.returncode != 0:
        raise RuntimeError(f"{script.name} failed with {result.returncode}")
    if not expect_success and result.returncode == 0:
        raise RuntimeError(f"{script.name} unexpectedly succeeded")
    return result


def run_update(package_root: Path, target: Path, local_appdata: Path, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    return run_ps1(package_root / "Apply_Update.ps1", target, local_appdata, expect_success)


def run_rollback(package_root: Path, target: Path, local_appdata: Path) -> subprocess.CompletedProcess[str]:
    return run_ps1(package_root / "Rollback_Update.ps1", target, local_appdata, True)


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
        for tool in ("Apply_Update.ps1", "Apply_Update.cmd", "Rollback_Update.ps1", "Rollback_Update.cmd"):
            if not (package_root / tool).is_file():
                raise RuntimeError(f"Update package is missing {tool}")

        target = work / "LỒNG TIẾNG" / "SRT Voice Studio"
        local_appdata = work / "LocalAppData"
        shutil.copytree(baseline, target)

        run_update(package_root, target, local_appdata)
        exact_app_match, preserved_installer_files = assert_patched_install(target, baseline, current)

        last_update_path = local_appdata / "SRTVoiceStudio" / "updates" / "last-update.json"
        if not last_update_path.is_file():
            raise RuntimeError("Persistent rollback audit record was not created")
        last_update = json.loads(last_update_path.read_text("utf-8-sig"))
        rollback_manifest = Path(last_update["rollback_manifest"])
        persistent_rollback_snapshot = bool(last_update.get("rollback_available")) and rollback_manifest.is_file()
        if not persistent_rollback_snapshot:
            raise RuntimeError("Persistent rollback snapshot is unavailable after a successful update")

        run_rollback(package_root, target, local_appdata)
        rollback_exact_baseline = inventory(target) == inventory(baseline)
        if not rollback_exact_baseline:
            raise RuntimeError("Persistent rollback did not restore the exact baseline")

        rolled_audit = json.loads(last_update_path.read_text("utf-8-sig"))
        if rolled_audit.get("rollback_available") is not False:
            raise RuntimeError("Rollback audit did not mark the snapshot as consumed")

        run_update(package_root, target, local_appdata)
        reapply_after_rollback = assert_patched_install(target, baseline, current)[0]

        first_pass = inventory(target)
        last_update_before_idempotent = last_update_path.read_bytes()
        run_update(package_root, target, local_appdata)
        idempotent = inventory(target) == first_pass
        rollback_record_preserved_on_idempotent = last_update_path.read_bytes() == last_update_before_idempotent
        if not idempotent:
            raise RuntimeError("Second update application changed the verified result")
        if not rollback_record_preserved_on_idempotent:
            raise RuntimeError("Idempotent update replaced the valid persistent rollback record")
        assert_patched_install(target, baseline, current)

        candidates = [item for item in manifest["files"] if item.get("old_sha256")]
        if not candidates:
            raise RuntimeError("No replaceable file exists for corruption-guard test")
        corrupt = work / "corrupt-baseline"
        corrupt_local = work / "CorruptLocalAppData"
        shutil.copytree(baseline, corrupt)
        victim = corrupt / Path(candidates[0]["path"])
        with victim.open("ab") as stream:
            stream.write(b"SRTVS-CORRUPTION-GUARD")
        before = inventory(corrupt)
        run_update(package_root, corrupt, corrupt_local, expect_success=False)
        corruption_rejected_without_partial_write = inventory(corrupt) == before
        if not corruption_rejected_without_partial_write:
            raise RuntimeError("Updater modified files after baseline verification failure")

    result = {
        "passed": True,
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
        "persistent_rollback_snapshot": persistent_rollback_snapshot,
        "rollback_exact_baseline": rollback_exact_baseline,
        "reapply_after_rollback": reapply_after_rollback,
        "idempotent": idempotent,
        "rollback_record_preserved_on_idempotent": rollback_record_preserved_on_idempotent,
        "corruption_rejected_without_partial_write": corruption_rejected_without_partial_write,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
