# AGENTS.md: Android 16 on the AT&T ZTE Axon M

Notes for AI coding agents (and people) continuing the effort to run the unofficial **LineageOS 23.2 (Android 16)** ROM and **TWRP 3.7.0** on an **AT&T ZTE Axon M (Z999, `fujisan`)**. It collects everything verified so far (October 2026), what was ruled out, the tooling that worked, and the next steps.

**Status: not finished.**
- The AT&T bootloader now accepts the 4.4-kernel images (fix 1 below).
- The 4.4 kernel runs on the phone and gets through early boot.
- Startup still stops during driver initialization, before userspace, so neither TWRP 3.7.0 nor LineageOS reach their UI yet.

The rest of this repository is the EDL/QFIL flash tool for TWRP 3.2.3; see [README.md](README.md) and [docs/FINDINGS.md](docs/FINDINGS.md).

---

## 1. Ground rules

1. **Modify, don't recreate.** Patch the published LineageOS 23.2 and TWRP 3.7.0 images: device tree, command line, re-signing, ramdisk tweaks. The one accepted exception is rebuilding the ROM developer's kernel from its published source, to debug and fix it.
2. **Never flash China/DoCoMo firmware on an AT&T unit.** That covers the bootloader chain and the ROM thread's "firmware zip".
   - XDA reports one AT&T Z999 hard-bricked after a CN update (stock firmware thread, post #62).
   - An AT&T user who sideloaded the ROM's firmware zip needed a full EDL restore to boot again.
   - The AT&T bootloader chain is signed with a different key from the China/DoCoMo one.
3. **Back up before writing, and verify every write by reading it back and comparing SHA-256.**
4. **Don't leave the misc "boot-recovery" flag set while recovery holds an image that doesn't boot.** That causes a boot loop that needs EDL to escape.
5. **Never commit or publish** signing keys, firehose programmers, firmware, ROM/TWRP binaries, or personal data from the phone (serial numbers, IMEI).
6. **The phone's owner does the physical steps:** EDL button combo, Power-key restarts, on-screen taps. Ask clearly, one step at a time, and wait.

## 2. Device facts (verified on one AT&T unit)

| Item | Value |
|---|---|
| Model | ZTE Axon M, AT&T Z999, codename `fujisan` |
| SoC | MSM8996 Pro ("8996 Pro v1.x"); DT match `qcom,msm-id` 0x131, `qcom,board-id` 0x66 |
| Storage | **eMMC** variant. Firehose programmer `prog_emmc_firehose_fujisan.mbn`; QFIL device type eMMC. Other Axon M units are UFS. |
| RAM | 4 GB LPDDR4 |
| Stock firmware | AT&T B37, Android 7.1.2, kernel 3.18.31. The AT&T model never got Oreo. |
| Bootloader | Unlocked. Every boot shows the orange "different operating system" notice, which continues on its own after 5 s. |
| Displays | Two **command-mode** DSI panels (JDI R63452 / Truly NT35695 / Truly TD4322 variants). LK splash framebuffer at `0x83401000`. Writing to the framebuffer doesn't show on screen without an MDP kickoff, so "draw a progress bar" debugging isn't trivial. |
| USB power-on behavior | After a PC-initiated (firehose) reset with USB attached, the bootloader starts the **boot** slot in charger mode (`androidboot.mode=charger`). Stock shows the charging animation there; hold Power ~5 s to start Android. |

Partitions (512-byte sectors; see also [docs/PARTITIONS.md](docs/PARTITIONS.md)):

| Partition | Start sector | Sectors |
|---|---|---|
| boot | 1050624 | 131072 (64 MiB) |
| recovery | 1181696 | 131072 (64 MiB) |
| system | 1312768 | n/a |
| misc | 18626584 | n/a (BCB: `boot-recovery` at offset 0, `recovery\n` at offset 64) |

## 3. Images involved

| Image | Kernel | Notes |
|---|---|---|
| `lineage-23.2-20261006-UNOFFICIAL-fujisan.zip` (boot.img, recovery.img) | 4.4.302-cip112-fujisan, clang 21, Oct 6 2026 | Built on the China Oreo base. The source says it relies on Oreo ADSP firmware (audio PCM ABI v3). |
| `TWRP-3.7.0_9-O-fujisan-20260809.img` | 4.4.302-fujisan+ #4, Aug 9 2026 | Needed to install Android 16 zips (`MADV_WIPEONFORK`; see docs/FINDINGS.md section 7). |
| TWRP 3.2.3-0 for fujisan (XDA) | 3.18.71 | Boots fine on AT&T B37. Used as the log reader (section 6). |

- All are boot image header **v0**: `Image.gz` with appended DTBs, two of them, (0x131,0x10001) and (0xf6,0x30001) with board-id 0x66, plus an AOSP `BootSignature` trailer.
- The ROM's boot/recovery DTB and TWRP 3.7.0's DTB are **byte-identical**.
- Re-signing with a self-made key is fine on this unlocked bootloader; it only shows the orange notice. Sign `/boot` images for the boot slot and `/recovery` images for the recovery slot.

## 4. Fixes found (apply to every 4.4 image)

### Fix 1: free space inside each DTB (required)

Unmodified 4.4 images were rejected about 6 s after power-on and the phone fell into EDL. Cause: before it adds its own data, the AT&T bootloader grows the DTB in place by only **about 1 KiB**. That data is its full command line appended to `/chosen/bootargs`, plus memory and initrd properties. The 4.4 DTBs plus the bootloader's long command line overflow that, the device-tree update fails, and boot is aborted.

**Fix:** re-serialize each appended DTB with **8 KiB of free space** (`totalsize` grown, padding after the strings block), then rebuild and re-sign the image. With this, the bootloader starts the 4.4 kernel.

### Fix 2: reserve `0x9FF00000` (1 MiB, no-map)

The stock AT&T DT (`ap_share_region`) and TWRP 3.2.3 (`vlog_mem_region`) both reserve 1 MiB at `0x9FF00000`; the 4.4 DTs don't. Add a `no-map` reserved-memory node for it. This alone didn't fix boot, but keep it.

### Fix 3 (pending, ROM only): GPU zap shader firmware

The ROM's `/system/vendor/firmware/a530_zap.{mdt,b0x,elf}` are signed for another root. Swap in the AT&T copies from B37 `/system/etc/firmware`; the code segment `b02` is identical.

## 5. Ruled out as the cause of the 4.4 boot failure

- Boot image `os_version`, EFI/MZ header, arm64 Image flags (0xa), compressed kernel size, command-line length, DTB size (up to ~410 KB), `linux,phandle`.
- DTB matching (msm-id/board-id), missing nodes the bootloader looks up.
- Kernel memory footprint (`image_size` ≈ 30–31.5 MB). It fits below where the bootloader places the DTB and ramdisk, with ≥1.5 MB to spare.
- Storage: the 4.4 DT enables both UFS and eMMC (`sdhci@7464900`); the ROM's fstab uses the eMMC path. On the stock 3.18 kernel, the UFS probe fails harmlessly with -ENODEV.
- **Device tree content.** A full stock-B37 vs 4.4 DT comparison found no early-boot-critical difference: reserved memory, `/memory`, CPUs/PSCI, GIC, timers, clock controllers, RPM/SMD/GLINK, SPMI arbiter values, IMEM. Only 4.4-specific additions differ: reset controllers, MPM wake maps, `linux,cma`, coresight nodes.
- Kernel stall detectors: with `CONFIG_DETECT_HUNG_TASK` and `CONFIG_LOCKUP_DETECTOR` enabled with panic, nothing fired. The stop is a hard stop, not a slow or blocked task.

## 6. Debug infrastructure that works

### 6.1 Kernel build (for debugging; the one allowed rebuild)

- Source: `github.com/Anya1014CN/android_kernel_zte_msm8996`, branch `lineage-23.2-rebase`. Device tree repo: `github.com/Anya1014CN/android_device_zte_fujisan`, branch `lineage-23.2`.
- Built in WSL Ubuntu with clang-21 / ld.lld-21 / llvm-*-21, `CROSS_COMPILE=aarch64-linux-gnu-`, `CROSS_COMPILE_ARM32=arm-linux-gnueabi-`, `lineageos_fujisan_defconfig`, target `Image.gz-dtb`. A full build takes about 15 min; an incremental one about 40 s.
- To test a rebuilt kernel, replace only the gzip kernel inside the shipped TWRP 3.7.0 image (keep its DTBs and ramdisk), then apply fixes 1 and 2 and re-sign.

### 6.2 Debug patches (kept on a local branch; small, self-contained)

1. **Early RAM console (`arch/arm64/kernel/epstore.c`).**
   - It registers a console in `setup_arch()` right after `early_ioremap_init()`. The console writes every printk straight into RAM in `persistent_ram` (pstore "DBGC") format: header of sig, start, size.
   - It appends to an existing valid ring.
   - It uses an early mapping of 256 KiB and remaps the full zone at `early_initcall`.
2. **MMU-off progress marks in `head.S`.** A macro appends characters (`\n[fj]ABCDE`) to the same ring at kernel entry and at each early stage. It clobbers only x9–x11.
3. **Boot checkpoints in `init/main.c`.**
   - `fj_reboot_at=<name>` stops the kernel at a named point: `setup_arch`, `mm`, `time`, `start_kernel`, `early`, `smp`, `sched`, `level0`…`level7` (after each initcall level), `userspace`.
   - `fj_reboot_at=@<initcall symbol>` stops right before that initcall.
   - The checkpoint now **halts** (prints `[fj] checkpoint X reached - halting`) instead of rebooting; see section 7.3 for why.
4. Command line used for debug images: `ignore_loglevel initcall_debug fj_reboot_at=<checkpoint>`. Disable the 4.4 DT's `/soc/ramoops` node in these images so it doesn't fight the early console.

### 6.3 Reading the log: TWRP 3.2.3 as a pstore reader

- **RAM survives a 10–15 s Power-key restart, but not the EDL button combo.** So after a frozen 4.4 boot, a Power restart into TWRP 3.2.3 shows the frozen kernel's log in `/sys/fs/pstore/console-ramoops`.
- **Use the reader's real ramoops layout**, read from `/sys/module/ramoops/parameters/` and not from the DT:

  | Parameter | Value |
  |---|---|
  | Region | `0xbfc00000`, size `0x140000` |
  | dmesg records | 24 × `0x8000`, starting at `0xbfc00000` |
  | console zone | **`0xbfcc0000`, size `0x80000`** |
  | ftrace | none |
  | ECC | none |

  - The early console and the head.S marks must write to `0xbfcc0000`.
  - An earlier attempt wrote to `0xbfc40000`, which is a dmesg slot. The reader discarded it, so for a long time no 4.4 output was ever seen. That was the biggest time sink.
- **Two reader ramdisk patches**, appended to `init.rc`:
  ```
  on charger
      trigger late-init            # charger-mode boots (after a PC reset) still start TWRP
  on property:sys.usb.config=mtp,adb
      setprop sys.usb.config adb   # MTP makes adb "offline" with TWRP 3.2.3 on adb 29
  ```
- Only trust **lines after the `[fj]ABCDE` entry mark** when reading a capture. The ring also holds earlier boots' output. A quick reboot back into the reader doesn't prove a checkpoint was reached; the log line `[fj] checkpoint X` does.
- adb: use adb 29.0.6 for TWRP 3.2.3. Newer platform-tools (37) shows it as `offline`.
- Writing partitions from a running TWRP works well and avoids EDL: `adb push` the image, `dd` it to `/dev/block/bootdevice/by-name/<part>`, then `head -c <len> … | sha256sum` to verify.

## 7. Results so far

### 7.1 The 4.4 kernel runs and gets through early boot

One clean capture with the halting/rebooting checkpoint at `level5` shows the following:
- head.S marks `[fj]ABCDE`, then normal 4.4 boot output.
- The reserved-memory map is as expected, including the added `ap_share_region`.
- All checkpoints `setup_arch` → `smp` → `sched` → `level0` … `level5` are passed, reaching `level5` (after fs initcalls) at **~1.39 s**.
- Notable lines are only normal probe deferrals: `cpu-clock-8996 … resources init failed` (retried), `msm-bus-type … -517`, `MPM 1 irq mapping errored -517`.

### 7.2 Where it stops: not pinpointed yet

The stop is **after `level5`**: device initcalls (`level6`), late initcalls (`level7`), or the very start of userspace. TWRP's UI and adb never appear. Every "full boot" capture attempted afterwards was lost to the issues in 7.3 and 7.4.

### 7.3 The 4.4 restart path freezes on AT&T firmware

- Once the 4.4 reboot driver is active (by `level5`), a restart prints `Going down for restart now` and `qpnp-power-on … PMIC@SID2: configuring PON for reset`, then freezes.
- Restarts earlier in boot, before that driver takes over, worked.
- **After such a frozen restart, later 4.4 boots failed to start the kernel at all until the phone was fully powered off** (`adb shell reboot -p` from TWRP, then power on).
- The ROM will need this restart path fixed. For debugging, checkpoints therefore halt instead of rebooting.

### 7.4 Starting debug images from the recovery slot is unreliable

- With debug images in **recovery** and the reader in **boot**, `adb reboot recovery` often came straight back to the reader without the 4.4 kernel ever starting: no `[fj]ABCDE` mark at all.
- Images whose checkpoint argument was `fj_reboot_at=init` never started in four tries. `level5` images did start, in a clean state. The reason is unknown, so avoid that value; it was renamed to `userspace`.
- The bootloader menu's "Recovery mode" entry and the Vol Up + Power combo both returned to the menu instead of booting recovery.
- **Boot-slot boots were reliable.** Put the debug kernel in **boot** for the next round.

## 8. Recommended next steps

1. **Pinpoint the stopping driver with a visible result**, so you don't depend on RAM logs.
   - Put the TWRP 3.7.0 image (fixes 1+2, its own kernel or a rebuilt one) in the **boot** slot. Add the standard kernel parameter `initcall_blacklist=<fn1>,<fn2>,…`, covering half of the `level6`/`level7` initcalls. Get the ordered list from the `.initcall6.init` / `.initcall7.init` sections of `vmlinux`, or from `System.map`.
   - If TWRP's UI or adb appears, the culprit is in the blacklisted half. Bisect down to one initcall, then fix or disable that driver for AT&T firmware.
   - Expect dependencies: blacklisting clock/regulator/bus drivers cascades. Bisect inside groups that don't include core infrastructure first.
   - Each round needs one EDL write, or an adb write from a booted TWRP.
2. Alternatively, retry the halting `userspace` checkpoint from the **boot** slot after a **full power-off**, with the reader in recovery. A Power-key restart then needs a working way into recovery (section 7.4), or the EDL combo, which loses RAM.
3. Fix the 4.4 restart path for AT&T firmware (7.3).
4. Once TWRP 3.7.0 boots:
   - build the ROM's `boot.img` with fixes 1 and 2 (same kernel fix);
   - swap the GPU zap firmware (fix 3);
   - format `/data` as f2fs (the ROM uses unencrypted f2fs);
   - install.
5. Expected gaps even after boot:
   - ADSP audio (the ROM expects Oreo ADSP firmware; ABI v3);
   - VoLTE (known issue upstream);
   - possibly modem/RIL, because AT&T Nougat firmware stays in place.

## 9. Community context (XDA, read October 2026)

- ROM thread: `xdaforums.com/t/rom-unofficial-16-lineageos-23-2-for-zte-axon-m-2026-10-06.4798874/`.
- Developer HanCF1014 (Anya1014CN). His own phone is a DoCoMo Z-01K. He says the "ATT variant is different from other variant" and asks US users to reach him on Telegram (`t.me/AxonMUpdates`, `t.me/AxonMOfficial`).
- **No one has reported the ROM or TWRP 3.7.0 fully running on an AT&T unit.**
  - One AT&T B37 eMMC user reached a ZTE-logo hang. Later attempts "got past the logo but never fully booted".
  - Another US eMMC user reported the LineageOS recovery booting but posted no details.
- US eMMC root guide (Magisk v26 only; pad patched boot to the original size): `xdaforums.com/t/guide-zte-axon-m-us-z999-att-emmc-root.4803967/`.
- Stock firmware and firehose thread: `xdaforums.com/t/rom-zte-axon-m-stock-firmware-firehose.3909847/`. Its firehose is a UFS programmer; eMMC units need the eMMC one.

## 10. Tool inventory used for this work (not yet in this repo)

| Tool | Purpose |
|---|---|
| `dtb_variant.py` | Parse and re-serialize appended DTBs. Free space (`--dtb-free`), `0x9FF00000` reservation, `--disable` nodes, `--cmdline` / `--cmdline-drop`, `--set` props, `--kernel` (replace Image.gz), `--ramdisk`, then rebuild the v0 image and re-sign `BootSignature`. |
| `rd_tool.py` | grep/cat/append files in a gzip newc ramdisk. |
| `bootinfo.py`, `dtb_extract.py`, `dtb_compare.py`, `kfootprint.py` | Inspect boot images, DTBs, memory maps, kernel `image_size`. |
| `klog.py` | Extract only the 4.4 kernel's lines (after `[fj]ABCDE`) from a pstore capture; list checkpoints and initcalls that never returned. |
| `sahara.ps1`, `fh_direct.ps1` | Sahara programmer upload (handles a missed HELLO) and raw firehose XML. |
| `run_chain.ps1`, `run_trap.ps1`, `run_ckpt.ps1`, `run_bootslot.ps1` | Automated test loops: EDL write plus verify, reset, wait for the reader, pull pstore. Also an adb-only loop from a running reader. |

## 11. Quirks worth knowing

- **Sahara.** An EDL session goes stale once its HELLO is missed. Wait for a fresh 9008 arrival, or send an unsolicited HELLO_RESP (mode 0).
- **`fh_loader`.**
  - `<read>` reuses an existing output file's size, so delete readback files before reading.
  - It fails with very long working paths.
  - A firehose `<power value="reset">` sometimes lands straight back in EDL. Confirm the 9008 port actually disappeared before trusting a result.
- **Production firehose.** The programmer refuses `<peek>`, so there are no RAM reads over EDL.
- **TWRP 3.2.3 can't install Android 16 zips** (`MADV_WIPEONFORK`); see docs/FINDINGS.md section 7.
