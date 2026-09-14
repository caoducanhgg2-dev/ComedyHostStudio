Param(
    [string]$TargetDir = "",
    [switch]$SkipRegistry,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $PackageRoot "update_manifest.json"
if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "Missing update_manifest.json"
}
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{68F0C1C1-17CB-4CED-8261-5C18EB92571A}_is1"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

if ([string]::IsNullOrWhiteSpace($TargetDir)) {
    if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
        $TargetDir = [string](Get-ItemProperty -Path $RegPath -Name InstallLocation).InstallLocation
    }
    if ([string]::IsNullOrWhiteSpace($TargetDir)) {
        $TargetDir = Join-Path $env:LOCALAPPDATA "Programs\SRTVoiceStudio"
    }
}
$TargetDir = [IO.Path]::GetFullPath($TargetDir)
$Exe = Join-Path $TargetDir "SRTVoiceStudio.exe"
if (-not (Test-Path -LiteralPath $Exe)) {
    throw "SRTVoiceStudio.exe was not found in: $TargetDir"
}

$OldRegistryVersion = $null
if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
    $OldRegistryVersion = [string](Get-ItemProperty -Path $RegPath -Name DisplayVersion).DisplayVersion
    if (($OldRegistryVersion -ne [string]$Manifest.from_version) -and
        ($OldRegistryVersion -ne [string]$Manifest.to_version)) {
        throw "Installed version is $OldRegistryVersion. This package only updates $($Manifest.from_version) to $($Manifest.to_version)."
    }
}

$Running = @(Get-Process -Name "SRTVoiceStudio" -ErrorAction SilentlyContinue)
if ($Running.Count -gt 0) {
    if ($NonInteractive) {
        throw "SRT Voice Studio is running. Close it before updating."
    }
    Write-Host "Close SRT Voice Studio, then press Enter to continue."
    [void](Read-Host)
    $Running = @(Get-Process -Name "SRTVoiceStudio" -ErrorAction SilentlyContinue)
    if ($Running.Count -gt 0) {
        throw "SRT Voice Studio is still running."
    }
}

$Plan = @()
foreach ($Item in @($Manifest.files)) {
    $Relative = [string]$Item.path
    $Native = $Relative -replace "/", "\"
    $Dest = Join-Path $TargetDir $Native
    $Payload = Join-Path (Join-Path $PackageRoot "payload") $Native
    if (-not (Test-Path -LiteralPath $Payload)) {
        throw "Missing payload: $Relative"
    }
    if ((Get-Sha256 $Payload) -ne ([string]$Item.sha256).ToLowerInvariant()) {
        throw "Payload checksum mismatch: $Relative"
    }

    if (Test-Path -LiteralPath $Dest) {
        $CurrentHash = Get-Sha256 $Dest
        if ($CurrentHash -eq ([string]$Item.sha256).ToLowerInvariant()) {
            $State = "already-new"
        } elseif (($null -ne $Item.old_sha256) -and
                  ($CurrentHash -eq ([string]$Item.old_sha256).ToLowerInvariant())) {
            $State = "replace"
        } else {
            throw "Baseline checksum mismatch; update stopped before overwrite: $Relative"
        }
    } else {
        if (($null -ne $Item.old_sha256) -and
            (-not [string]::IsNullOrWhiteSpace([string]$Item.old_sha256))) {
            throw "Baseline file is missing: $Relative"
        }
        $State = "add"
    }
    $Plan += [pscustomobject]@{
        Kind = "file"
        State = $State
        Relative = $Relative
        Dest = $Dest
        Payload = $Payload
    }
}

