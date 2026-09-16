"""Harden a direct recovery ZIP with a full installed-baseline checksum guard.

The ordinary delta updater validates every file it changes. Recovery from a
known rebuilt 1.3.0 variant needs one extra guarantee: every *unchanged* app
file must also match the verified 1.3.0 release before any write occurs. This
script embeds a full baseline inventory and replaces Apply_Update.ps1 with a
small preflight wrapper. The original transactional updater is preserved as
Apply_Update_Core.ps1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_installer_managed(rel: str) -> bool:
    p = Path(rel)
    return len(p.parts) == 1 and p.name.lower().startswith("unins")


def inventory(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if is_installer_managed(rel):
            continue
        result[rel] = path
    return result


WRAPPER = r'''Param(
    [string]$TargetDir = "",
    [switch]$SkipRegistry,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $PackageRoot "update_manifest.json"
$CorePath = Join-Path $PackageRoot "Apply_Update_Core.ps1"
if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Missing update_manifest.json" }
if (-not (Test-Path -LiteralPath $CorePath)) { throw "Missing Apply_Update_Core.ps1" }
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{68F0C1C1-17CB-4CED-8261-5C18EB92571A}_is1"

function Get-Sha256([string]$Path) {
    $Stream = [System.IO.File]::OpenRead($Path)
    try {
        $Sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $Hash = $Sha.ComputeHash($Stream)
            return (([System.BitConverter]::ToString($Hash)) -replace "-", "").ToLowerInvariant()
        }
        finally { $Sha.Dispose() }
    }
    finally { $Stream.Dispose() }
}

if ([string]::IsNullOrWhiteSpace($TargetDir)) {
    if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
        $TargetDir = [string](Get-ItemProperty -Path $RegPath -Name InstallLocation).InstallLocation
    }
    if ([string]::IsNullOrWhiteSpace($TargetDir)) {
        $TargetDir = Join-Path $env:LOCALAPPDATA "Programs\SRTVoiceStudio"
    }
}
$TargetDir = [IO.Path]::GetFullPath($TargetDir).TrimEnd("\")

$InstalledVersion = $null
if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
    $InstalledVersion = [string](Get-ItemProperty -Path $RegPath -Name DisplayVersion).DisplayVersion
}

# Idempotent/reapply path: once the final version is installed, the core updater
# validates all payload target hashes and leaves the persistent rollback intact.
$AlreadyFinal = ($null -ne $InstalledVersion) -and ($InstalledVersion -eq [string]$Manifest.to_version)

if (-not $AlreadyFinal) {
    if (($null -ne $InstalledVersion) -and ($InstalledVersion -ne [string]$Manifest.from_version)) {
        throw "Installed version is $InstalledVersion. This recovery package only updates $($Manifest.from_version) to $($Manifest.to_version)."
    }

    $GuardNames = @($Manifest.PSObject.Properties.Name)
    if (-not ($GuardNames -contains "full_baseline_guard")) {
        throw "Recovery package is missing full_baseline_guard."
    }
    $Guard = $Manifest.full_baseline_guard
    $Expected = @{}

    Write-Host "Running full read-only baseline verification before update..."
    foreach ($Item in @($Guard.files)) {
        $Rel = [string]$Item.path
        $Dest = Join-Path $TargetDir ($Rel -replace "/", "\")
        if (-not (Test-Path -LiteralPath $Dest)) {
            throw "Full baseline guard failed; required file is missing: $Rel"
        }
        $Accepted = New-Object System.Collections.Generic.List[string]
        foreach ($Candidate in @($Item.accepted_sha256)) {
            if ($null -eq $Candidate) { continue }
            $Value = ([string]$Candidate).Trim().ToLowerInvariant()
            if ((-not [string]::IsNullOrWhiteSpace($Value)) -and (-not $Accepted.Contains($Value))) {
                $Accepted.Add($Value)
            }
        }
        $Actual = Get-Sha256 $Dest
        if (-not $Accepted.Contains($Actual)) {
            throw "Full baseline guard failed before overwrite: $Rel`nInstalled: $Actual`nAccepted: $($Accepted -join ', ')"
        }
        $Expected[$Rel.ToLowerInvariant()] = $true
    }

    if ([bool]$Guard.strict_file_set) {
        foreach ($File in Get-ChildItem -LiteralPath $TargetDir -Recurse -File) {
            $Rel = $File.FullName.Substring($TargetDir.Length).TrimStart("\").Replace("\", "/")
            $RootOnly = -not $Rel.Contains("/")
            if ($RootOnly -and $File.Name.ToLowerInvariant().StartsWith("unins")) { continue }
            if (-not $Expected.ContainsKey($Rel.ToLowerInvariant())) {
                throw "Full baseline guard found an unexpected app file; update stopped before overwrite: $Rel"
            }
        }
    }
    Write-Host "FULL BASELINE VERIFIED: $($Guard.files.Count) app files"
}

$Args = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$CorePath,'-TargetDir',$TargetDir)
if ($SkipRegistry) { $Args += '-SkipRegistry' }
if ($NonInteractive) { $Args += '-NonInteractive' }
& powershell.exe @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--package", required=True)
    ap.add_argument("--variant-manifest", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    baseline = Path(args.baseline).resolve()
    package = Path(args.package).resolve()
    variant_path = Path(args.variant_manifest).resolve()
    output = Path(args.output).resolve()
    summary_path = Path(args.summary).resolve()

    base = inventory(baseline)
    if not base or "SRTVoiceStudio.exe" not in base:
        raise SystemExit("Verified baseline inventory is invalid.")
    variant = json.loads(variant_path.read_text("utf-8"))
    variant_hashes = {
        Path(str(k)).as_posix(): str(v).lower()
        for k, v in dict(variant.get("file_hashes", {})).items()
    }
    missing_variant_paths = sorted(set(variant_hashes) - set(base))
    if missing_variant_paths:
        raise SystemExit(f"Variant names files not present in baseline: {missing_variant_paths}")

    guard_files = []
    for rel in sorted(base):
        primary = digest(base[rel])
        accepted = [primary]
        alt = variant_hashes.get(rel)
        if alt and alt not in accepted:
            accepted.append(alt)
        guard_files.append({"path": rel, "accepted_sha256": accepted})

    with tempfile.TemporaryDirectory(prefix="srt-recovery-") as td:
        root = Path(td)
        with zipfile.ZipFile(package, "r") as zin:
            zin.extractall(root)
        manifest_path = root / "update_manifest.json"
        manifest = json.loads(manifest_path.read_text("utf-8"))
        if manifest.get("from_version") != "1.3.0" or manifest.get("to_version") != "1.4.0":
            raise SystemExit("Recovery package must be 1.3.0 -> 1.4.0")

        # Every user-reported variant hash must be represented either as the
        # primary old hash or an alternate old hash for a payload/deletion item
        # whenever that path differs from the final target.
        changed_by_path = {str(x["path"]): x for x in manifest.get("files", [])}
        delete_by_path = {str(x["path"]): x for x in manifest.get("delete", [])}
        represented = 0
        target_same = 0
        for rel, alt in variant_hashes.items():
            item = changed_by_path.get(rel) or delete_by_path.get(rel)
            if item is None:
                # Safe only when this variant hash equals the verified baseline;
                # then the unchanged file is covered by the full guard.
                primary = digest(base[rel])
                if alt != primary:
                    raise SystemExit(
                        f"Variant differs at {rel} but direct delta does not replace/delete it"
                    )
                target_same += 1
                continue
            known = []
            if item.get("old_sha256"):
                known.append(str(item["old_sha256"]).lower())
            known.extend(str(x).lower() for x in item.get("old_sha256_variants", []))
            if alt not in known and alt != str(item.get("sha256", "")).lower():
                raise SystemExit(f"Variant hash is not accepted by delta: {rel}")
            represented += 1

        manifest["baseline_kind"] = "verified-1.3.0-with-full-recovery-guard"
        manifest["full_baseline_guard"] = {
            "strict_file_set": True,
            "installer_managed_root_prefix": "unins",
            "verified_primary_file_count": len(guard_files),
            "accepted_variant": str(variant.get("name", "user-installed-variant")),
            "files": guard_files,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")

        original_apply = root / "Apply_Update.ps1"
        if not original_apply.is_file():
            raise SystemExit("Apply_Update.ps1 is missing from delta package")
        shutil.move(str(original_apply), str(root / "Apply_Update_Core.ps1"))
        original_apply.write_text(WRAPPER, "utf-8-sig")

        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zout.write(path, path.relative_to(root).as_posix())

    result = {
        "passed": True,
        "package": output.name,
        "sha256": digest(output),
        "bytes": output.stat().st_size,
        "from_version": "1.3.0",
        "to_version": "1.4.0",
        "full_baseline_guard": True,
        "strict_file_set": True,
        "guarded_app_files": len(guard_files),
        "user_variant_hashes": len(variant_hashes),
        "variant_hashes_represented_by_delta": represented,
        "variant_hashes_equal_primary_unchanged": target_same,
        "rollback": "transactional plus persistent exact-installed-file snapshot",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
