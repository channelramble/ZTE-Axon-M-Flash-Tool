# Findings

How each problem was tracked down on an AT&T Axon M with QPST/QFIL 2.0.1.9, Qualcomm 9008 driver 2.1.2.7, Windows 10 (Boot Camp on a 2012 MacBook Pro).

## 1. QFIL fails at Sahara: `SAHARA_NAK_INVALID_CMD`

**What QFIL showed** on every attempt, including after entering EDL properly with `adb reboot edl`:

```
ERROR: function: is_ack_successful:991 SAHARA_NAK_INVALID_CMD
ERROR: function: sahara_start:895 Exiting abruptly
ERROR: function: sahara_main:924 Sahara protocol error
ERROR: function: main:303 Uploading  Image using Sahara protocol failed
Download Fail:Sahara Fail:QSaharaServer Fail:Process fail
```

**Evidence for the cause:**

- `%APPDATA%\Qualcomm\QFIL\QFIL.config` contained `<add key="RESETSAHARASTATEMACHINE" value="True;..."/>`.
- QFIL's download library `SwDownloadDLL.dll` contains the strings `ARG_STR_RESETSAHARASTATEMACHINE` and ` -k`, which it uses to build the QSaharaServer command line.
- `QSaharaServer.exe -h` describes `-k` as: `--sendclearstate  Send command to target to reset the Sahara State Machine. Does not work on all targets.`
- A Sahara NAK of `0x01` (`NAK_INVALID_CMD`) is what a target sends back for a command it doesn't accept.
- The tool's own Sahara client (`scripts/Invoke-Sahara.ps1`), which never sends that reset command, loaded the same programmer over the same cable on the first try:

```
HELLO: version=2 minVersion=1 maxCmdLen=0x400 mode=0
READ_DATA64 image=13 offset=0x0 len=0x40
READ_DATA64 image=13 offset=0x40 len=0x230
READ_DATA64 image=13 offset=0x1000 len=0x1000
END_IMAGE_TX image=13 status=0x00 (SUCCESS) after 117 data requests
DONE_RESP cmd=0x6 status=0x1
PROGRAMMER LOADED
```

- With `RESETSAHARASTATEMACHINE` set to `False`, QFIL's Download succeeded on the same phone and TWRP booted.

So the firehose programmer (`prog_emmc_firehose_fujisan.mbn`), the driver and the cable were fine all along. The extra reset command was the problem.

## 2. adb shows the phone as `offline`

