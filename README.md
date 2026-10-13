# ZTE Axon M Flash Tool

Scripts, a corrected config and notes for flashing the **ZTE Axon M** (Z999, codename `fujisan`, Snapdragon 821 / MSM8996) with Qualcomm **QFIL** in EDL mode. It includes the fix for QFIL failing with `SAHARA_NAK_INVALID_CMD` / "Sahara protocol error".

Tested on an AT&T Axon M flashing the unofficial TWRP 3.2.3-0 for fujisan from XDA, using QFIL 2.0.1.9 on Windows 10.

> **Warning:** EDL flashing writes straight to the phone's storage. The wrong file or sector can brick it. Use this at your own risk.

## What goes wrong, and the fix

| Symptom | Cause | Fix |
|---|---|---|
| QFIL: `is_ack_successful SAHARA_NAK_INVALID_CMD`, `sahara_main Sahara protocol error`, `Download Fail:Sahara Fail:QSaharaServer Fail:Process fail` | QFIL's `RESETSAHARASTATEMACHINE` setting makes it run QSaharaServer with `-k` ("reset Sahara state machine"). The Axon M rejects that command. | Turn the setting off: menu option **2** (`scripts\Fix-QFILConfig.ps1`). |
| `adb devices` lists the phone as `offline` | An old `adb.exe` earlier in PATH. On the test PC, `C:\Windows\adb.exe` was 1.0.26, the same version bundled with the ZTE Handset USB Driver. | Use platform-tools adb 1.0.32 or newer. The tool always picks the newest copy it can find. |
| Still `offline` with a new adb | The phone's adbd is stuck | Turn USB debugging off and on, or switch USB mode Charging / File transfer. The tool also runs `adb reconnect offline`. |
| Phone keeps disconnecting and reconnecting | An unpowered USB hub can't supply the phone | Plug it straight into the PC. |
| 9008 port shows up but QFIL can't talk to the phone | Usually the QFIL setting in the first row. The TWRP developer also reports that the Vol+/Vol-/Power combo can enter ZTE's DFU mode, which also appears as 9008. | Prefer `adb reboot edl` (menu option **3**). On the AT&T test phone the button combo gave real EDL too. |
| A second Download attempt fails right away | After a failed attempt the phone stops answering Sahara until it reboots | Hold Power ~15 s, boot Android, enter EDL again. |
| TWRP "flashes fine" but stock recovery is still there, or worse | The `rawprogram0.xml` in the TWRP download uses `start_sector="210048"`, which is not the recovery partition (it overlaps ZTE's `fbop` partition) | Use `config\rawprogram0.xml` from this repo (`start_sector="1181696"`, checked against the phone's partition table). |
| LineageOS 23 zip: `adb sideload` stops at `0.00x`; TWRP's `/tmp/recovery.log` shows `arc4random data MADV_WIPEONFORK failed` and `Updater process ended with signal: 6` | The ROM's Android 16 installer needs a newer kernel feature than TWRP 3.2.3 has, so it aborts before writing anything | Install with the recovery linked in the ROM thread, as its post says. |
| Recovery won't boot after flashing a different recovery | The new recovery doesn't suit the phone's firmware | See "Restoring a recovery that won't boot" below. |

Full details and evidence: [docs/FINDINGS.md](docs/FINDINGS.md). Partition layout: [docs/PARTITIONS.md](docs/PARTITIONS.md).

## Requirements (not included)

