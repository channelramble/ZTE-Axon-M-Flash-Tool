# Shared helpers for the ZTE Axon M Flash Tool. Dot-source this file.

$script:ToolRoot = Split-Path -Parent $PSScriptRoot

function Write-Step([string]$Text)    { Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Pass([string]$Text)    { Write-Host "  [OK]   $Text" -ForegroundColor Green }
function Write-Caution([string]$Text) { Write-Host "  [WARN] $Text" -ForegroundColor Yellow }
function Write-Fail([string]$Text)    { Write-Host "  [FAIL] $Text" -ForegroundColor Red }
function Write-Detail([string]$Text)  { Write-Host "         $Text" }

# Every adb.exe on PATH plus the usual platform-tools locations.
function Get-AdbCandidates {
    $paths = @()
    $paths += Get-Command adb.exe -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }
    $paths += @(
        (Join-Path $script:ToolRoot 'platform-tools\adb.exe'),
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        'C:\Android\android-sdk\platform-tools\adb.exe',
        'C:\platform-tools\adb.exe',
        "$env:USERPROFILE\platform-tools\adb.exe",
        "$env:USERPROFILE\Downloads\platform-tools\adb.exe"
    )
    $paths | Where-Object { $_ -and (Test-Path $_) } | ForEach-Object { (Resolve-Path $_).Path } | Select-Object -Unique
}

# Returns the minor version (the 41 in 1.0.41), or 0 if unknown.
function Get-AdbVersion([string]$Path) {
    $out = & $Path version 2>$null | Out-String
    if ($out -match 'version 1\.0\.(\d+)') { return [int]$Matches[1] }
    return 0
}

# Newest adb found. adb older than 1.0.31 can't do RSA auth, so phones show as "offline"; callers require 1.0.32+.
function Get-BestAdb {
    $best = $null
    foreach ($p in Get-AdbCandidates) {
        $v = Get-AdbVersion $p
        if (-not $best -or $v -gt $best.Minor) { $best = [pscustomobject]@{ Path = $p; Minor = $v } }
    }
    return $best
}

function Get-QpstBin {
    foreach ($d in @("${env:ProgramFiles(x86)}\Qualcomm\QPST\bin", "$env:ProgramFiles\Qualcomm\QPST\bin")) {
        if ($d -and (Test-Path (Join-Path $d 'QSaharaServer.exe'))) { return $d }
    }
    return $null
}

# COM port of a Qualcomm HS-USB QDLoader 9008 device, e.g. "COM28", or $null.
function Get-EdlPort {
    $d = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match 'VID_05C6&PID_9008' } | Select-Object -First 1
    if ($d -and $d.FriendlyName -match '\((COM\d+)\)') { return $Matches[1] }
    return $null
}

function Get-QfilConfigPath { Join-Path $env:APPDATA 'Qualcomm\QFIL\QFIL.config' }
