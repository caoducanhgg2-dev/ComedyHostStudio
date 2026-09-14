"""Build a delta ZIP update from a released install and a new frozen app."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PRODUCT = "SRT Voice Studio"
APP_ID = "{68F0C1C1-17CB-4CED-8261-5C18EB92571A}"
ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_installer_managed(rel: str) -> bool:
    """Files created by Inno Setup are preserved, never patched/deleted."""
    path = Path(rel)
    return len(path.parts) == 1 and path.name.lower().startswith("unins")


def inventory(root: Path, *, ignore_installer_managed: bool = False) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if ignore_installer_managed and is_installer_managed(rel):
            continue
        files[rel] = path
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--baseline-run", default="")
    args = parser.parse_args()

    baseline = Path(args.baseline).resolve()
    current = Path(args.current).resolve()
    out = Path(args.output_dir).resolve()
    if not (baseline / "SRTVoiceStudio.exe").is_file():
        raise SystemExit(f"Invalid baseline folder: {baseline}")
    if not (current / "SRTVoiceStudio.exe").is_file():
        raise SystemExit(f"Invalid current folder: {current}")

    old = inventory(baseline, ignore_installer_managed=True)
    new = inventory(current)
    changed: list[dict[str, object]] = []
    deleted: list[dict[str, object]] = []

    for rel in sorted(new):
        old_hash = digest(old[rel]) if rel in old else None
        new_hash = digest(new[rel])
        if old_hash != new_hash:
            changed.append({
                "path": rel,
                "old_sha256": old_hash,
                "sha256": new_hash,
                "size": new[rel].stat().st_size,
            })

    for rel in sorted(set(old) - set(new)):
        deleted.append({
            "path": rel,
            "old_sha256": digest(old[rel]),
            "size": old[rel].stat().st_size,
        })

    if not changed and not deleted:
        raise SystemExit("No delta detected; refusing empty update.")

    current_bytes = sum(p.stat().st_size for p in new.values())
    payload_bytes = sum(int(item["size"]) for item in changed)
    if len(changed) >= len(new) or payload_bytes >= current_bytes:
        raise SystemExit("Package is not a delta; refusing to ship the full app as an update.")

    manifest = {
        "format": 1,
        "product": PRODUCT,
        "app_id": APP_ID,
        "from_version": args.from_version,
        "to_version": args.to_version,
        "baseline_commit": args.baseline_commit,
        "baseline_run": args.baseline_run,
        "baseline_kind": "verified-installed-release",
        "preserve_installer_files": "root unins*",
        "files": changed,
        "delete": deleted,
        "stats": {
            "baseline_app_file_count": len(old),
            "current_file_count": len(new),
            "changed_file_count": len(changed),
            "deleted_file_count": len(deleted),
            "current_bytes": current_bytes,
            "payload_bytes": payload_bytes,
            "payload_ratio": round(payload_bytes / current_bytes, 6) if current_bytes else 0.0,
        },
    }

    out.mkdir(parents=True, exist_ok=True)
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    (out / "update_manifest.json").write_text(manifest_text, encoding="utf-8")

    package = out / f"SRTVoiceStudio_Update_{args.from_version}_to_{args.to_version}.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("update_manifest.json", manifest_text)
        archive.write(ROOT / "build_tools" / "update_zip" / "Apply_Update.cmd", "Apply_Update.cmd")
        archive.write(ROOT / "build_tools" / "update_zip" / "Apply_Update.ps1", "Apply_Update.ps1")
        for item in changed:
            rel = str(item["path"])
            archive.write(new[rel], f"payload/{rel}")

    build = {
        "package": package.name,
        "sha256": digest(package),
        "size": package.stat().st_size,
        "manifest": manifest,
    }
    (out / "update-build.json").write_text(
        json.dumps(build, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest["stats"], ensure_ascii=False, indent=2))
    print(f"Built {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