The PC had nine copies of `adb.exe`. The first one on PATH was `C:\Windows\adb.exe`, version **1.0.26**, the same version as the copy in `C:\Program Files\ZTE Handset USB Driver\`. adb older than 1.0.31 predates the RSA authentication that Android 4.2.2+ requires, so the phone shows up as `offline`. The tool requires 1.0.32 or newer to be safe. Using platform-tools adb 1.0.41 by its full path fixed it.

Even with the new adb, the phone sometimes sat at `offline`. `adb reconnect offline` moved it to `unauthorized`, then accepting the prompt on the phone made it `device`. `scripts/Enter-EDL.ps1` does this automatically.

## 3. Phone keeps dropping off USB

With the phone on an unpowered USB 2.0 hub (Terminus Tech, `VID_1A40&PID_0101`), Windows showed the phone's USB device disappearing and reappearing every few seconds, and adb flipped between `offline`, missing and `device`. Plugged straight into the MacBook's port, the connection was stable. `scripts/Test-Setup.ps1` warns when the phone is behind a hub.

The 2012 MacBook Pro only has USB 3.0 ports. Flashing worked fine on them, so USB 3.0 by itself was not a problem here.

## 4. Button-combo EDL vs `adb reboot edl`

From the TWRP developer on XDA: the Vol+/Vol-/Power combo can put the phone in ZTE's DFU mode, which QFIL also sees as a 9008 port, and `adb reboot edl` gets real EDL. On the test phone, QFIL still failed after `adb reboot edl` until finding 1 was fixed, so DFU wasn't the cause here.

Later, with Android not booting, the button combo (phone off, hold Vol Up + Vol Down, plug in USB) gave real EDL: the phone sent a normal Sahara HELLO and accepted the programmer. `adb reboot edl` is the easiest way in when Android boots; the buttons work when it doesn't.

## 5. One Sahara attempt per EDL session

After a failed QFIL attempt, the phone stayed on the 9008 port but sent nothing at all: a QSaharaServer run waited 45 s without receiving a HELLO. Holding Power ~15 s, booting Android and running `adb reboot edl` again gave a fresh session.

## 6. Wrong sector in the TWRP `rawprogram0.xml`

The `rawprogram0.xml` shipped with the TWRP build:

```xml
<program ... label="recovery" num_partition_sectors="131072" start_byte_hex="0x6690000" start_sector="210048"/>
```

The phone's GPT (`docs/PARTITIONS.md`) puts `recovery` at sectors 1181696 to 1312767. A 64 MB write at sector 210048 covers 210048 to 341119, which overlaps `fbop` (262144 to 262399) and never touches `recovery`. That's why people saw "flash successful" but still booted stock recovery, and why some ended up stuck. The developer later posted the corrected line on XDA. `config/rawprogram0.xml` uses it:

```xml
<program ... label="recovery" num_partition_sectors="131072" start_byte_hex="0x24100000" start_sector="1181696"/>
```

## 7. LineageOS 23 zip won't install from TWRP 3.2.3

`adb sideload` of `lineage-23.2-20261006-UNOFFICIAL-fujisan.zip` stopped at `Total xfer: 0.00x`. The transfer itself was fine; TWRP's `/tmp/recovery.log` showed the zip's installer crashing on startup:

```
sideload-host file size 1068692459 block size 65536
Installing zip file '/sideload/package.zip'
arc4random data MADV_WIPEONFORK failed: No such file or directory
Updater process ended with signal: 6
```

The ROM's installer is built against Android 16's C library, which needs `MADV_WIPEONFORK` support in the kernel. TWRP 3.2.3's kernel doesn't have it, so the installer aborts before writing anything. The ROM post says to use the latest TWRP or its LineageOS recovery.

`TWRP-3.7.0_9-O-fujisan-20260809.img` from that thread did not boot on the AT&T test phone (stock Nougat 7.1.2). The "O" suggests an Oreo base, which the AT&T model never received; that's an inference, not confirmed. An AT&T owner in the ROM thread reports the LineageOS recovery booting and installing the zip, but LineageOS then stuck at the ZTE logo on their phone.

## 8. Restoring recovery through firehose

After the 3.7.0 image broke recovery, TWRP 3.2.3 was restored over EDL: programmer loaded with `Invoke-Sahara.ps1`, a fresh GPT read confirmed `recovery` at 1181696/131072, `fh_loader --sendxml=rawprogram0.xml` wrote the image, and a readback of the written sectors matched `twrp-3.2.3-0_fujisan.img` byte for byte. QFIL's Download does the same write.

## 9. Smaller notes

- `fh_loader.exe` fails to open its log and output files when the working path is very long (around 200 characters). `Get-PartitionTable.ps1` defaults to `C:\AxonM-FlashTool\...` for that reason.
- `fh_loader --getgptmainbackup=<dir>` saves `gpt_main0.bin` and `gpt_backup0.bin` in its working directory, not in `<dir>`. `Get-PartitionTable.ps1` sets both to the same folder.
- The `31: mba.mbn` and similar lines at the top of QFIL's log are just QSaharaServer's default image table, not errors.
- QFIL's Device Type must be `emmc` for this programmer. The firehose reports `Supported Functions: program configure nop firmwarewrite patch setbootablestoragedrive ufs emmc power benchmark read getstorageinfo getsha256digest erase peek poke getnumdisksectors`.
