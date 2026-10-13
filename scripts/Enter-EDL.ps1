# Reboots an Axon M that is booted into Android into real EDL (Qualcomm 9008) with "adb reboot edl".
# The Vol+/Vol-/Power combo can land in ZTE's DFU mode instead, which also shows up as 9008.
param([string]$Serial, [int]$TimeoutSeconds = 300)
. "$PSScriptRoot\Common.ps1"

$adb = Get-BestAdb
if (-not $adb -or $adb.Minor -lt 32) { Write-Fail 'Need adb 1.0.32 or newer (Android SDK platform-tools).'; exit 1 }
Write-Detail "Using $($adb.Path) (1.0.$($adb.Minor))"

$existing = Get-EdlPort
if ($existing) {
    Write-Caution "The phone is already in EDL on $existing."
    Write-Detail 'If QFIL already failed in this session, hold Power ~15 s to restart into Android and run this again.'
    exit 0
}

function Get-AdbDevices {
    & $adb.Path devices | Select-Object -Skip 1 | ForEach-Object {
        if ($_ -match '^(\S+)\s+(\S+)$') { [pscustomobject]@{ Serial = $Matches[1]; State = $Matches[2] } }
    }
}

Write-Step 'Waiting for the phone (booted into Android, USB debugging on, plugged straight into the PC)'
$last = ''; $offlineSince = $null; $sent = $false
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    $rows = @(Get-AdbDevices)
    if ($Serial) { $rows = @($rows | Where-Object { $_.Serial -eq $Serial }) }
    if ($rows.Count -gt 1) {
        Write-Fail 'More than one device is connected. Run again with -Serial <serial>:'
        $rows | ForEach-Object { Write-Detail "$($_.Serial)  $($_.State)" }
        exit 1
    }
    $state = 'not connected'
    if ($rows.Count -eq 1) { $state = $rows[0].State }

    if ($state -ne $last) {
        Write-Detail ("{0:HH:mm:ss}  adb: {1}" -f (Get-Date), $state)
        if ($state -eq 'unauthorized') { Write-Caution 'Unlock the phone and accept "Allow USB debugging?" (check BOTH screens). Tick "Always allow".' }
        if ($state -eq 'offline') { Write-Caution 'If it stays offline: turn USB debugging off and on, or switch USB mode Charging <-> File transfer.' }
        $last = $state
    }

    # A stuck "offline" transport often recovers after a reconnect.
    if ($state -eq 'offline') {
        if (-not $offlineSince) { $offlineSince = Get-Date }
        elseif (((Get-Date) - $offlineSince).TotalSeconds -gt 15) { & $adb.Path reconnect offline | Out-Null; $offlineSince = $null }
    } else { $offlineSince = $null }

    if ($state -eq 'device') {
        $s = $rows[0].Serial
        $codename = (& $adb.Path -s $s shell getprop ro.product.device 2>$null | Out-String).Trim()
        if ($codename -and $codename -ne 'fujisan') { Write-Fail "This phone is '$codename', not an Axon M (fujisan). Stopping."; exit 1 }
        & $adb.Path -s $s reboot edl
        if ($LASTEXITCODE -eq 0) { $sent = $true; break }
    }
    Start-Sleep -Milliseconds 700
}
if (-not $sent) { Write-Fail 'Timed out waiting for an authorized adb connection.'; exit 1 }

$port = $null
for ($i = 0; $i -lt 60 -and -not $port; $i++) { Start-Sleep -Milliseconds 500; $port = Get-EdlPort }
if (-not $port) { Write-Fail 'The 9008 port did not appear. Check Device Manager and the Qualcomm driver.'; exit 1 }

Write-Pass "Phone is in EDL on $port (screen black, red LED)."
Write-Detail 'Click Download in QFIL now. If it fails, hold Power ~15 s and run this again;'
Write-Detail 'the phone does not accept a second attempt in the same EDL session.'
