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


def load_baseline_variant(path: Path, expected_version: str) -> dict[str, object]:
    data = json.loads(path.read_text("utf-8"))
    version = str(data.get("version", ""))
    if version != expected_version:
        raise SystemExit(f"Baseline variant {path} is for {version!r}, expected {expected_version!r}")
    hashes = data.get("file_hashes")
    if not isinstance(hashes, dict) or not hashes:
        raise SystemExit(f"Baseline variant {path} has no file_hashes mapping")
    normalized: dict[str, str] = {}
    for rel, value in hashes.items():
        rel = Path(str(rel)).as_posix()
        value = str(value).lower()
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit(f"Invalid SHA-256 in baseline variant {path}: {rel}")
        normalized[rel] = value
    return {
        "name": str(data.get("name") or path.stem),
        "version": version,
        "source": str(data.get("source", "")),
        "source_package_sha256": str(data.get("source_package_sha256", "")),
        "file_hashes": normalized,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--baseline-run", default="")
    parser.add_argument("--alternate-baseline-manifest", action="append", default=[])
    args = parser.parse_args()

    baseline = Path(args.baseline).resolve()
    current = Path(args.current).resolve()
    out = Path(args.output_dir).resolve()
    if not (baseline / "SRTVoiceStudio.exe").is_file():
        raise SystemExit(f"Invalid baseline folder: {baseline}")
    if not (current / "SRTVoiceStudio.exe").is_file():
        raise SystemExit(f"Invalid current folder: {current}")

    alternate_variants = [
        load_baseline_variant(Path(p).resolve(), args.from_version)
        for p in args.alternate_baseline_manifest
    ]
    old = inventory(baseline, ignore_installer_managed=True)
    new = inventory(current)
    changed: list[dict[str, object]] = []
    deleted: list[dict[str, object]] = []

    for rel in sorted(new):
        old_hash = digest(old[rel]) if rel in old else None
        new_hash = digest(new[rel])
        variant_hashes = sorted({
            str(variant["file_hashes"].get(rel, "")).lower()
            for variant in alternate_variants
            if rel in variant["file_hashes"]
            and str(variant["file_hashes"][rel]).lower() not in {old_hash, new_hash}
        })
        if old_hash != new_hash or variant_hashes:
            item: dict[str, object] = {
                "path": rel,
                "old_sha256": old_hash,
                "sha256": new_hash,
                "size": new[rel].stat().st_size,
            }
            if variant_hashes:
                item["old_sha256_variants"] = variant_hashes
            changed.append(item)

    for rel in sorted(set(old) - set(new)):
        old_hash = digest(old[rel])
        variant_hashes = sorted({
            str(variant["file_hashes"].get(rel, "")).lower()
            for variant in alternate_variants
            if rel in variant["file_hashes"]
            and str(variant["file_hashes"][rel]).lower() != old_hash
        })
        item: dict[str, object] = {
            "path": rel,
            "old_sha256": old_hash,
            "size": old[rel].stat().st_size,
        }
        if variant_hashes:
            item["old_sha256_variants"] = variant_hashes
        deleted.append(item)

    # If an alternate released baseline names a file that differs from the target,
    # that file must be in the payload even when the primary baseline already has
    # target bytes. This prevents a known alternate release from being silently
    # left with stale bytes.
    changed_paths = {str(item["path"]) for item in changed}
    for variant in alternate_variants:
        for rel, variant_hash in variant["file_hashes"].items():
            if rel not in new:
                continue
            new_hash = digest(new[rel])
            if variant_hash == new_hash or rel in changed_paths:
                continue
            primary_hash = digest(old[rel]) if rel in old else None
            changed.append({
                "path": rel,
                "old_sha256": primary_hash,
                "old_sha256_variants": [variant_hash],
                "sha256": new_hash,
                "size": new[rel].stat().st_size,
            })
            changed_paths.add(rel)
    changed.sort(key=lambda item: str(item["path"]))

    if not changed and not deleted:
        raise SystemExit("No delta detected; refusing empty update.")

    current_bytes = sum(p.stat().st_size for p in new.values())
    payload_bytes = sum(int(item["size"]) for item in changed)
    if len(changed) >= len(new) or payload_bytes >= current_bytes:
        raise SystemExit("Package is not a delta; refusing to ship the full app as an update.")

    baseline_variants = [{
        "name": "primary-github-release",
        "version": args.from_version,
        "kind": "verified-installed-release",
        "commit": args.baseline_commit,
        "run": args.baseline_run,
    }]
    baseline_variants.extend({
        "name": str(v["name"]),
        "version": str(v["version"]),
        "kind": "verified-hash-variant",
        "source": str(v["source"]),
        "source_package_sha256": str(v["source_package_sha256"]),
        "known_hash_count": len(v["file_hashes"]),
    } for v in alternate_variants)

    manifest = {
        "format": 4,
        "health_check": "--update-health-check",
        "product": PRODUCT,
        "app_id": APP_ID,
        "from_version": args.from_version,
        "to_version": args.to_version,
        "baseline_commit": args.baseline_commit,
        "baseline_run": args.baseline_run,
        "baseline_kind": "verified-installed-release-with-known-hash-variants",
        "baseline_variants": baseline_variants,
        "preserve_installer_files": "root unins*",
        "persistent_rollback": True,
        "rollback_audit_root": "%LOCALAPPDATA%/SRTVoiceStudio/updates",
        "files": changed,
        "delete": deleted,
        "stats": {
            "baseline_app_file_count": len(old),
            "current_file_count": len(new),
            "changed_file_count": len(changed),
            "deleted_file_count": len(deleted),
            "alternate_baseline_count": len(alternate_variants),
            "current_bytes": current_bytes,
            "payload_bytes": payload_bytes,
            "payload_ratio": round(payload_bytes / current_bytes, 6) if current_bytes else 0.0,
        },
    }

    out.mkdir(parents=True, exist_ok=True)
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    (out / "update_manifest.json").write_text(manifest_text, encoding="utf-8")

    package = out / f"SRTVoiceStudio_Update_{args.from_version}_to_{args.to_version}.zip"
    tool_root = ROOT / "build_tools" / "update_zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("update_manifest.json", manifest_text)
        for tool in ("Apply_Update.cmd", "Apply_Update.ps1", "Restore_Previous.cmd", "Restore_Previous.ps1", "Update_Common.ps1"):
            archive.write(tool_root / tool, tool)
        for item in changed:
            rel = str(item["path"])
            archive.write(new[rel], f"payload/{rel}")

    build = {
        "package": package.name,
        "sha256": digest(package),
        "size": package.stat().st_size,
        "rollback_tools": ["Restore_Previous.cmd", "Restore_Previous.ps1", "Update_Common.ps1"],
        "baseline_variants": baseline_variants,
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
