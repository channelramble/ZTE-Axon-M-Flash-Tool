# ZTE AXON M FLASH TOOL - menu front end for the scripts in .\scripts
$Version = '1.0.0'
. "$PSScriptRoot\scripts\Common.ps1"
try { $host.UI.RawUI.WindowTitle = "ZTE Axon M Flash Tool $Version" } catch {}

function Invoke-ToolScript([string]$Name, [string[]]$Arguments = @()) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path "$PSScriptRoot\scripts" $Name) @Arguments
}

function Read-Programmer {
    $p = (Read-Host 'Path to prog_emmc_firehose_fujisan.mbn (drag the file here)').Trim().Trim('"')
    if (-not (Test-Path $p)) { Write-Fail "Not found: $p"; return $null }
    return $p
}

function Show-QfilSteps {
    Write-Step 'Flashing TWRP with QFIL'
    Write-Detail '1. Put prog_emmc_firehose_fujisan.mbn, twrp-3.2.3-0_fujisan.img and config\rawprogram0.xml'
    Write-Detail '   from this tool in one short folder without spaces, e.g. C:\Z999-TWRP'
    Write-Detail '2. Run option 2 (Fix QFIL config) once.'
    Write-Detail '3. In QFIL: Configuration > FireHose Configuration > Device Type = eMMC'
    Write-Detail '   Flat Build, Programmer = prog_emmc_firehose_fujisan.mbn,'
    Write-Detail '   Load XML = rawprogram0.xml (cancel the patch prompt).'
    Write-Detail '4. Option 3 (Reboot phone to EDL), then click Download in QFIL right away.'
    Write-Detail '5. After "Download Succeed", hold Power + Vol Up until TWRP appears.'
    Write-Detail '   Do not boot Android first; stock firmware can restore the stock recovery.'
    Write-Detail 'If Download fails: hold Power ~15 s, boot Android, repeat from step 4.'
}

while ($true) {
    Write-Host ''
    Write-Host "  ZTE AXON M FLASH TOOL  v$Version" -ForegroundColor Cyan
    Write-Host '  ----------------------------------'
    Write-Host '  1  Check setup (read-only)'
    Write-Host '  2  Fix QFIL config (turn off reset Sahara state machine)'
    Write-Host '  3  Reboot phone to EDL (adb reboot edl)'
    Write-Host '  4  Show QFIL flashing steps'
    Write-Host '  5  Diagnostics: load programmer only (Sahara test)'
    Write-Host '  6  Diagnostics: read partition table (read-only)'
    Write-Host '  7  Undo QFIL config fix'
    Write-Host '  Q  Quit'
    $choice = (Read-Host '  Choose').Trim().ToUpper()
    Write-Host ''
    switch ($choice) {
        '1' { Invoke-ToolScript 'Test-Setup.ps1' }
        '2' { Invoke-ToolScript 'Fix-QFILConfig.ps1' }
        '3' { Invoke-ToolScript 'Enter-EDL.ps1' }
        '4' { Show-QfilSteps }
        '5' {
            Write-Caution 'After this the phone needs a fresh EDL session before QFIL will work.'
            $p = Read-Programmer
            if ($p) { Invoke-ToolScript 'Invoke-Sahara.ps1' @('-Programmer', $p) }
        }
        '6' {
            Write-Caution 'After this the phone needs a fresh EDL session before QFIL will work.'
            $ans = (Read-Host 'Is the programmer already loaded (did option 5 just succeed)? [y/N]').Trim().ToLower()
            if ($ans -eq 'y') { Invoke-ToolScript 'Get-PartitionTable.ps1' }
            else { $p = Read-Programmer; if ($p) { Invoke-ToolScript 'Get-PartitionTable.ps1' @('-Programmer', $p) } }
        }
        '7' { Invoke-ToolScript 'Fix-QFILConfig.ps1' @('-Revert') }
        'Q' { return }
        default { Write-Caution "Unknown choice '$choice'" }
    }
}