- Windows 10 or 11
- QPST 2.7.x (Qualcomm's flashing suite; it includes QFIL) and the Qualcomm HS-USB QDLoader 9008 driver
- [Android SDK platform-tools](https://developer.android.com/tools/releases/platform-tools) (adb 1.0.32+)
- `prog_emmc_firehose_fujisan.mbn` and `twrp-3.2.3-0_fujisan.img` from the [XDA TWRP thread](https://xdaforums.com/t/recovery-3-2-3-0-fujisan-unofficial-twrp-recovery-for-axon-m.3959314/)

Those are third-party files and are not redistributed here.

## How to flash TWRP

1. Put `prog_emmc_firehose_fujisan.mbn`, `twrp-3.2.3-0_fujisan.img` and this repo's `config\rawprogram0.xml` in one folder with a short path and no spaces, such as `C:\Z999-TWRP`.
2. Double-click **`FlashTool.cmd`**.
   - **1 Check setup.** Fix anything marked `[FAIL]`.
   - **2 Fix QFIL config.** If QFIL is open, the script waits for you to close it.
3. Open QFIL and set it up:
   - Configuration > FireHose Configuration > Device Type: **eMMC**
   - Select Build Type: **Flat Build**
   - Programmer: `prog_emmc_firehose_fujisan.mbn`
   - Load XML: `rawprogram0.xml` (cancel the patch prompt)
4. Boot the phone into Android, turn on USB debugging, plug it straight into the PC and unlock it.
5. **3 Reboot phone to EDL.** Accept "Allow USB debugging?" if it appears (check both screens). The phone's screen goes black and the LED turns red.
6. In QFIL, check the port shows **Qualcomm HS-USB QDLoader 9008** and click **Download** right away.
7. When the log shows `Download Succeed` and `Finish Download`, hold **Power + Vol Up** until TWRP appears. Don't let it boot Android first, because stock firmware can put the stock recovery back.

If Download fails, hold Power ~15 s, boot Android and repeat from step 5.

## Menu options

| Option | Script | What it does |
|---|---|---|
| 1 | `scripts\Test-Setup.ps1` | Read-only checks: every adb on the PC and its version, QPST/QFIL, the QFIL config, USB connection and hubs |
| 2 | `scripts\Fix-QFILConfig.ps1` | Sets `RESETSAHARASTATEMACHINE` to False in `%APPDATA%\Qualcomm\QFIL\QFIL.config` (with a timestamped backup) |
| 3 | `scripts\Enter-EDL.ps1` | Waits for the phone in Android, handles `unauthorized`/`offline`, checks it's a fujisan, runs `adb reboot edl`, waits for the 9008 port |
| 4 | (menu) | Prints the QFIL steps |
| 5 | `scripts\Invoke-Sahara.ps1` | Diagnostic: uploads the programmer with the tool's own Sahara client and prints the phone's HELLO and every request |
| 6 | `scripts\Get-PartitionTable.ps1` | Diagnostic, read-only: dumps the GPT through `fh_loader`, prints it and checks `recovery` against `config\rawprogram0.xml` |
| 7 | `scripts\Fix-QFILConfig.ps1 -Revert` | Undoes option 2 |

Options 5 and 6 leave the phone in firehose mode. Reboot it into EDL again before using QFIL.

## Restoring a recovery that won't boot

EDL lives in the boot ROM, so a broken recovery (or system) doesn't stop you from reflashing:

1. Hold Power until the phone is completely off.
2. Hold **Vol Up + Vol Down** and plug the cable into the PC. If nothing happens after about 5 seconds, also hold **Power** for about 10 seconds. A black screen with a red LED means EDL.
3. In QFIL, click **Download** with the same setup as above. That writes TWRP 3.2.3 back to recovery.
4. Hold **Power + Vol Up** to boot into it.

On the AT&T test phone (stock Nougat), `TWRP-3.7.0_9-O-fujisan-20260809.img` from the LineageOS 23.2 thread left recovery unbootable. Restoring 3.2.3 this way fixed it.

## After flashing (tips from the XDA thread)

- If TWRP asks whether to keep /system read-only, **Keep Read Only** is the safe choice for stock Android.
- Don't flash Magisk on the stock boot image. It bootloops this phone.
- If Android shows a "device is corrupt" screen: `adb reboot "dm-verity enforcing"`.

## Credits

- **Unjustified Dev**: TWRP for fujisan and the working firehose programmer
- **deadman96385**: [Axon M stock firmware and firehose thread](https://xdaforums.com/t/rom-zte-axon-m-stock-firmware-firehose.3909847/) and the original QFIL guide
- XDA thread contributors (ZeroTheSavior, Drakosha, sybob, FF7CloudsNobody, Corekai and others) for the rawprogram typo, dm-verity and flashing tips

## License

MIT for the scripts and docs in this repository (see [LICENSE](LICENSE)). QPST/QFIL, Qualcomm drivers, firehose programmers and TWRP builds belong to their respective owners.
