Param(
    [string]$TargetDir = "",
    [string]$BackupDir = "",
    [switch]$SkipRegistry,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{68F0C1C1-17CB-4CED-8261-5C18EB92571A}_is1"
$AuditDir = Join-Path $env:LOCALAPPDATA "SRTVoiceStudio\updates"
$LastUpdatePath = Join-Path $AuditDir "last-update.json"
$UsingLatestRecord = [string]::IsNullOrWhiteSpace($BackupDir)

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

if ($UsingLatestRecord) {
    if (-not (Test-Path -LiteralPath $LastUpdatePath)) {
        throw "No rollback record was found. Apply the 1.4 ZIP update first."
    }
    $LastUpdate = Get-Content -LiteralPath $LastUpdatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $PropertyNames = @($LastUpdate.PSObject.Properties.Name)
    if (-not ($PropertyNames -contains "rollback_dir")) {
        throw "The latest update record is from an older updater and has no persistent rollback snapshot."
    }
    if (($PropertyNames -contains "rollback_available") -and (-not [bool]$LastUpdate.rollback_available)) {
        throw "The latest update has already been rolled back."
    }
    $BackupDir = [string]$LastUpdate.rollback_dir
}
if ([string]::IsNullOrWhiteSpace($BackupDir)) {
    throw "Rollback backup directory is empty."
}
$BackupDir = [IO.Path]::GetFullPath($BackupDir)
$RollbackManifestPath = Join-Path $BackupDir "rollback_manifest.json"
if (-not (Test-Path -LiteralPath $RollbackManifestPath)) {
    throw "Missing rollback_manifest.json in: $BackupDir"
}
$Manifest = Get-Content -LiteralPath $RollbackManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ([string]::IsNullOrWhiteSpace($TargetDir)) {
    $TargetDir = [string]$Manifest.target
}
$TargetDir = [IO.Path]::GetFullPath($TargetDir)
if (-not (Test-Path -LiteralPath (Join-Path $TargetDir "SRTVoiceStudio.exe"))) {
    throw "SRTVoiceStudio.exe was not found in: $TargetDir"
}

$Running = @(Get-Process -Name "SRTVoiceStudio" -ErrorAction SilentlyContinue)
if ($Running.Count -gt 0) {
    if ($NonInteractive) {
        throw "SRT Voice Studio is running. Close it before rollback."
    }
    Write-Host "Close SRT Voice Studio, then press Enter to continue."
    [void](Read-Host)
    $Running = @(Get-Process -Name "SRTVoiceStudio" -ErrorAction SilentlyContinue)
    if ($Running.Count -gt 0) { throw "SRT Voice Studio is still running." }
}

$Plan = @()
foreach ($Item in @($Manifest.entries)) {
    $Relative = [string]$Item.path
    $Dest = Join-Path $TargetDir ($Relative -replace "/", "\")
    $Action = [string]$Item.action
    $NewSha = if ($null -ne $Item.new_sha256) { [string]$Item.new_sha256 } else { $null }
    $OldSha = if ($null -ne $Item.old_sha256) { [string]$Item.old_sha256 } else { $null }
    $Backup = $null

    if ($Action -eq "restore") {
        $Backup = Join-Path $BackupDir (([string]$Item.backup) -replace "/", "\")
        if (-not (Test-Path -LiteralPath $Backup)) { throw "Rollback backup is missing: $Relative" }
        if ((Get-Sha256 $Backup) -ne $OldSha.ToLowerInvariant()) { throw "Rollback backup checksum mismatch: $Relative" }
        if ([string]::IsNullOrWhiteSpace($NewSha)) {
            if (Test-Path -LiteralPath $Dest) { throw "Current file should be absent before rollback: $Relative" }
        } else {
            if (-not (Test-Path -LiteralPath $Dest)) { throw "Current updated file is missing: $Relative" }
            if ((Get-Sha256 $Dest) -ne $NewSha.ToLowerInvariant()) { throw "Current updated file checksum mismatch: $Relative" }
        }
    } elseif ($Action -eq "remove") {
        if (-not (Test-Path -LiteralPath $Dest)) { throw "Added update file is missing before rollback: $Relative" }
        if ((Get-Sha256 $Dest) -ne $NewSha.ToLowerInvariant()) { throw "Added update file checksum mismatch: $Relative" }
    } else {
        throw "Unknown rollback action: $Action"
    }

    $Plan += [pscustomobject]@{
        Action = $Action
        Relative = $Relative
        Dest = $Dest
        Backup = $Backup
        OldSha = $OldSha
        NewSha = $NewSha
    }
}

$OldRegistryVersion = $null
if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
    $OldRegistryVersion = [string](Get-ItemProperty -Path $RegPath -Name DisplayVersion).DisplayVersion
    if (($OldRegistryVersion -ne [string]$Manifest.to_version) -and
        ($OldRegistryVersion -ne [string]$Manifest.from_version)) {
        throw "Installed version is $OldRegistryVersion; refusing rollback for $($Manifest.to_version)."
    }
}

$TransactionBackup = Join-Path $env:TEMP ("SRTVoiceStudio-rollback-backup-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TransactionBackup | Out-Null
$Undo = @()
$RegistryChanged = $false

try {
    foreach ($Entry in $Plan) {
        if (Test-Path -LiteralPath $Entry.Dest) {
            $CurrentBackup = Join-Path $TransactionBackup ($Entry.Relative -replace "/", "\")
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $CurrentBackup) | Out-Null
            Copy-Item -LiteralPath $Entry.Dest -Destination $CurrentBackup -Force
            $Undo += [pscustomobject]@{ Action = "restore"; Dest = $Entry.Dest; Backup = $CurrentBackup }
        } else {
            $Undo += [pscustomobject]@{ Action = "remove"; Dest = $Entry.Dest; Backup = $null }
        }

        if ($Entry.Action -eq "restore") {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Entry.Dest) | Out-Null
            Copy-Item -LiteralPath $Entry.Backup -Destination $Entry.Dest -Force
        } elseif ($Entry.Action -eq "remove") {
            Remove-Item -LiteralPath $Entry.Dest -Force
        }
    }

    foreach ($Entry in $Plan) {
        if ($Entry.Action -eq "restore") {
            if (-not (Test-Path -LiteralPath $Entry.Dest)) { throw "Rollback restore failed: $($Entry.Relative)" }
            if ((Get-Sha256 $Entry.Dest) -ne $Entry.OldSha.ToLowerInvariant()) { throw "Rollback verification failed: $($Entry.Relative)" }
        } elseif (Test-Path -LiteralPath $Entry.Dest) {
            throw "Rollback removal failed: $($Entry.Relative)"
        }
    }

    if ((-not $SkipRegistry) -and (Test-Path $RegPath)) {
        Set-ItemProperty -Path $RegPath -Name DisplayVersion -Value ([string]$Manifest.from_version)
        $RegistryChanged = $true
    }

    New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null
    [ordered]@{
        product = [string]$Manifest.product
        from_version = [string]$Manifest.to_version
        to_version = [string]$Manifest.from_version
        rolled_back_at = (Get-Date).ToString("o")
        target = $TargetDir
        rollback_dir = $BackupDir
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $AuditDir "last-rollback.json") -Encoding UTF8

    if ($UsingLatestRecord -and (Test-Path -LiteralPath $LastUpdatePath)) {
        $LastUpdate = Get-Content -LiteralPath $LastUpdatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $LastUpdate | Add-Member -NotePropertyName rollback_available -NotePropertyValue $false -Force
        $LastUpdate | Add-Member -NotePropertyName rolled_back_at -NotePropertyValue (Get-Date).ToString("o") -Force
        $LastUpdate | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $LastUpdatePath -Encoding UTF8
    }

    Write-Host ""
    Write-Host "ROLLBACK SUCCESS: SRT Voice Studio $($Manifest.from_version) restored."
    Write-Host "The 1.4 update ZIP can be applied again later if needed."
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
    Remove-Item -LiteralPath $TransactionBackup -Recurse -Force -ErrorAction SilentlyContinue
}
