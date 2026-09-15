Param([string]$TargetDir = '', [switch]$SkipRegistry, [switch]$NonInteractive)
. (Join-Path $PSScriptRoot 'Update_Common.ps1')
$TargetDir = Resolve-Target $TargetDir ([bool]$SkipRegistry)
Assert-AppClosed
$history = History-Root $TargetDir
$lock = [IO.File]::Open((Join-Path $history 'update.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
try {
    $pointer = Join-Path $history 'latest.json'
    if (Test-Path -LiteralPath $pointer) {
        $previous = Get-Content -LiteralPath $pointer -Raw -Encoding UTF8 | ConvertFrom-Json
        $pending = Get-Content -LiteralPath $previous.journal -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($pending.state -in @('applying','restoring')) {
            Restore-Journal $previous.journal $TargetDir
            throw 'Interrupted update restored. Open the old app or run the update again.'
        }
    }
    $manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'update_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not (Test-Path -LiteralPath (Join-Path $TargetDir 'SRTVoiceStudio.exe') -PathType Leaf)) { throw 'Installed app executable not found. Use Restore_Previous.cmd if a prior update was interrupted.' }
    if ($manifest.format -ne 4 -or $manifest.product -ne 'SRT Voice Studio' -or
        $manifest.app_id -ne '{68F0C1C1-17CB-4CED-8261-5C18EB92571A}') { throw 'Unsupported update package.' }
    $registryUsed = (-not $SkipRegistry) -and (Test-Path $RegPath)
    $oldVersion = [string]$manifest.from_version
    if ($registryUsed) {
        $oldVersion = [string](Get-ItemProperty $RegPath).DisplayVersion
        if ($oldVersion -notin @($manifest.from_version,$manifest.to_version)) { throw 'Wrong installed version. No files changed.' }
    }
    $plan = @(); $seen = @{}; $already = 0
    foreach ($e in @($manifest.files) + @($manifest.delete)) {
        $rel = [string]$e.path
        if ($seen.ContainsKey($rel)) { throw 'Duplicate package path.' }; $seen[$rel] = $true
        if ($rel -match '^unins[^/]*$') { throw 'Package must preserve the uninstaller.' }
        $dest = Safe-Path $TargetDir $rel
        $isDelete = -not ($e.PSObject.Properties.Name -contains 'sha256')
        $newHash = $null; $payload = $null
        if (-not $isDelete) {
            $payload = Safe-Path (Join-Path $PSScriptRoot 'payload') $rel
            $newHash = [string]$e.sha256
            if ((Get-Sha256 $payload) -ne $newHash -or (Get-Item -LiteralPath $payload).Length -ne $e.size) { throw "Bad payload: $rel" }
        }
        $hash = if (Test-Path -LiteralPath $dest) { Get-Sha256 $dest } else { $null }
        if ($hash -eq $newHash) { $already++; continue }
        $accepted = @($e.old_sha256)
        if ($e.PSObject.Properties.Name -contains 'old_sha256_variants') { $accepted += @($e.old_sha256_variants) }
        if ($hash -notin $accepted) { throw "Baseline checksum mismatch: $rel. No files changed." }
        $plan += [pscustomobject]@{path=$rel;old_sha256=$hash;new_sha256=$newHash;payload=$payload}
    }
    if ($plan.Count -eq 0) { Write-Host 'This update is already installed. Existing backup preserved.'; return }
    # A known baseline can already contain target bytes for files that only
    # differ in another verified baseline variant. Preserve them unchanged.
    if ($oldVersion -eq $manifest.to_version) { throw 'Version and file hashes disagree. Restore the previous update first.' }
    $backup = Join-Path $history ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($e in $plan) {
        if ($e.old_sha256) {
            $saved = Safe-Path (Join-Path $backup 'files') $e.path
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $saved) | Out-Null
            Copy-Item -LiteralPath (Safe-Path $TargetDir $e.path) -Destination $saved
            if ((Get-Sha256 $saved) -ne $e.old_sha256) { throw 'Backup verification failed. Installed app unchanged.' }
        }
    }
    foreach ($name in @('Restore_Previous.cmd','Restore_Previous.ps1','Update_Common.ps1')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $backup $name)
    }
    $journalPath = Join-Path $backup 'journal.json'
    $journal = [ordered]@{target=$TargetDir;old_version=$oldVersion;new_version=[string]$manifest.to_version;registry_used=$registryUsed;state='applying';entries=$plan}
    Save-Json $journalPath $journal
    Save-Json $pointer @{journal=$journalPath}
    try {
        foreach ($e in $plan) {
            $dest = Safe-Path $TargetDir $e.path
            if ($e.new_sha256) {
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
                Copy-Item -LiteralPath $e.payload -Destination $dest -Force
                if ((Get-Sha256 $dest) -ne $e.new_sha256) { throw 'Post-update checksum failed.' }
            } else { Remove-Item -LiteralPath $dest -Force }
        }
        # Check the actual frozen application in isolated settings, without editing user data.
        $psi = New-Object Diagnostics.ProcessStartInfo
        $psi.FileName = Join-Path $TargetDir 'SRTVoiceStudio.exe'
        $psi.Arguments = '--update-health-check'
        $psi.WorkingDirectory = $TargetDir
        $psi.UseShellExecute = $false
        $psi.EnvironmentVariables['LOCALAPPDATA'] = Join-Path $backup 'health-check'
        $process = [Diagnostics.Process]::Start($psi)
        if (-not $process.WaitForExit(300000)) { $process.Kill(); $process.WaitForExit(); throw 'New app health check timed out.' }
        if ($process.ExitCode -ne 0) { throw "New app health check failed: $($process.ExitCode)" }
        $report = Join-Path $backup 'health-check\SRTVoiceStudio\update-health.json'
        if (-not (Test-Path -LiteralPath $report)) { throw 'New app did not produce its health report.' }
        $health = Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $health.passed -or $health.version -ne $manifest.to_version) { throw 'Health report version or result is invalid.' }
        if ($registryUsed) { Set-ItemProperty $RegPath -Name DisplayVersion -Value ([string]$manifest.to_version) }
        $journal.state = 'applied'; Save-Json $journalPath $journal
        Write-Host "UPDATE SUCCESS: $($manifest.to_version)"
        Write-Host "Backup retained: $backup"
        Write-Host 'If a problem appears later, close the app and run Restore_Previous.cmd.'
    } catch {
        $failure = $_
        try { Restore-Journal $journalPath $TargetDir; Write-Host 'Previous version restored.' }
        catch { Write-Error "Automatic restore failed. Backup retained at $backup. Run its Restore_Previous.cmd. $_" -ErrorAction Continue }
        throw $failure
    }
} finally { $lock.Dispose() }
