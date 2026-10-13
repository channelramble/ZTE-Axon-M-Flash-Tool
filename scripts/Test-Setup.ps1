# Read-only check of everything that broke QFIL flashing on the Axon M.
. "$PSScriptRoot\Common.ps1"

Write-Step 'ADB'
$best = $null
$all = @(Get-AdbCandidates)
if (-not $all) {
    Write-Fail 'No adb.exe found. Install Android SDK platform-tools.'
} else {
    foreach ($p in $all) { Write-Detail ("1.0.{0,-4} {1}" -f (Get-AdbVersion $p), $p) }
    $best = Get-BestAdb
    if ($best.Minor -ge 32) {
        Write-Pass "Newest adb is 1.0.$($best.Minor): $($best.Path) (the tool uses this one)"
    } else {
        Write-Fail "Newest adb is 1.0.$($best.Minor). Need 1.0.32+ or the phone shows as 'offline'."
    }
    $onPath = Get-Command adb.exe -ErrorAction SilentlyContinue
    if ($onPath) {
        $v = Get-AdbVersion $onPath.Source
        if ($v -lt 32) {
            Write-Caution "Typing plain 'adb' runs $($onPath.Source) (1.0.$v), which is too old."
            Write-Detail 'Run adb by its full path (above) or put platform-tools first in PATH.'
        }
    }
}

Write-Step 'QPST / QFIL'
$bin = Get-QpstBin
if ($bin) {
    $qfil = Join-Path $bin 'QFIL.exe'
    $ver = 'not found'
    if (Test-Path $qfil) { $ver = (Get-Item $qfil).VersionInfo.FileVersion }
    Write-Pass "QPST: $bin (QFIL $ver)"
    if (-not (Test-Path (Join-Path $bin 'fh_loader.exe'))) {
        Write-Caution 'fh_loader.exe missing (only needed by the partition-table reader).'
    }
} else {
    Write-Fail 'QPST not found. Install QPST 2.7.x (it includes QFIL).'
}

Write-Step 'QFIL config'
$cfg = Get-QfilConfigPath
if (-not (Test-Path $cfg)) {
    Write-Caution "No $cfg yet. Open and close QFIL once, then run 'Fix QFIL config'."
} else {
    $m = Select-String -Path $cfg -Pattern 'key="RESETSAHARASTATEMACHINE" value="([^"]*)"' | Select-Object -First 1
    if (-not $m) {
        Write-Caution 'RESETSAHARASTATEMACHINE is not in QFIL.config (different QFIL version?).'
    } elseif ($m.Matches[0].Groups[1].Value -like 'False*') {
        Write-Pass 'Reset Sahara state machine is OFF.'
    } else {
        Write-Fail "Reset Sahara state machine is ON. The Axon M answers it with SAHARA_NAK_INVALID_CMD. Run 'Fix QFIL config'."
    }
    $dt = Select-String -Path $cfg -Pattern 'key="DEVICETYPE" value="([^"]*)"' | Select-Object -First 1
    if ($dt) {
        $t = $dt.Matches[0].Groups[1].Value
        if ($t -eq 'emmc') { Write-Pass 'Device type: emmc' }
        else { Write-Caution "Device type is '$t'. The Axon M needs emmc (QFIL > Configuration > FireHose Configuration)." }
    }
}

Write-Step 'Phone connection'
$devs = @(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
    Where-Object { $_.InstanceId -match '^USB\\VID_(05C6|19D2)&PID_[0-9A-F]{4}\\' })
if (-not $devs) { Write-Detail 'No ZTE or Qualcomm USB device connected right now.' }
foreach ($d in $devs) {
    $mode = 'Android'
    if ($d.InstanceId -match 'PID_9008') { $mode = 'EDL (9008)' }
    Write-Detail "$mode : $($d.FriendlyName)"
    $parent = (Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data
    if ($parent -and $parent -notmatch 'ROOT_HUB') {
        Write-Caution 'Connected through a USB hub. If the phone keeps dropping out, plug it straight into the PC.'
    }
}
if ($best -and $best.Minor -ge 32) {
    & $best.Path devices | Select-Object -Skip 1 | Where-Object { $_ -match '\S' } | ForEach-Object { Write-Detail "adb: $_" }
}
