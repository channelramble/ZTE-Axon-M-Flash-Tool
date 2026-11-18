# Flashing the Axon M from macOS (EDL)

This is a macOS-native walkthrough for installing the AT&T-patched LineageOS 23.2
images on a **ZTE Axon M, AT&T `Z999` / `P996A25` / `fujisan`** with a **locked**
bootloader, using the open-source [`bkerler/edl`](https://github.com/bkerler/edl)
client instead of QFIL. It also documents a **firehose write workaround** that
isn't covered elsewhere.

> Verified end-to-end on 2026-11-18 on a locked AT&T unit (stock 7.1.2 B21):
> flashed `test20-boot` + `test24-recovery` + `test25-system-gapps`, device
> boots LineageOS 23.2 / Android 16. **No bootloader unlock was needed** — this
> unit's locked bootloader boots self-signed images (shows the orange "device is
> corrupt" warning, press Power to continue).

## 0. Prerequisites (macOS)

```bash
brew install android-platform-tools        # adb, fastboot
# bkerler/edl in a venv (uv or pip):
git clone https://github.com/bkerler/edl && cd edl
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
```
You also need, from the release:
`…-test20-boot.img`, `…-test24-recovery.img`, a system image
(`…-test25-system-gapps.img.gz` or `…-vanilla.img.gz`), `SHA256SUMS`, and the
device-specific firehose loader `prog_emmc_firehose_fujisan.mbn`.
**Verify every file against `SHA256SUMS` before flashing.**

## 1. Entering EDL (9008) on macOS

- From Android/recovery: `adb reboot edl`
- Hardware (no adb): **hold Vol-Up + Vol-Down while plugging in USB**; screen
  stays black. (Long-pressing Power to "off" makes this unit auto-reboot
  immediately, so there's no clean "power off then key combo" window — use the
  plug-in-while-holding-volume method.)
- Confirm enumeration: macOS shows a USB device `QUSB__BULK`, vendor Qualcomm
  (`05c6`). `ioreg -p IOUSB -l | grep -i QUSB__BULK`

## 2. bkerler/edl quirks with this legacy loader (important)

- **One Sahara handshake per EDL entry.** A failed op (especially a large read)
  wedges the session into `Mode detected: error`; you must re-enter EDL. So make
  the first op after each `adb reboot edl` the one that matters.
- **`reset` rejects `--memory`** (prints usage). Use:
  `edl reset --resetmode=reset --loader=<loader>` (no `--memory`).
- **Multi-partition in one session:** `edl --loader=<loader> --memory=emmc qfil rawprogram.xml patch.xml <imagedir>`
- Writes are byte-exact from the file starting at the partition offset (safe);
  the loader over-reports *read* length using 4096-byte sectors — only affects
  reads.

## 3. The 7 GB system write: firehose collapses — use `dd` in recovery instead

**Problem:** writing the ~7 GB system image over firehose (`edl w system …` /
`qfil`) starts at ~36 MB/s but **collapses to ~0.25 MB/s after ~2.6 GB** (loader
USB flow-control once the eMMC write cache saturates — not the eMMC itself, not a
USB hub). The remaining ~4 GB would take hours.

**Workaround (reliable, ~30 MB/s steady, binary-clean):** flash the patched
recovery first, boot it, then stream the system image to the block device with
`dd` over adb — the Linux mmc driver sustains the write where the firehose loader
doesn't.

```bash
# 1) In EDL: flash patched boot + recovery (small, firehose is fine here)
edl --loader=LOADER --memory=emmc w boot     test20-boot.img
edl --loader=LOADER --memory=emmc w recovery test24-recovery.img
# set a BCB so the bootloader goes straight to recovery (see §4), then:
edl reset --resetmode=reset --loader=LOADER
# press Power at the orange "corrupt" menu -> boots Lineage recovery (adb shows 'recovery')

# 2) Find the system block device from recovery
adb shell 'ls -l /dev/block/by-name/system'   # -> mmcblk0p20 on this unit

# 3) Stream system.img via dd (segmented so you can watch the speed)
SRC=lineage-…-system.img ; DEV=/dev/block/mmcblk0p20 ; off=0 ; TOTAL=6656   # MB
while [ $off -lt $TOTAL ]; do
  cnt=1024 ; [ $((off+cnt)) -gt $TOTAL ] && cnt=$((TOTAL-off))
  dd if="$SRC" bs=1048576 skip=$off count=$cnt 2>/dev/null \
    | adb shell "dd of=$DEV bs=1048576 seek=$off 2>/dev/null"
  off=$((off+cnt))
done
adb shell sync

# 4) Verify ON-DEVICE (don't pull 7 GB back):
adb shell "dd if=$DEV bs=1048576 count=$TOTAL 2>/dev/null | sha256sum"
#   compare to uncompressed_sha256 in release-manifest.json
```

## 4. Factory reset + first boot

Write a standard AOSP BCB to `misc` (offset 0: `boot-recovery\0`; offset 64:
`recovery\n--wipe_data\n`) to trigger a native factory reset on the next
recovery boot — from recovery you can `dd` it straight to the misc partition:

```bash
adb shell "dd of=/dev/block/by-name/misc bs=8192 count=1 conv=sync" < misc_wipe_bcb.img
adb reboot
# Press Power at the corrupt menu -> recovery wipes data -> auto-reboots
# Press Power again at the corrupt menu -> LineageOS first boot (several minutes)
```

## Notes / caveats
- **Every boot stops at the orange "device is corrupt" menu and needs a Power
  press** ("Continue boot") — permanent for self-signed boot on this locked
  bootloader; powers off after 30 s if not pressed.
- No stock `system` backup is implied here — keep your own EDL backups of
  `boot`/`recovery`/`misc`/both GPT copies and the EFS/modem/persist partitions
  before you start.
- This is a debug build (permissive SELinux, root adb). Known-unstable HALs
  (camera `mm-qcamera-daemon`, AudioFX, ADSP) crash-loop and heat the device;
  not a daily driver.

Credits: AT&T patches & images by **channelramble**; base `fujisan` port by
**Anya1014CN / HanCF1014**; EDL client by **bkerler**.
