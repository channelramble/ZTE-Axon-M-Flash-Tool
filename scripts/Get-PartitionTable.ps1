# Read-only: dumps the phone's eMMC partition table through firehose and checks the recovery
# partition against config\rawprogram0.xml. Pass -Programmer to load the programmer first.
# Afterwards the phone stays in firehose mode; QFIL needs a fresh EDL session.
param([string]$Programmer, [string]$Port, [string]$OutDir)
. "$PSScriptRoot\Common.ps1"

$bin = Get-QpstBin
if (-not $bin -or -not (Test-Path (Join-Path $bin 'fh_loader.exe'))) { Write-Fail 'fh_loader.exe not found (install QPST).'; exit 1 }
$fh = Join-Path $bin 'fh_loader.exe'

if (-not $Port) { $Port = Get-EdlPort }
if (-not $Port) { Write-Fail 'The phone is not in EDL (no 9008 port).'; exit 1 }

if ($Programmer) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\Invoke-Sahara.ps1" -Port $Port -Programmer $Programmer
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Programmer did not load.'; exit 1 }
    Start-Sleep -Seconds 2
}

# fh_loader cannot open long paths or paths with spaces, so default to a short folder.
if (-not $OutDir) { $OutDir = "$env:SystemDrive\AxonM-FlashTool\gpt-" + (Get-Date -Format 'yyyyMMdd-HHmmss') }
if ($OutDir -match ' ' -or $OutDir.Length -gt 100) { Write-Fail 'Use a short -OutDir with no spaces, e.g. C:\AxonM-gpt'; exit 1 }
New-Item -ItemType Directory -Force $OutDir | Out-Null

Write-Step "Reading partition table on $Port (read-only)"
$log = Join-Path $OutDir 'fh_loader.log'
$p = Start-Process -FilePath $fh -WorkingDirectory $OutDir -NoNewWindow -PassThru -RedirectStandardOutput $log `
    -ArgumentList "--port=\\.\$Port", '--memoryname=emmc', "--getgptmainbackup=$OutDir\", '--noreset', '--noprompt', '--zlpawarehost=1'
if (-not $p.WaitForExit(120000)) { $p.Kill(); Write-Fail 'fh_loader timed out.'; exit 1 }

$gpt = Join-Path $OutDir 'gpt_main0.bin'
if (-not (Test-Path $gpt)) {
    Write-Fail "No partition table was read. Log: $log"
    Get-Content $log | Select-String 'ERROR' | Select-Object -Last 5 | ForEach-Object { Write-Detail $_.Line }
    exit 1
}

$parts = @(& "$PSScriptRoot\ConvertFrom-GPT.ps1" -Path $gpt)
$parts | Format-Table Name, StartSector, EndSector, SizeKB -AutoSize | Out-String -Width 200 | Write-Host

$rec = $parts | Where-Object { $_.Name -eq 'recovery' } | Select-Object -First 1
$xml = [xml](Get-Content (Join-Path $script:ToolRoot 'config\rawprogram0.xml'))
$entry = $xml.data.program | Where-Object { $_.label -eq 'recovery' } | Select-Object -First 1
if ($rec -and $entry) {
    if ([uint64]$entry.start_sector -eq $rec.StartSector -and [uint64]$entry.num_partition_sectors -eq $rec.Sectors) {
        Write-Pass "recovery is at sector $($rec.StartSector), $($rec.Sectors) sectors. Matches config\rawprogram0.xml."
    } else {
        Write-Fail "recovery on this phone is at $($rec.StartSector) ($($rec.Sectors) sectors), but rawprogram0.xml says $($entry.start_sector) ($($entry.num_partition_sectors)). Do not flash with it."
    }
}
Write-Detail "Saved to $OutDir"
Write-Detail 'The phone is still in firehose mode. Hold Power ~15 s to leave EDL.'
