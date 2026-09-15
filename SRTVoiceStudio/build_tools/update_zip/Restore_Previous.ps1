Param([string]$TargetDir = '', [switch]$SkipRegistry, [switch]$NonInteractive)
. (Join-Path $PSScriptRoot 'Update_Common.ps1')
$localJournal = Join-Path $PSScriptRoot 'journal.json'
if ((Test-Path -LiteralPath $localJournal) -and [string]::IsNullOrWhiteSpace($TargetDir)) {
    $TargetDir = [string](Get-Content -LiteralPath $localJournal -Raw -Encoding UTF8 | ConvertFrom-Json).target
}
$TargetDir = Resolve-Target $TargetDir ([bool]$SkipRegistry)
Assert-AppClosed
$history = History-Root $TargetDir
$lock = [IO.File]::Open((Join-Path $history 'update.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
try {
    $pointer = Join-Path $history 'latest.json'
    if (-not (Test-Path -LiteralPath $pointer)) { throw 'No previous update backup found for this installation.' }
    $latest = Get-Content -LiteralPath $pointer -Raw -Encoding UTF8 | ConvertFrom-Json
    if ((Test-Path -LiteralPath $localJournal) -and $latest.journal -ne $localJournal) { throw 'This backup is not the latest. Use the latest backup to avoid downgrading over newer changes.' }
    Restore-Journal $latest.journal $TargetDir
    Write-Host 'RESTORE SUCCESS. Open the previous SRT Voice Studio version normally.'
} finally { $lock.Dispose() }