foreach ($Item in @($Manifest.delete)) {
    $Relative = [string]$Item.path
    $Dest = Join-Path $TargetDir ($Relative -replace "/", "\")
    if (-not (Test-Path -LiteralPath $Dest)) {
        $State = "already-deleted"
    } else {
        if ((Get-Sha256 $Dest) -ne ([string]$Item.old_sha256).ToLowerInvariant()) {
            throw "Old file checksum mismatch; delete stopped: $Relative"
        }
        $State = "delete"
    }
    $Plan += [pscustomobject]@{
        Kind = "delete"
        State = $State
        Relative = $Relative
        Dest = $Dest
        Payload = $null
    }
}

$BackupRoot = Join-Path $env:TEMP ("SRTVoiceStudio-update-backup-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
$Undo = @()
$RegistryChanged = $false

try {
    foreach ($Entry in $Plan) {
        if (($Entry.State -eq "already-new") -or ($Entry.State -eq "already-deleted")) {
            continue
        }

        $Backup = Join-Path $BackupRoot ($Entry.Relative -replace "/", "\")
        if (($Entry.State -eq "replace") -or ($Entry.State -eq "delete")) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Backup) | Out-Null
            Copy-Item -LiteralPath $Entry.Dest -Destination $Backup -Force
            $Undo += [pscustomobject]@{ Action = "restore"; Dest = $Entry.Dest; Backup = $Backup }
        } elseif ($Entry.State -eq "add") {
            $Undo += [pscustomobject]@{ Action = "remove"; Dest = $Entry.Dest; Backup = $null }
        }

        if ($Entry.Kind -eq "delete") {
            Remove-Item -LiteralPath $Entry.Dest -Force
            continue
        }

        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Entry.Dest) | Out-Null
        Copy-Item -LiteralPath $Entry.Payload -Destination $Entry.Dest -Force
    }

    foreach ($Item in @($Manifest.files)) {
        $Dest = Join-Path $TargetDir (([string]$Item.path) -replace "/", "\")
        if ((-not (Test-Path -LiteralPath $Dest)) -or
            ((Get-Sha256 $Dest) -ne ([string]$Item.sha256).ToLowerInvariant())) {
            throw "Post-update verification failed: $($Item.path)"
        }
    }
    foreach ($Item in @($Manifest.delete)) {
        $Dest = Join-Path $TargetDir (([string]$Item.path) -replace "/", "\")
        if (Test-Path -LiteralPath $Dest) {
            throw "Old file still exists after update: $($Item.path)"
        }
    }

    if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
        Set-ItemProperty -Path $RegPath -Name DisplayVersion -Value ([string]$Manifest.to_version)
        $RegistryChanged = $true
    }

    $AuditDir = Join-Path $env:LOCALAPPDATA "SRTVoiceStudio\updates"
    New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null
    [ordered]@{
        product = [string]$Manifest.product
        from_version = [string]$Manifest.from_version
        to_version = [string]$Manifest.to_version
        applied_at = (Get-Date).ToString("o")
        target = $TargetDir
        changed_files = @($Manifest.files).Count
        deleted_files = @($Manifest.delete).Count
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $AuditDir "last-update.json") -Encoding UTF8

    Write-Host ""
    Write-Host "UPDATE SUCCESS: SRT Voice Studio $($Manifest.to_version)"
    Write-Host "No installer EXE was run. User data was preserved."
}
catch {
    if ($RegistryChanged -and ($null -ne $OldRegistryVersion) -and (Test-Path $RegPath)) {
        try { Set-ItemProperty -Path $RegPath -Name DisplayVersion -Value $OldRegistryVersion } catch {}
    }
    for ($i = $Undo.Count - 1; $i -ge 0; $i--) {
        $Step = $Undo[$i]
        try {
            if ($Step.Action -eq "restore") {
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Step.Dest) | Out-Null
                Copy-Item -LiteralPath $Step.Backup -Destination $Step.Dest -Force
            } elseif ($Step.Action -eq "remove") {
                Remove-Item -LiteralPath $Step.Dest -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
    throw
}
finally {
    Remove-Item -LiteralPath $BackupRoot -Recurse -Force -ErrorAction SilentlyContinue
}
