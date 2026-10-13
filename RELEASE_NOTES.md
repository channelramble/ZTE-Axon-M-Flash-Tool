# ZTE AXON M FLASH TOOL v1.0.0

First release. Helper scripts and a corrected config for flashing the ZTE Axon M (Z999 / fujisan) with QFIL.

## Fixes

- **QFIL `SAHARA_NAK_INVALID_CMD` / "Sahara protocol error"**: one-click fix that turns off QFIL's `RESETSAHARASTATEMACHINE` setting, which makes QFIL send a Sahara reset command the Axon M rejects.
- **Corrected TWRP `rawprogram0.xml`**: recovery at sector 1181696 instead of the wrong 210048, checked against the phone's partition table.
- **adb `offline`**: finds and uses the newest adb on the PC and warns about old copies on PATH.
- **Docs**: why the LineageOS 23 zip fails in TWRP 3.2.3 (`MADV_WIPEONFORK`), and how to restore a recovery that won't boot through EDL.

## Included

- `FlashTool.cmd` menu: setup check, QFIL config fix (and undo), reboot to EDL, QFIL steps
- Diagnostics: standalone Sahara programmer loader with packet logging, read-only partition table reader
- Docs: findings with evidence, Axon M (AT&T) partition table

## Not included

QPST/QFIL, Qualcomm drivers, adb, the firehose programmer and the TWRP image. See the README for where to get them.

## Tested

AT&T Axon M, QFIL 2.0.1.9, Windows 10. The QFIL config fix, setup check and GPT parser were tested directly. The EDL-entry and Sahara scripts are the same code used during the original fix; their packaged versions have not been rerun on a phone.
