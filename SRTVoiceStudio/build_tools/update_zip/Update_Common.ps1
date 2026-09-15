$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RegPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{68F0C1C1-17CB-4CED-8261-5C18EB92571A}_is1'
function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Resolve-Target([string]$Target, [bool]$NoRegistry) {
    if ([string]::IsNullOrWhiteSpace($Target)) {
        if ((-not $NoRegistry) -and (Test-Path $RegPath)) {
            $Target = [string](Get-ItemProperty $RegPath).InstallLocation
        } else { $Target = Join-Path $env:LOCALAPPDATA 'Programs\SRTVoiceStudio' }
    }
    $Target = [IO.Path]::GetFullPath($Target).TrimEnd('\','/')
    if ($Target -eq [IO.Path]::GetPathRoot($Target).TrimEnd('\','/')) { throw 'A drive root cannot be an app installation.' }
    if (-not (Test-Path -LiteralPath $Target -PathType Container)) { throw 'Installation folder not found.' }
    Assert-NoLinks $Target
    return $Target
}
function Assert-NoLinks([string]$Path) {
    $cursor = $Path
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Linked paths are not supported: $cursor"
            }
        }
        $parent = Split-Path -Parent $cursor
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
function Safe-Path([string]$Root, [string]$Relative) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or $Relative -match '(^[/\\]|[:\\]|(^|/)\.\.?(/|$))') {
        throw "Unsafe package path: $Relative"
    }
    $full = [IO.Path]::GetFullPath((Join-Path $Root ($Relative -replace '/', '\')))
    $prefix = [IO.Path]::GetFullPath($Root).TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escapes installation.' }
    Assert-NoLinks $full
    return $full
}
function Save-Json([string]$Path, $Value) {
    $temp = $Path + '.tmp'
    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $Path -Force
}
function History-Root([string]$Target) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $id = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Target.ToLowerInvariant())))).Replace('-','') }
    finally { $sha.Dispose() }
    $root = Join-Path $env:LOCALAPPDATA ('SRTVoiceStudio\updates\' + $id)
    Assert-NoLinks $root
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    return $root
}
function Assert-AppClosed {
    if (@(Get-Process -Name SRTVoiceStudio -ErrorAction SilentlyContinue).Count) {
        throw 'Close SRT Voice Studio before updating or restoring.'
    }
}
function Restore-Journal([string]$JournalPath, [string]$Target) {
    $j = Get-Content -LiteralPath $JournalPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($j.target -ne $Target) { throw 'Backup belongs to another installation.' }
    if ($j.state -eq 'restored') { return }
    $backupRoot = Split-Path -Parent $JournalPath
    # Validate every backup before changing anything. Never discard a failed backup.
    foreach ($e in @($j.entries)) {
        $dest = Safe-Path $Target ([string]$e.path)
        if ($e.old_sha256) {
            $saved = Safe-Path (Join-Path $backupRoot 'files') ([string]$e.path)
            if ((-not (Test-Path -LiteralPath $saved)) -or (Get-Sha256 $saved) -ne $e.old_sha256) {
                throw "Backup checksum failed; backup retained: $($e.path)"
            }
        }
        if ($j.state -eq 'applied' -and (Test-Path -LiteralPath $dest)) {
            $hash = Get-Sha256 $dest
            if ($hash -ne $e.old_sha256 -and $hash -ne $e.new_sha256) {
                throw "File changed since update; refusing to overwrite: $($e.path)"
            }
        }
    }
    $j.state = 'restoring'; Save-Json $JournalPath $j
    foreach ($e in @($j.entries)) {
        $dest = Safe-Path $Target ([string]$e.path)
        if ($e.old_sha256) {
            $saved = Safe-Path (Join-Path $backupRoot 'files') ([string]$e.path)
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
            Copy-Item -LiteralPath $saved -Destination $dest -Force
            if ((Get-Sha256 $dest) -ne $e.old_sha256) { throw 'Restore verification failed; retry Restore_Previous.cmd.' }
        } elseif (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Force }
    }
    if ($j.registry_used) {
        Set-ItemProperty -Path $RegPath -Name DisplayVersion -Value ([string]$j.old_version)
    }
    $j.state = 'restored'; Save-Json $JournalPath $j
}
