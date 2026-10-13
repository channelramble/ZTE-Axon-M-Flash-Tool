# Minimal Sahara client: uploads a firehose programmer to a Qualcomm 9008 device and logs every packet.
# Diagnostic alternative to QFIL's Sahara step. Sends no "reset state machine" command.
# Afterwards the phone is in firehose mode; QFIL needs a fresh EDL session.
param([string]$Port, [Parameter(Mandatory = $true)][string]$Programmer)
. "$PSScriptRoot\Common.ps1"

if (-not $Port) { $Port = Get-EdlPort }
if (-not $Port) { Write-Fail 'No 9008 port found. Put the phone in EDL first.'; exit 1 }
if (-not (Test-Path $Programmer)) { Write-Fail "Programmer not found: $Programmer"; exit 1 }

$img = [System.IO.File]::ReadAllBytes((Resolve-Path $Programmer).Path)
"Port: $Port"
"Programmer: $Programmer ($($img.Length) bytes)"
$sp = New-Object System.IO.Ports.SerialPort $Port, 115200
$sp.ReadTimeout = 15000
$sp.WriteTimeout = 15000
$sp.Open()

$names = @{ 0x00='SUCCESS'; 0x01='NAK_INVALID_CMD'; 0x02='NAK_PROTOCOL_MISMATCH'; 0x03='NAK_INVALID_TARGET_PROTOCOL';
  0x04='NAK_INVALID_HOST_PROTOCOL'; 0x05='NAK_INVALID_PACKET_SIZE'; 0x06='NAK_UNEXPECTED_IMAGE_ID'; 0x07='NAK_INVALID_HEADER_SIZE';
  0x08='NAK_INVALID_DATA_SIZE'; 0x09='NAK_INVALID_IMAGE_TYPE'; 0x0A='NAK_INVALID_TX_LENGTH'; 0x0B='NAK_INVALID_RX_LENGTH';
  0x0C='NAK_GENERAL_TX_RX_ERROR'; 0x0D='NAK_READ_DATA_ERROR'; 0x14='NAK_INVALID_ELF_HDR'; 0x15='NAK_UNKNOWN_HOST_ERROR';
  0x16='NAK_TIMEOUT_RX'; 0x17='NAK_TIMEOUT_TX'; 0x18='NAK_INVALID_HOST_MODE' }

function Read-Exact([int]$n) {
  $buf = New-Object byte[] $n; $got = 0
  while ($got -lt $n) { $got += $sp.Read($buf, $got, $n - $got) }
  return ,$buf
}
function U32($b, $o) { [BitConverter]::ToUInt32($b, $o) }
function U64($b, $o) { [BitConverter]::ToUInt64($b, $o) }
function Hex($b) { ($b | ForEach-Object { $_.ToString('X2') }) -join ' ' }
function Send-Words([uint32[]]$w) {
  $b = New-Object byte[] ($w.Length * 4)
  for ($i = 0; $i -lt $w.Length; $i++) { [BitConverter]::GetBytes($w[$i]).CopyTo($b, $i * 4) }
  $sp.Write($b, 0, $b.Length)
}
function Read-Packet {
  $h = Read-Exact 8
  $len = U32 $h 4
  $all = New-Object byte[] ([Math]::Max($len, 8))
  $h.CopyTo($all, 0)
  if ($len -gt 8) { (Read-Exact ($len - 8)).CopyTo($all, 8) }
  return @{ cmd = (U32 $h 0); len = $len; data = $all }
}

$script:code = 1
function Main {
try {
  $p = Read-Packet
  if ($p.cmd -ne 1) { "First packet was cmd 0x{0:X}, not HELLO: {1}" -f $p.cmd, (Hex $p.data); $script:code = 3; return }
  "HELLO: version={0} minVersion={1} maxCmdLen=0x{2:X} mode={3}" -f (U32 $p.data 8), (U32 $p.data 12), (U32 $p.data 16), (U32 $p.data 20)
  $mode = U32 $p.data 20
  Send-Words @(2, 0x30, 2, 1, 0, $mode, 0, 0, 0, 0, 0, 0)
  $reads = 0
  while ($true) {
    $p = Read-Packet
    if ($p.cmd -eq 3) {
      $id = U32 $p.data 8; $off = U32 $p.data 12; $ln = U32 $p.data 16
      if ($reads -lt 3) { "READ_DATA image=$id offset=0x{0:X} len=0x{1:X}" -f $off, $ln }
      $sp.Write($img, [int]$off, [int]$ln); $reads++
    } elseif ($p.cmd -eq 0x12) {
      $id = U64 $p.data 8; $off = U64 $p.data 16; $ln = U64 $p.data 24
      if ($reads -lt 3) { "READ_DATA64 image=$id offset=0x{0:X} len=0x{1:X}" -f $off, $ln }
      $sp.Write($img, [int]$off, [int]$ln); $reads++
    } elseif ($p.cmd -eq 4) {
      $st = [int](U32 $p.data 12)
      "END_IMAGE_TX image={0} status=0x{1:X2} ({2}) after {3} data requests" -f (U32 $p.data 8), $st, $names[$st], $reads
      if ($st -ne 0) { $script:code = 2; return }
      Send-Words @(5, 8)
      $r = Read-Packet
      "DONE_RESP cmd=0x{0:X} status=0x{1:X}" -f $r.cmd, (U32 $r.data 8)
      "PROGRAMMER LOADED - phone is now in firehose mode"
      $script:code = 0; return
    } else {
      "Unexpected packet cmd=0x{0:X} len={1}: {2}" -f $p.cmd, $p.len, (Hex $p.data); $script:code = 4; return
    }
  }
} catch [System.TimeoutException] {
  "TIMEOUT: the phone sent nothing for 15 s (EDL session already used, or not really in EDL)"; $script:code = 5
} catch {
  "ERROR: $($_.Exception.Message)"; $script:code = 6
} finally {
  $sp.Close()
}
}
Main
exit $script:code
