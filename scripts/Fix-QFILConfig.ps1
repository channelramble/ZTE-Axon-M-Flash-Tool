# Turns off QFIL's "reset Sahara state machine" option. With it on, QFIL runs QSaharaServer
# with -k, which the Axon M rejects with SAHARA_NAK_INVALID_CMD. -Revert turns it back on.
param([switch]$Revert, [string]$ConfigPath)
. "$PSScriptRoot\Common.ps1"

$isLiveConfig = -not $ConfigPath
if (-not $ConfigPath) { $ConfigPath = Get-QfilConfigPath }
if (-not (Test-Path $ConfigPath)) {
    Write-Fail "$ConfigPath not found. Open QFIL once, close it, then run this again."
    exit 1
}

# QFIL writes its config when it closes, which would undo the edit.
if ($isLiveConfig -and (Get-Process QFIL -ErrorAction SilentlyContinue)) {
    Write-Caution 'QFIL is open. Close it now; waiting...'
    while (Get-Process QFIL -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 1 }
    Start-Sleep -Seconds 1
}

$from = 'True'; $to = 'False'
if ($Revert) { $from = 'False'; $to = 'True' }

$text = [System.IO.File]::ReadAllText($ConfigPath)
if ($text -notmatch 'key="RESETSAHARASTATEMACHINE"') {
    Write-Caution 'RESETSAHARASTATEMACHINE is not in this QFIL.config. Nothing changed.'
    exit 1
}
$pattern = '(key="RESETSAHARASTATEMACHINE" value=")' + $from + '(;|")'
if ($text -notmatch $pattern) {
    Write-Pass "Already $to. Nothing to do."
    exit 0
}

$backup = "$ConfigPath.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
Copy-Item $ConfigPath $backup
$new = [regex]::Replace($text, $pattern, '${1}' + $to + '${2}')
[System.IO.File]::WriteAllText($ConfigPath, $new, (New-Object System.Text.UTF8Encoding $true))
Write-Pass "RESETSAHARASTATEMACHINE set to $to."
Write-Detail "Backup: $backup"
