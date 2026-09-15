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
$AuditDir = Join-Path $env:LOCALAPPDATA "SRTVoiceStudio\updates"

function Get-Sha256([string]$Path) {
    $Stream = [System.IO.File]::OpenRead($Path)
    try {
        $Sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $Hash = $Sha.ComputeHash($Stream)
            return (([System.BitConverter]::ToString($Hash)) -replace "-", "").ToLowerInvariant()
        }
        finally {
            $Sha.Dispose()
        }
    }
    finally {
        $Stream.Dispose()
    }
}

function Get-AcceptedOldHashes($Item) {
    $Values = New-Object System.Collections.Generic.List[string]
    $Names = @($Item.PSObject.Properties.Name)
    if (($Names -contains "old_sha256") -and ($null -ne $Item.old_sha256)) {
        $Value = ([string]$Item.old_sha256).Trim().ToLowerInvariant()
        if (-not [string]::IsNullOrWhiteSpace($Value)) { $Values.Add($Value) }
    }
    if (($Names -contains "old_sha256_variants") -and ($null -ne $Item.old_sha256_variants)) {
        foreach ($Candidate in @($Item.old_sha256_variants)) {
            if ($null -eq $Candidate) { continue }
            $Value = ([string]$Candidate).Trim().ToLowerInvariant()
            if ((-not [string]::IsNullOrWhiteSpace($Value)) -and (-not $Values.Contains($Value))) {
                $Values.Add($Value)
            }
        }
    }
    return @($Values)
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

# Build and validate the complete plan before writing anything. Each file may
# accept more than one released 1.3.1 hash, but arbitrary modified bytes remain
# rejected. The exact hash found on this machine is saved for rollback.
$Plan = @()
foreach ($Item in @($Manifest.files)) {
    $Relative = [string]$Item.path
    $Native = $Relative -replace "/", "\"
    $Dest = Join-Path $TargetDir $Native
    $Payload = Join-Path (Join-Path $PackageRoot "payload") $Native
    $NewSha = ([string]$Item.sha256).ToLowerInvariant()
    $AcceptedOld = @(Get-AcceptedOldHashes $Item)
    if (-not (Test-Path -LiteralPath $Payload)) {
        throw "Missing payload: $Relative"
    }
    if ((Get-Sha256 $Payload) -ne $NewSha) {
        throw "Payload checksum mismatch: $Relative"
    }

    $ActualOldSha = $null
    if (Test-Path -LiteralPath $Dest) {
        $CurrentHash = Get-Sha256 $Dest
        if ($CurrentHash -eq $NewSha) {
            $State = "already-new"
        } elseif ($AcceptedOld -contains $CurrentHash) {
            $State = "replace"
            $ActualOldSha = $CurrentHash
        } else {
            $Known = if ($AcceptedOld.Count) { $AcceptedOld -join ", " } else { "<new file expected>" }
            throw "Baseline checksum mismatch; update stopped before overwrite: $Relative`nInstalled: $CurrentHash`nAccepted: $Known"
        }
    } else {
        if ($AcceptedOld.Count -gt 0) {
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
        OldSha = $ActualOldSha
        NewSha = $NewSha
    }
}

foreach ($Item in @($Manifest.delete)) {
    $Relative = [string]$Item.path
    $Dest = Join-Path $TargetDir ($Relative -replace "/", "\")
    $AcceptedOld = @(Get-AcceptedOldHashes $Item)
    $ActualOldSha = $null
    if (-not (Test-Path -LiteralPath $Dest)) {
        $State = "already-deleted"
    } else {
        $CurrentHash = Get-Sha256 $Dest
        if (-not ($AcceptedOld -contains $CurrentHash)) {
            $Known = if ($AcceptedOld.Count) { $AcceptedOld -join ", " } else { "<none>" }
            throw "Old file checksum mismatch; delete stopped: $Relative`nInstalled: $CurrentHash`nAccepted: $Known"
        }
        $State = "delete"
        $ActualOldSha = $CurrentHash
    }
    $Plan += [pscustomobject]@{
        Kind = "delete"
        State = $State
        Relative = $Relative
        Dest = $Dest
        Payload = $null
        OldSha = $ActualOldSha
        NewSha = $null
    }
}

$ChangesNeeded = @($Plan | Where-Object { $_.State -in @("replace", "add", "delete") }).Count -gt 0
$TransactionBackup = Join-Path $env:TEMP ("SRTVoiceStudio-update-backup-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TransactionBackup | Out-Null
$Undo = @()
$RegistryChanged = $false
$PersistentBackupRoot = $null
$RollbackEntries = @()

try {
    if ($ChangesNeeded) {
        New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null
        $Stamp = (Get-Date).ToString("yyyyMMdd-HHmmssfff")
        $PersistentBackupRoot = Join-Path $AuditDir ("rollback-$($Manifest.from_version)-before-$($Manifest.to_version)-$Stamp-" + [guid]::NewGuid().ToString("N").Substring(0,8))
        New-Item -ItemType Directory -Force -Path (Join-Path $PersistentBackupRoot "files") | Out-Null
    }

    foreach ($Entry in $Plan) {
        if (($Entry.State -eq "already-new") -or ($Entry.State -eq "already-deleted")) {
            continue
        }

        $TransactionFile = Join-Path $TransactionBackup ($Entry.Relative -replace "/", "\")
        if (($Entry.State -eq "replace") -or ($Entry.State -eq "delete")) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $TransactionFile) | Out-Null
            Copy-Item -LiteralPath $Entry.Dest -Destination $TransactionFile -Force
            $Undo += [pscustomobject]@{ Action = "restore"; Dest = $Entry.Dest; Backup = $TransactionFile }

            # Verify again before copying to the persistent rollback snapshot so
            # rollback metadata always describes the exact bytes actually saved.
            $BeforeWriteHash = Get-Sha256 $Entry.Dest
            if ($BeforeWriteHash -ne $Entry.OldSha) {
                throw "Baseline changed after preflight; update stopped: $($Entry.Relative)"
            }
            $PersistentFile = Join-Path (Join-Path $PersistentBackupRoot "files") ($Entry.Relative -replace "/", "\")
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $PersistentFile) | Out-Null
            Copy-Item -LiteralPath $Entry.Dest -Destination $PersistentFile -Force
            if ((Get-Sha256 $PersistentFile) -ne $Entry.OldSha) {
                throw "Persistent rollback backup verification failed: $($Entry.Relative)"
            }
            $RollbackEntries += [ordered]@{
                action = "restore"
                path = $Entry.Relative
                backup = "files/$($Entry.Relative)"
                old_sha256 = $Entry.OldSha
                new_sha256 = $Entry.NewSha
            }
        } elseif ($Entry.State -eq "add") {
            $Undo += [pscustomobject]@{ Action = "remove"; Dest = $Entry.Dest; Backup = $null }
            $RollbackEntries += [ordered]@{
                action = "remove"
                path = $Entry.Relative
                backup = $null
                old_sha256 = $null
                new_sha256 = $Entry.NewSha
            }
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

    if ($ChangesNeeded) {
        $RollbackManifest = [ordered]@{
            format = 2
            product = [string]$Manifest.product
            from_version = [string]$Manifest.from_version
            to_version = [string]$Manifest.to_version
            created_at = (Get-Date).ToString("o")
            target = $TargetDir
            exact_installed_old_hashes = $true
            entries = @($RollbackEntries)
        }
        $RollbackManifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PersistentBackupRoot "rollback_manifest.json") -Encoding UTF8
    }

    if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
        Set-ItemProperty -Path $RegPath -Name DisplayVersion -Value ([string]$Manifest.to_version)
        $RegistryChanged = $true
    }

    if ($ChangesNeeded) {
        New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null
        [ordered]@{
            product = [string]$Manifest.product
            from_version = [string]$Manifest.from_version
            to_version = [string]$Manifest.to_version
            applied_at = (Get-Date).ToString("o")
            target = $TargetDir
            changed_files = @($Manifest.files).Count
            deleted_files = @($Manifest.delete).Count
            rollback_available = $true
            rollback_dir = $PersistentBackupRoot
            rollback_manifest = (Join-Path $PersistentBackupRoot "rollback_manifest.json")
            exact_installed_baseline_saved = $true
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $AuditDir "last-update.json") -Encoding UTF8
    }

    Write-Host ""
    if ($ChangesNeeded) {
        Write-Host "UPDATE SUCCESS: SRT Voice Studio $($Manifest.to_version)"
        Write-Host "Rollback snapshot: $PersistentBackupRoot"
        Write-Host "Use Rollback_Update.cmd from this ZIP if you need to restore $($Manifest.from_version)."
    } else {
        Write-Host "UPDATE ALREADY APPLIED: SRT Voice Studio $($Manifest.to_version)"
        Write-Host "Existing rollback snapshot was preserved."
    }
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
    if (($null -ne $PersistentBackupRoot) -and (Test-Path -LiteralPath $PersistentBackupRoot)) {
        Remove-Item -LiteralPath $PersistentBackupRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    throw
}
finally {
    Remove-Item -LiteralPath $TransactionBackup -Recurse -Force -ErrorAction SilentlyContinue
}
