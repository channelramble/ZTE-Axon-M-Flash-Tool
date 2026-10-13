# Parses a GPT dump (gpt_main0.bin: protective MBR + header + entries) into partition objects.
param([Parameter(Mandatory = $true)][string]$Path)

$b = [System.IO.File]::ReadAllBytes($Path)
$sig = [System.Text.Encoding]::ASCII.GetString($b, 512, 8)
if ($sig -ne 'EFI PART') { throw "No GPT header at LBA 1 of $Path (found '$sig')" }
$entLba = [BitConverter]::ToUInt64($b, 512 + 72)
$count = [BitConverter]::ToUInt32($b, 512 + 80)
$size = [BitConverter]::ToUInt32($b, 512 + 84)
$base = [int]$entLba * 512
for ($i = 0; $i -lt $count; $i++) {
    $o = $base + $i * $size
    if ($o + $size -gt $b.Length) { break }
    $first = [BitConverter]::ToUInt64($b, $o + 32)
    if ($first -eq 0) { continue }
    $last = [BitConverter]::ToUInt64($b, $o + 40)
    [pscustomobject]@{
        Name        = [System.Text.Encoding]::Unicode.GetString($b, $o + 56, 72).TrimEnd([char]0)
        StartSector = $first
        EndSector   = $last
        Sectors     = $last - $first + 1
        SizeKB      = ($last - $first + 1) * 512 / 1024
    }
}
