# AGENTS.md: Android 16 on the AT&T ZTE Axon M

Notes for AI coding agents (and people) continuing the effort to run the unofficial **LineageOS 23.2 (Android 16)** ROM and **TWRP 3.7.0** on an **AT&T ZTE Axon M (Z999, `fujisan`)**. It collects everything verified so far (October 2026), what was ruled out, the tooling that worked, and the next steps.

**Status: Test23 boots full Android; hardware validation remains unfinished.**
- **Latest investigation:** fresh slot hashes prove boot/recovery are not
  swapped. Previous-boot pstore records an incoming BCB recovery request;
  diagnostic CLI arguments suppressed the Settings factory-reset arguments.
  Test24 restores native recovery argument handling and cache/data access;
  it is flashed with full readback verified; native recovery boot and the
  owner-requested factory reset are now verified (section56).
  Menu/PMIC routing remains separate.
  GApps is installed and fully verified after the owner-approved reset.
  Owner confirms LineageOS and recovery both boot (sections56–57).
  Direct Volume Up entry still needs investigation.
  See sections54–55 before any write or reset.
- **Working recovery controls (October16): Test18 TWRP3.7 and Test19 LOS23.2**
  boot with adb on their own4.4 kernels. Test06 TWRP3.2.3/3.18 is the older
  fallback. See sections38 and42 for verified live captures.
- The AT&T bootloader now accepts the 4.4-kernel images (fix 1 below).
- The 4.4 kernel runs on the phone and gets through early boot.
- **Current installed system: Test23 plus Test25 GApps (October16).**
  Test20 Android boot remains intact; Test24 recovery is now installed and boots. The owner-approved native
  factory reset completed before GApps installation (section56). Test22 persists the Gatekeeper diagnostic and GPU-memory-stat
  fallback for the two recorded system_server failures. Android reaches the
  end of its animation in Test22 but blocked on the disabled USB port HAL.
  Test23 restores the published USB port-service init RC. **Owner now confirms
  full Android boot; ADB is back and sys.boot_completed=1.** Seven samples over
  185.767seconds confirm the same system_server PID/starttime and healthy USB.
  User0 is unlocked and the launcher is resumed. Owner also confirms both
  screens work perfectly: single folded, spanning both unfolded. Extra stock
  ZTE modes are a feature gap in this port, not the reported display failure.
  See section52.
  **Actual recovery-slot boot is verified** using an
  explicit menu-only BCB request, bypassing the unreliable menu/PMIC route.
  Native recovery cleared BCB back to its exact baseline.
  See sections50–51; earlier status notes are historical.

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
5. **Publication authorization updated October17:** the owner explicitly instructed publishing the patched TWRP and LOS binaries to GitHub, overriding the earlier binary-publication restriction. Publish the verified image artifacts as release assets with checksums and accurate target/experimental-status notes. Continue excluding private signing/SSH keys, Firehose programmers, unrelated firmware/bootloader dumps, userdata, raw personal logs, serial numbers and IMEI. Historical statements excluding ROM/TWRP binaries below describe the earlier policy, not this current authorization.
6. **The phone's owner does the physical steps:** EDL button combo, Power-key restarts, on-screen taps. **Updated owner preference (October 16):** the owner handles EDL reentry between rounds; detect it and proceed with prepared, validated tests without repeatedly requesting EDL entry or asking whether reentry was manual. Keep testing moving. Ask only for essential new observations or nonroutine physical steps; never infer an unreported screen result from USB mode alone.
7. **TWRP tests must boot with MTP disabled and adb enabled.** The owner
   explicitly requested this to reduce reconnect delays. Verify both the
   ramdisk defaults and USB activation actions; an after-the-fact `mtp,adb`
   redirect alone can still briefly enumerate MTP. Preserve historical test
   binaries and create newly named adb-only candidates.

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
- LOS recovery's DTBs match published TWRP 3.7.0's DTBs as a set, in reversed
  order. **LOS boot has different DTBs**, including display/sleep/thermal
  changes. Preserve each published image's own DTBs and apply semantic fixes;
  do not replace the LOS boot DT tail with TWRP's.
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
- Kernel stall detectors did not produce a captured report in the older debug
  build. This does not rule out a blocked task or workqueue in the current
  published-kernel tests; sections 25–33 investigate that possibility.

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

  **These addresses describe the older modified reader.** The fresh published
  reader used in test 06 has a different measured layout: 1 MiB at `0xbfc00000`,
  console at **`0xbfc40000`** (512 KiB), pmsg at `0xbfcc0000` (256 KiB), eight
  32 KiB dmesg slots, no ftrace/ECC. Match the actual reader when preparing
  another logging image; do not reuse the old console address blindly.

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

**Historical plan; superseded by sections 31–33.** The 3.18 control works
(section 19), but the marked recovery reader/RAM-retention route was not
established. Current priority is Test 16's persistent runtime log retrieval.
The older blacklist strategy below records the original debugging plan.

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

## 12. Local preparation resumed on macOS (October 15, 2026)

See [docs/LOCAL_PREPARATION.md](docs/LOCAL_PREPARATION.md) for the restored offline
workflow. `scripts/fujisan_image.py` inspects and patches the published v0 images
and signs them with a private local key. `scripts/check_backups.py` validates
saved primary GPT and partition backups; `scripts/initcall_order.py` reads the
exact debug build's System.map. The old scripts in section 10 are still not
recovered; these are new, narrower replacements.

- Recovered the original eMMC programmer/TWRP 3.2.3 ZIP and the developer's
  exact TWRP 3.7.0 and October 6 LineageOS releases. The published 3.7.0 image
  uses a legacy Qualcomm SHA-1 boot ID that also hashes a zero DT-size word;
  preserve that convention when rebuilding it.
- Prepared separately signed boot/recovery reader images, TWRP 3.7.0 images
  with fixes 1+2, and Lineage boot/recovery images with fixes 1+2. Kernel machine
  code is unchanged. No blacklist or early-console patches have been added.
  All are **locally validated candidates, not hardware-tested fixes**.
- Artifacts, signing material, hashes, and session state stay in the private
  `.axon-m-private` sibling directory, outside Git. No phone writes were made
  during preparation. The previous System.map/vmlinux/debug patches remain
  missing. The ROM ZIP is not an AT&T-ready installer.
- The phone is connected to the MacBook.
  EDL is installed there under `~/.local/share/axon-m-edl`, pinned to bkerler/edl
  `1cda1a616748d608667b2d13b73a28d3197ceb45`. Its `gpt` handler has file writes
  commented out despite success messages. Further hardware findings below
  supersede the initial recommendation to use its `rs` command.

## 13. MacBook EDL session and recovered symbols (October 15 evening)

- Fresh EDL after a Power-key restart accepted the original eMMC programmer.
  Replugging the cable and a host USB reset did **not** repair a stale session.
- The upstream EDL reconnect probe reads only 48 bytes and overflows on the
  running programmer's XML. The programmer also rejects endpoint `clear_halt`.
  Use the private `sahara_load.py` and bounded `firehose_read.py` scripts in
  `.axon-m-private`; copies are in the remote session directory recorded in
  `session.json`. The reader accepts an initial NOP NAK, configures eMMC with
  `SkipWrite=1`, then requires both raw-mode and completion ACKs for every read.
- Complete boot, recovery, misc, and both GPT backups are verified on both Macs.
  All GPT header/array CRCs pass and the partition arrays agree. The actual
  boot/recovery offsets match section 2. Misc is entirely zero.
- At backup time, both active images were the old 3.18.71 TWRP reader, with charger/USB patches
  and valid signatures for their respective slots. The previous 4.4 debug
  kernel is not installed. Nonzero bytes **after** each signed image are stale
  partition contents; keep the full backups and trim only inspection copies.
- Recovered 119,746 symbols from the published TWRP 3.7.0 kernel with
  `marin-m/vmlinux-to-elf` commit `2d094bc9c220b6b50f8215cbc3c9e581210ce1a6`.
  All **614 level-6 and 76 level-7** initcall pointers were checked against the
  raw kernel and resolved to their expected function symbols. Files are in
  `.axon-m-private/kernel-analysis`. This map belongs to the published 3.7.0
  kernel, **not** the missing previous debug build or the October Lineage kernel.
- The published 3.7.0 ramdisk has no `on charger` action. A new candidate,
  `prepared/twrp-3.7.0-att-charger-boot.img`, adds only that ramdisk action, the
  two DT fixes, and ordinary initcall logging. Its kernel code is unchanged.
  This baseline has no blacklist; section 14 records the subsequent diagnostic
  candidate. The baseline remains untested; test 01's result is recorded below.
- Google adb 29.0.6 is installed separately at
  `~/.local/share/axon-m-edl/platform-tools-29.0.6/adb` on the MacBook. Intel
  execution works. A separate adb server uses port **5038**.
- No phone partitions were written during the backup phase. A Firehose
  power reset disconnected USB before its final ACK; 9008 disappeared, but
  the existing reader did not appear over USB during the following checks.
  The owner now reports a **Start menu saying "your device is corrupt"**, with
  Recovery, fastboot, and Power off choices. Fastboot appears to do nothing.
  The owner confirmed Recovery returns to Start, exactly as section 7.4 already
  recorded. **Do not repeat that menu test or make recovery-menu success a
  prerequisite for the documented EDL/boot-slot investigation.**

## 14. First boot-slot blacklist test: logo hang (October 15–16)

- Follow section 8's visible-result approach. The first diagnostic group skips
  six verified level-6 initcalls related to peripheral firmware loading:
  `adsp_loader_init,pil_tz_init,pil_mss_init,msm_pil_init,msm_vidc_init,sensors_ssc_init`.
  This is a hypothesis test, not an identified faulty driver or a final fix.
- Private candidate: `prepared/test-01-remoteproc-boot.img`, SHA-256
  `81860b6b9360724a5d3e294c7ec257c5c4fdabd21bc8003c56ce327b99ea3bab`.
  It preserves the published 3.7.0 kernel code and adds the two DT fixes,
  charger-mode `late-init`, `ignore_loglevel initcall_debug`, and the blacklist.
  The complete command line is **463 bytes**, fitting in the first boot-header
  field; no reliance on this bootloader's unverified `extra_cmdline` handling.
- The image and `test01-remote-plan.json` are staged in the MacBook session.
  Both Macs pass the private `firehose_boot_test.py` file-only preflight. Its
  nine offline transfer/transaction tests pass, including changed GPT/misc,
  short transfers, NAKs, and readback mismatch. It requires fresh matching GPT
  and misc reads, permits only boot writes, and compares SHA-256 of the exact
  image and sector-padded data after programming. It sends **no reset**.
- `firehose_boot_test.py PLAN` is file validation only. `--execute` performs
  the boot write and mandatory readback when the correct programmer is already
  loaded. Keep private transaction logs and inspect `readback_verified` before
  a separate restart. No bootloader-chain, recovery, or misc write is planned.
- The owner confirmed full power-off. The next MacBook check already found a
  fresh Sahara HELLO; the verified programmer loaded successfully.
- **Test 01 was written to boot.** Fresh GPT and misc reads matched the
  backups. The 26,178,611-byte image (51,131 padded sectors) received a program
  ACK and an exact SHA-256 readback match. The readback copy on this Mac also
  matches. Recovery and misc were not written. Private evidence is in the
  remote `test01-remoteproc` directory and local
  `.axon-m-private/hardware-tests/test01-remoteproc`.
- Firehose transfer quirk: after configuring 64 KiB payloads, requesting 1 MiB
  again returns NAK advertising a 65,536-byte maximum. The private reader now
  requests **65,536 bytes** consistently. This initially delayed reset; it did
  not invalidate or repeat the successful image write.
- A separate power reset was sent after verified readback. USB disconnected
  before ACK as previously observed. No USB device or adb appeared over the
  following ~45 seconds; that poll was **before** the owner selected Start.
- The owner subsequently selected **Start**, saw the ZTE logo, and reported a
  hang. **Test 01 did not reach a visible TWRP boot.** There is no current kernel
  trace proving kernel entry or blacklist consumption; do not treat this as
  proof that the six skipped drivers are innocent. A later MacBook USB check
  found `05c6:9008` and no adb. The owner subsequently confirmed **manual EDL
  entry**; this is not evidence of an automatic crash into EDL.
- Independent inspection of the exact published kernel confirms that all six
  names match unique symbols and raw initcall pointers. Its blacklist code
  compares the `%pf` function name and returns `-EPERM` on a match.
- The built-in `ramoops_fujisan_snapshot_init` is a level-7 initcall. Its
  9,000-jiffy deferred work runs after **90 seconds** (`CONFIG_HZ=100`) and only
  calls `kmsg_dump(1)` into RAM. It neither persists logs to eMMC nor helps a
  level-6 hard stop; EDL still loses that RAM.

## 15. Second boot-slot diagnostic written; boot result pending (October 16)

- Keep test 01's six skips and add `kgsl_3d_init,tz_log_init`.
  These driver probes make initialization-time TrustZone calls. Both
  names and pointers were checked against the exact published kernel. Keep
  `kgsl_core_init`, MDSS, USB, eMMC, clocks, regulators, and buses enabled.
- Private candidate: `prepared/test-02-gpu-tzlog-boot.img`, SHA-256
  `4ebf12a656a2c3d38c7e172b6ae5b918c2625cd4be727a75106b00531d74641e`.
  Its complete command line is **488 bytes**. Kernel code, ramdisk, and both
  fixed DTBs are unchanged from the charger-mode baseline. It is a diagnostic
  candidate, not a final recovery: GPU acceleration and TZ logging would be absent.
- **Rejected before flashing:** the initial nine-skip candidate also disabled
  `qseecom_init`. Exact binary review confirmed that `qseecom_start_app` wakes
  queues before its readiness check, while the probe initializes those queues.
  Skipping that initializer could therefore introduce a separate crash. The
  private `test-02-trustzone-boot.img` and `test02-remote-plan.json` are obsolete;
  use `test02-gpu-tzlog-remote-plan.json` instead. QSEE remains enabled.
- This cumulative test avoids reintroducing a possible first blocker while
  testing the next group. A further hang is inconclusive because dependent
  drivers or multiple blockers can hide progress. A successful boot needs
  `/proc/cmdline`, logs, and driver-presence checks before narrowing the group.
- **Test 02 was written to boot and readback-verified on both Macs.** Fresh GPT
  and misc reads matched the backups; programming and readback both ACKed.
  The padded 26,179,072-byte readback has SHA-256
  `a7d7fbd5d028b4d7a957214c717f3d1c0a3eeefdac22af8b5daf18649bae157d`.
  Recovery still holds the backed-up 3.18.71 reader; misc is unchanged zero.
  Private evidence is in `hardware-tests/test02-gpu-tzlog` locally and
  `test02-gpu-tzlog` in the MacBook session. Check `session.json` for reset and
  pending physical steps before touching the phone.
- A separate Firehose reset was sent after verified readback. USB disconnected
  before ACK, and EDL remained absent in five samples over 12 seconds.
  The requested full power-off/Start attempt was not confirmed. The owner then
  reported manual EDL entry and requested a new image. A fresh complete readback
  still matched test 02. **Its boot result remains unconfirmed**, not failed;
  subsequent diagnostics cannot be described as a successful bisection of it.

## 16. Third diagnostic: QSEE failed-probe path (October 16)

- Private candidate: `prepared/test-03-qsee-probe-boot.img`, SHA-256
  `649981ce66684f9c34d45432ac840cf70d9dcfbb8868387bc43bb09f85328574`.
  Keep test 02's eight-entry blacklist, corrected DTBs, and charger ramdisk.
  The command line remains 488 bytes. The image is signed for `/boot`.
- This diagnostic changes exactly **one four-byte instruction** in the
  published kernel: raw Image offset `0x636a6c`, `91efff97` (BL to
  `qseecom_scm_call`) becomes `40028012` (MOVN W0,#18, returning `-ENODEV`).
  This is the first SCM query in `qseecom_probe`, after list/waitqueue setup.
  Two independent disassembly reviews checked the target, instruction,
  preserved mutex unlock, existing cleanup path, and stack/link-register use.
- Unlike blacklisting `qseecom_init`, this preserves initialized queues and
  leaves QSEE in NOT_READY state. It bypasses subsequent QSEE probe work and
  removes its character device through normal error cleanup. It is a temporary
  diagnostic, **not a production QSEE fix**. The existing error path prints an
  uninitialized response value; do not interpret that logged QSEE version.
- Guarded private builder: `prepare_test03_qsee_probe.py`. It requires the
  exact source-image hash, raw-kernel hash, and original instruction, decodes
  the original branch target, and checks that only those four raw bytes differ.
  Patched raw-kernel SHA-256:
  `1aac4cf131ffd28f2b7c1f9049ebf2fa8cf1fa1a7905de037b92bd1c3a06946a`.
  Ramdisk, appended DTBs, and command line are byte-identical to test 02;
  gzip, boot ID, and BootSignature were rebuilt and validated.
- A positive boot implicates the QSEE probe path or work it enables; it does
  not isolate the first SCM query. A negative result remains inconclusive.
  Test 02's missing screen result must remain explicit when comparing tests.
- MacBook file preflight passed using `test03-qsee-probe-remote-plan.json`.
- **Test 03 was written to boot and readback-verified on both Macs.** Fresh
  GPT and misc match the backups; program and readback both ACKed. The padded
  readback SHA-256 is
  `6fac8c92469307e38a9a965477f017b36986fcb14b936b627dee34db8746a784`.
  Recovery remains the 3.18.71 reader and misc remains zero. Private evidence:
  `hardware-tests/test03-qsee-probe` locally; `test03-qsee-probe` remotely.
  Check private `session.json` for current reset/physical-step state.
- A separate Firehose reset disconnected USB before ACK. EDL was absent in
  five samples over 12 seconds, but a later USB/adb check found `QUSB__BULK`
  again and no adb. The owner confirmed **manual reentry** and asked to stop
  repeatedly requesting EDL entry/confirmation so testing can move faster.
  A subsequent 45-second monitor saw neither EDL nor adb; no new image had
  been written at that point. The owner later explicitly reported **test 03
  results in the ZTE screen**. No TWRP was reported. Record that against test
  03, not the already-installed test 04; there is still no current kernel trace
  proving where this test stopped.

## 17. Fourth diagnostic: ZTE screen/red LED, no positive marker (October 16)

- Private candidate: `prepared/test-04-blue-led-boot.img`, SHA-256
  `6a80d22902a4545eb90a9ee610ba7252dde4d50ee1929679497666ded2425739`.
  This preserves test 03's kernel gzip (including its QSEE probe patch),
  ramdisk, and 488-byte command line. The only semantic change in both DTBs is
  `/soc/qcom,spmi@400f000/qcom,pmi8994@3/qcom,leds@d000/qcom,rgb_2`:
  `qcom,default-state` changes from `off` to `on`. Each DTB retains 8 KiB slack,
  its AT&T reservation, and its own PWM phandle. Boot ID/signature validate.
- Exact driver inspection confirms the default-on path synchronously applies
  the LED state during probe, without relying on a queued worker or an absent
  generic LED trigger. Blue is the final RGB child. Current limit/PWM settings
  are unchanged. Private reproducible builder: `prepare_test04_led.py`.
- A **new blue or purple transition after Start**, even briefly, supports
  reaching the QPNP RGB probe: level-6 initcall **376 of 614**. An absent change
  remains inconclusive (earlier stop, probe/PWM failure, hardware variation).
  Existing blue after a later warm reset is not fresh evidence: PMIC LED state
  can persist. Later userspace may also overwrite the marker.
- **Test 04 was written to boot and readback-verified on both Macs.** EDL
  appeared during an automatic wait; the verified programmer loaded without
  another owner prompt. The plan is `test04-blue-led-remote-plan.json`. Fresh
  GPT/misc matched the backups; program and readback ACKed. Padded readback
  SHA-256: `f8f6c7559cb6188976261189d426858f85ee2634153cca0f4c0d7a72eec6980b`.
  Recovery/misc remain unchanged. Evidence is in private
  `hardware-tests/test04-blue-led` locally and `test04-blue-led` remotely.
- A separate verified-session reset disconnected USB before ACK. EDL was
  absent in five samples over 12 seconds; adb was absent at the end of that
  check. The owner handles physical testing and
  EDL reentry. Detect it automatically, without repeating entry questions;
  consult `session.json` for live state before the next operation.
- After the owner's delayed test 03 screen report, another MacBook snapshot
  still found neither EDL nor adb. The owner subsequently explicitly reported
  **test 04: red LED on the ZTE screen when plugged in**. This is not a positive
  blue-marker result. It does not prove lack of kernel entry, rule out a brief
  unreported transition, or establish that this blue channel works on the
  physical unit. No LP5562 device appeared in either published 4.4 or old-reader
  DT; that supports QPNP as the candidate controller, without proving wiring.
- For a later controlled driver test, `lmh_init_driver` is the strongest
  remaining reviewed secure-firmware probe. It is level 7, raw pointer offset
  `0x174d328` to `0xffffff800979ac10`; its enabled DT node is `/soc/qcom,lmh`.
  Adding that single skip would make the command line 504 bytes. Preserve
  `lmh_mon_init_call`, which initializes the shared interface. Prefer observing
  the LED marker before targeting this later stage. No LMH skip is in test 04.
- Do not blindly skip the crypto trio: `_qcrypto_init` initializes a global
  engine list used without readiness guards by built-in `req_dm_crypt`.

## 18. Fifth diagnostic: suppress optional QCE devices (October 16)

- Private candidate: `prepared/test-05-qce-disabled-boot.img`, SHA-256
  `2bdf23078453af1eaca576b3f89fcd5875200c935cc8778219399a8bad558700`.
  Relative to test 04, only two DT nodes gain `status = "disabled"` in each
  appended DTB: `/soc/qcrypto@660000` and `/soc/qcedev@660000`. Their probes
  access QCE clocks, MMIO, and BAM before the LED marker. This is a hardware
  probe hypothesis test, not an identified SCM fault.
- Keep both crypto initcalls: `_qcrypto_init` still initializes its engine
  list/workqueue, and `qcedev` has no accessible `/dev/qce` without its probe.
  Independent source/binary review found no analogous uninitialized-client
  hazard. Software/ARM64 crypto remains enabled; Qualcomm-specific encrypted
  storage operations may fail. Preserve `/soc/sdcc1ice@7443000`, eMMC, USB,
  display, all other DT properties, and the blue marker.
- Private guarded builder: `prepare_test05_qce_disabled.py`. It checks the
  exact source hash, compatible strings, MMIO ranges, and initially absent
  status properties, then verifies that these are the only semantic DT changes.
  Kernel gzip, ramdisk, and 488-byte command line remain identical to test 04.
  Both DTBs retain 8 KiB slack; rebuilt boot ID and `/boot` signature validate.
- **Test 05 was written to boot with verified full readback.** Fresh GPT/misc
  matched the backups; programming and readback ACKed. Padded readback SHA-256:
  `2d4a33946e671523939b7c2e9b2021c45a6545ec3fa87a9815424c3fbfbd4993`.
  Evidence: private `hardware-tests/test05-qce-disabled` locally and
  `test05-qce-disabled` remotely. Plan: `test05-qce-disabled-remote-plan.json`.
  Recovery and misc were unchanged. Read `session.json` for reset/live state.
- Readback was also copied and hash-verified on this Mac. A separate reset was
  sent; USB disconnected before ACK, EDL stayed absent in five samples over
  12 seconds, and adb was absent at the end. The owner subsequently reported
  **test 05: red LED, stuck on the ZTE screen during normal boot**. No positive
  marker or TWRP result was reported. Owner-managed EDL handling remains in effect.
- **Use a 3.18 boot-slot control before adding more cumulative 4.4 skips.**
  Existing control image:
  `prepared/reader-3.2.3-boot.img`, 23,430,195 bytes, SHA-256
  `76990c6f20c61a919629600c9afbb4551e0792e911f05034927852c9fcdefe28`.
  Kernel, both DTBs, and command line match the published 3.2.3 exactly; only
  `init.rc` gains charger `late-init` and `mtp,adb` → `adb`. Do not add the blue
  marker or 4.4 DT changes to this initial control. Use **boot**, not Recovery.
  The earlier backed-up reader's missing USB after Firehose reset did not
  establish that a clean normal boot-slot control failed in this session.
  TWRP/ADB would validate the current old-kernel boot path; no UI/ADB means
  resolve that control path before interpreting more 4.4 driver experiments.

## 19. Sixth diagnostic: published 3.18 boot-slot control (October 16)

- **Test 06 boot image:** `prepared/reader-3.2.3-boot.img`, 23,430,195 bytes,
  SHA-256 `76990c6f20c61a919629600c9afbb4551e0792e911f05034927852c9fcdefe28`.
  Kernel 3.18.71, both DTBs, the 227-byte command line, and load addresses
  match the published TWRP 3.2.3 image. Only `init.rc` changes: charger
  `late-init` and `mtp,adb` → `adb`. No blacklist, QSEE patch, blue marker,
  or 4.4 DT modifications are present.
- Two independent reviews checked the control and image-construction path.
  The boot ID and `/boot` RSA/SHA-256 signature verify, including verification
  independent of the image helper. CPIO, header layout, signed length, and
  preserved addresses were checked. No common construction error was found;
  this does not establish hardware acceptance or successful boot.
- EDL was detected automatically; the programmer loaded in RAM. Fresh GPT
  and misc matched their backups. **Only boot was programmed**, with ACK and
  complete readback verification on both Macs before reset. The 45,763-sector
  padded image is 23,430,656 bytes, SHA-256
  `320e252ae5b1e8b17cf366025217286c6c60b920f53b016e44d3080a9fce6c8d`.
  Evidence is in private `hardware-tests/test06-reader-control` locally and
  `test06-reader-control` in the MacBook session. The remote plan is
  `test06-reader-control-remote-plan.json`.
- A separate Firehose reset was sent once. USB disconnected before its ACK;
  EDL remained absent and adb 29 on port 5038 found no device in 21 samples
  over 41.4 seconds. **The owner subsequently confirmed test 06 boots TWRP.**
  adb 29 then connected in `recovery` state. Live kernel is
  `3.18.71lineageos-ge6d1b19ed527`, TWRP `3.2.3-0`; `ro.bootmode=charger`,
  `ro.boot.verifiedbootstate=yellow`, `sys.usb.config=adb`. The early no-USB
  observation was not a control boot failure.
- This validates the current 3.18 boot-slot image and enables direct captures
  and verified writes. It does not identify the 4.4 fault or prove that every
  failed 4.4 candidate entered its kernel. This EDL round erased the preceding
  RAM log; current pstore is empty.
- Private live captures: `hardware-tests/test06-reader-control/live-baseline`.
  They include kernel config, dmesg, command line, live DT, ramoops parameters,
  partition map, LED settings, recovery log, and mount state. Current reader
  ramoops: base `0xbfc00000`, total `0x100000`, records `0x8000`, console
  `0x80000` at **`0xbfc40000`**, pmsg `0x40000`, ftrace/ECC zero. Current 4.4
  candidate console instead calculates to `0xbfc80000`; align the complete
  layout before a RAM-preserving capture round.
- Blue/green/red LEDs bind to `leds-qpnp-25`; blue maps to the same PMI8994 RGB
  ID 5/PWM `b100` hardware as the 4.4 DT. A reversible 40-second sysfs blue
  test set brightness 255 then restored its original zero value. The owner's
  visual result is pending; sysfs success alone does not prove visible color.
- Stock system is still `Z999V1.0.0B37`, Android 7.1.2. Mounted it temporarily
  with `ro,noload`, archived all five `a530_zap.*` files and `build.prop`, then
  unmounted. Copies and per-file hashes are private on both Macs. This prepares
  the AT&T GPU firmware substitution without modifying system or installing LOS.
- This reader emits `propClient` warnings into `adb exec-out` binary streams.
  The two tar captures had an exact 76-byte warning prefix; separate `.clean.tar`
  derivatives were validated. Prefer writing binary captures into `/tmp` and
  `adb pull` so stdout warnings cannot corrupt partition readbacks.

## 20. Restore a log-reader route before the next 4.4 test (October 16)

- Prepared `reader-3.2.3-recovery-control.img`, 23,430,199 bytes, SHA-256
  `6850d87358bb4d46861b83a4c9f88b0fe57e41e6aa0f542e0e615e1b90bcf56b`.
  It derives from the proven test 06 boot image. Every existing encoded CPIO
  entry, kernel, DTB, command line, and init action is unchanged. The sole
  addition is root-owned mode-0444 `/fujisan-reader-slot`, containing
  `recovery-control-20261016` plus newline. The boot ID is rebuilt and the
  image signed for `/recovery`. Padded SHA-256:
  `f4ddb5f137977f1fa6410f11e48e20ed35e119c8eb21fc72e122ecfe20622384`.
  Builder: private `prepare_recovery_reader_control.py`; external CPIO and
  full signature validation passed. Consult `session.json` for write state.
- This is a new controlled recovery-route test: the old recovery image has
  different ramoops DT and ramdisk modifications. Keep the now-proven reader
  in boot. Back up and verify recovery/misc before writing the marked image;
  verify the complete recovery partition after the write. Plain
  `adb reboot recovery` is expected to use the reboot reason without setting
  a BCB command (exact reader adbd inspection); still check misc afterward.
  Do not invoke sideload or manually set `boot-recovery`.
- A returned TWRP counts as recovery success only if the marker file exists.
  Emit a unique kernel-log marker before reboot, then capture pstore to test
  RAM retention. If recovery selection fails, a normal Start boot should use
  the untouched working reader. A successful adb recovery reboot alone does
  not prove the manual recovery-entry route after a frozen 4.4 boot.
- Also prepared, **not flashed**: `test-07-early-blue-led-boot.img`, SHA-256
  `10eae36d5ede339594318203add501086d1956f9b818e779426873fa07ab1efe`.
  It retains test 05 and rotates the first 376 level-6 pointers to put
  `qpnp_led_init` first. All 690 level-6/7 entries retain their multiplicity;
  all other initcalls preserve relative order. Exactly 622 raw bytes change
  inside the pointer table, with no executable instruction changes. DTs,
  ramdisk and command line are unchanged. Independent signature and raw-byte
  checks passed. This remains a fallback visible diagnostic; prefer actual
  boot logs if a RAM-preserving reader route is established.
- Prepared `twrp-3.7.0-att-logged-recovery.img`, 26,178,615 bytes, SHA-256
  `7a80f52acfd8a522c30402dcca677fcb7673970ed5b68a5c6e9308c322a97dc5`.
  This uses the original published 4.4 kernel/gzip, fixes 1+2, charger ramdisk,
  and 358-byte command line including `ignore_loglevel initcall_debug`. There
  are no cumulative blacklist, QSEE, QCE, or LED modifications. The ramoops
  layout matches the current 3.18 reader. Its unused reservation expands down
  to `0xbfd00000` to preserve the overall `0xbfc00000`–`0xc0000000` reserved
  range. Full semantic DT diffs, hashes, and signature validation are private.
  **Not flashed; contingent on a proven recovery and RAM-preserving return.**
- In this published kernel, `ramoops_init` is level 2. The pstore console
  replays the printk buffer on registration and then logs continuously. It
  can capture an initcall stall before any 90-second snapshot timer runs,
  provided its probe succeeds. It cannot guarantee evidence of a fault before
  console registration. Capture pstore immediately on reader return.
- Private `adb_recovery_control.py` permits only the 3.18 recovery write and
  never reboots. Its 16 focused offline checks passed, including changed
  preflight inputs, wrong geometry, staged-image mismatch, full-partition
  tail corruption, boot/misc changes, and timeout/no-retry handling. Separate
  `test_reader_recovery_route.py` attempts one recovery reboot after verified
  readback, distinguishes a new boot from stale adb, and captures the slot
  marker, pstore, and misc without further reboot or partition writes.
- **The marked 3.18 recovery control has now been written through adb.** Fresh
  GPT, full recovery/misc, and the test 06 boot prefix passed preflight. The
  entire 64 MiB recovery readback matched the expected padded image plus
  unchanged tail on both Macs; full-partition SHA-256:
  `29b5052e639b46c2ea08c2cbdae59ecbb2e4a38b97f7b4e703019db83434cff8`.
  Boot prefix and misc were unchanged. Evidence: private
  `hardware-tests/reader-recovery-control`. Consult `session.json` and
  `reader-recovery-route` evidence for the subsequent route-test result.
- One plain `adb reboot recovery` was attempted after the verified write and
  a unique `/dev/kmsg` marker. The command completed, but no new adb boot was
  observed during the 55-second monitor. **Screen result and actual recovery
  selection remain unconfirmed.** The owner was asked to select normal Start
  if at that menu, returning to the untouched working boot reader without EDL.
  Capture pstore and check `/fujisan-reader-slot` immediately when adb returns.
  The logged 4.4 recovery image must remain unflashed until this route works.
- The owner subsequently returned to TWRP/adb. Captures in private
  `hardware-tests/reader-recovery-return` prove this is the **unmarked boot
  reader**. Misc is unchanged. `console-ramoops` (326,509 bytes) retained the
  unique pre-reboot kernel-log marker and prior 3.18 reboot-to-recovery trace;
  no second kernel banner or marked-recovery execution is shown. RAM retention
  through the actual return path is established; recovery selection is not.
- Live USB on this return: `sys.usb.config=adb`, `sys.usb.state=adb`, functions
  `ffs`, but **`persist.sys.usb.config=mtp,adb`**. The working reader's callback
  corrects that only after the request. A stronger adb-only boot patch is being
  prepared for this reader and the active 3.7 candidates, per owner preference.
- Read-only aboot capture: private `aboot-readonly-analysis/aboot.bin`,
  1,048,576 bytes, SHA-256
  `87bb01570c58e8b1c29f4b75cedba22b20f7efc2ca74feec566beb21094ded04`.
  Copies are on both Macs for recovery-selection analysis. No bootloader
  modification or write was performed.

## 21. Adb-only USB startup for TWRP (October 16)

- Added `patch_adb_only(ramdisk)` and `--adb-only` in `scripts/fujisan_image.py`.
  It changes only `prop.default` and `init.recovery.usb.rc`: all USB defaults
  become adb; TWRP's verified `mtp.crash_check=1` startup guard skips its first
  MTP request; MTP hardware activation blocks become adb redirects. The legacy
  function writes use fixed values rather than expanding a later property
  value. Existing charger actions, FunctionFS mounts, configfs readiness/UDC
  actions, binaries, kernel, DTBs, command line, and load addresses are retained.
  A later manual GUI MTP request may still cause an adb reconnect, but cannot
  bind MTP through the patched USB handlers.
- All **36 repository tests passed**, including five focused USB tests. Real
  archive audits cover both TWRP versions. Every other encoded CPIO entry is
  identical, external CPIO accepts the new archives, the patch is idempotent,
  and every rebuilt boot ID and full BootSignature validates.
- Private `prepare_adb_only_candidates.py` created new immutable variants;
  source/hardware-tested images were not overwritten. Manifest:
  `adb-only-candidates.json`. Prefer these candidates from now on:

  | Candidate | SHA-256 |
  |---|---|
  | `reader-3.2.3-boot-adb-only.img` | `dbefa370bc3014c2931ac9d940fc9417ee5f7bbf99fe5e3d865a9f59d0139b2e` |
  | `reader-3.2.3-recovery-control-adb-only.img` | `09c27a94d6a865a1dec4a36e71073c21836915b01d1a5da6721c1aa9a98d5ba9` |
  | `test-07-early-blue-led-boot-adb-only.img` | `1d46cae5a75550e5bd0ddd162c52f9288362fe1a09a93f18e522392de831bee7` |
  | `twrp-3.7.0-att-logged-recovery-adb-only.img` | `19eea0ac0091b100aeaa4d36850d335baa22f833b04e6bf6557c52148175bdc4` |
  | `twrp-3.7.0-att-charger-boot-adb-only.img` | `55bc66b96be06a2e4e3f0c946bcee1e14da1f132afe2cc1cd003a46d3ffbfd0c` |

- **The adb-only 3.18 reader is now written to boot.** Private
  `adb_boot_usb_control.py` reuses the reviewed adb transport, fixes its write
  to boot only, and passed ten focused offline safety tests. Fresh entire boot
  matched the reconstructed test 05→06 state, full recovery matched the marked
  control, and GPT/misc matched their backups. Complete 64 MiB readback was
  checked on both Macs. Full boot SHA-256 is now
  `95e32aa952517640df1b0607bf6dbe16d3daed7e79062d2e4473ab445cb26a7a`;
  padded image SHA-256 is
  `9cc3e245d5a849f14ea5fe93fde86c9e2e192669e0f4d8ded263840c75ff1f88`.
  Recovery and misc were unchanged. Evidence: `hardware-tests/reader-boot-adb-only`.
  The old writers/plans pin earlier boot hashes; do not rerun them blindly.
- A separate one-shot normal-reboot monitor checks for a new boot UUID on the
  same device, the two exact candidate ramdisk-file hashes, and live adb-only
  USB configuration. See private `session.json` and
  `reader-boot-adb-only-reboot` for its current result. The stronger USB patch
  is installed in boot; the marked recovery partition still holds its earlier
  control image until a later explicit test updates it.
- **Runtime adb-only boot is verified.** The owner reported TWRP open. The
  initial empty adb 29 inventory was a host connection conflict: adb 37 on
  port 5037 had acquired the phone in `recovery` state. Stopping that server
  released it, and adb 29 on port 5038 connected without a phone reboot.
  Both live ramdisk-file hashes match the new candidate; persistent USB config,
  current config, and state are all `adb`, active functions are `ffs`, and
  `mtp.crash_check=1`. Kernel/TWRP remain 3.18.71 / 3.2.3-0. The slot marker is
  absent, confirming the boot reader. Private evidence:
  `hardware-tests/reader-boot-adb-only-return`. Check competing host adb servers
  before interpreting an empty inventory as a failed boot or USB patch.
- The blue LED was requested at brightness 255 for 40 seconds in this verified
  reader, then restored to its original zero; the owner's visual result is
  still pending. Test 07's marker needs that physical calibration. A positive
  marker proves entry into its first level-6 driver, not completion of level 6;
  a missing marker remains inconclusive because the LED probe can fail/defer.
- Prepared private `adb_test07_control.py` and
  `test07-early-blue-led-adb-only-{local,remote}-plan.json`. The writer fixes the
  exact candidate hash, current full boot/recovery hashes, GPT, and boot node;
  it reuses the reviewed full-partition before/after transaction with no reboot.
  Nine focused offline checks passed; files-only preflight passed on both Macs.
  Image and writer are staged on the MacBook. **Test 07 is not written.**
- The owner requested another blue calibration and watched the 40-second
  brightness-255 repeat: **no light was visible**, despite sysfs reading 255.
  Brightness was restored to zero. The blue marker has therefore failed its
  physical positive control; investigate the LED mapping/control before
  spending a Test 07 flash. No new image was flashed or phone rebooted.
- A comparison requested green, then red at brightness 255 for 20 seconds
  each with their triggers temporarily disabled. Both were restored to zero;
  green's `none` trigger and red's `battery-charging` trigger were restored.
  The owner's comparison result is pending. No matching LED/PWM error appeared
  in dmesg; PWM debugfs is unavailable. The driver's sysfs value is stored
  before asynchronous hardware work, so readback alone cannot validate a color.

## 22. Physically calibrated green checkpoint (October 16)

- On the repeated green/red comparison, the owner confirmed **both green and
  red lit successfully**. Brightness returned to zero for both, with green's
  `none` and red's `battery-charging` triggers restored. Blue remains invisible
  in the 3.18 positive control; do not use its absence as kernel evidence.
- Prepared `test-07-early-green-led-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `9e30e21a7bea1b6cd95d7a3e0da8adacbcdc6507a44d58e87a2fd44cf5e03241`.
  Relative to the unflashed blue Test 07, only two DT properties change in
  each tree: green default-state off→on and blue on→off. Kernel gzip/raw bytes,
  first-level-6 LED initcall, QSEE patch, eight skips, ramdisk, command line,
  addresses, and all other DT properties remain unchanged. Both trees keep
  8 KiB slack; full `/boot` signature and boot ID validate.
- Padded image is 26,179,072 bytes (51,131 sectors), SHA-256
  `a240637dee97f98a34514880f736f96e29cdba8978d2aee024899d8962eb9c68`.
  Builder: private `prepare_test07_green_led.py`; guarded writer:
  `adb_test07_green_control.py`. Nine focused writer tests passed. The original
  blue image/writer are preserved. Consult `session.json` for write state.
- A fresh green transition supports reaching the first level-6 RGB driver;
  no green remains inconclusive. Pre-test battery was 99%, charging, with all
  three RGB brightness values zero. Distinguish a new kernel-stage transition
  from bootloader charging indication or retained PMIC state. Recovery selection
  remains unproven, and the logged 4.4 recovery image remains unflashed.
- **Green Test 07 is now written to boot.** Fresh GPT, entire previous boot,
  recovery and misc matched the pinned inputs. Complete 64 MiB readback was
  verified on both Macs against the padded candidate plus unchanged tail.
  Full boot SHA-256:
  `68db906dd36a53e013ac76cc1bdcb8b8dc195b3c5521604d755272645d74761a`.
  Recovery and misc are unchanged. Evidence: private
  `hardware-tests/test07-early-green-led-adb-only`. All earlier writers pin
  older boot contents and must not be rerun blindly. Separate
  `reboot_test07_green.py` permits only one normal reboot after checking the
  two-Mac readback receipt; consult session/reboot evidence for its result.
- One normal adb reboot was then sent successfully. No new adb boot appeared
  in the 55-second monitor. A subsequent USB check found no phone entry and
  confirmed the competing default adb server was not running. **The owner's
  Test 07 screen/green-transition report is pending; this does not establish
  a boot failure.** If the Start menu appears, select Start. Do not send another
  reset automatically. Reboot evidence:
  `hardware-tests/test07-early-green-led-adb-only-reboot`.
- **Owner result: stuck at ZTE, green light.** The owner clarified the timing:
  the Start screen is red; after starting, the ZTE screen appears and turns
  green about one second later. This fresh transition supports execution of
  the early level-6 RGB checkpoint in this exact published 4.4 derivative.
  It is not completion of level 6 or proof that TWRP userspace started. ADB
  remains absent. The earlier blue-negative tests do not establish an upper
  bound because blue failed the working-reader physical calibration.

## 23. Eighth diagnostic prepared: midpoint green checkpoint (October 16)

- Prepared `test-08-mid-green-led-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `761cd2d5251bad78e611c00a5cd2ac6d2401d7fd81e6f54fa864ad71877c5b7f`.
  It moves `qpnp_led_init` from the first level-6 position to index 307,
  after original entries 0–306 (`keyreset_init`) and before `keycombo_init`.
  This probes progress halfway through the 613 ordinary level-6 calls; it
  does not assume the stall is before the original LED position 375.
- All 690 level-6/7 pointers retain their multiplicity, and every other call
  preserves its relative order. Exactly 523 raw bytes change, all within
  `[0x174be28, 0x174c7c8)`. Executable code, later pointers including all sync
  and level-7 entries, DT tail, green marker settings, adb-only ramdisk,
  command line and load addresses remain unchanged. No new driver is skipped.
  Boot ID and full `/boot` signature validate; independent byte/table checks
  and files-only preflight passed on both Macs.
- Private builder `prepare_test08_mid_green.py`, plans
  `test08-mid-green-{local,remote}-plan.json`, and
  `test08-mid-green-independent-audit.json` are staged/prepared. The plans use
  the existing bounded Firehose boot writer. Before executing, separately
  capture and hash-check fresh entire boot/recovery/misc; the writer itself
  checks GPT/misc and the programmed prefix. Afterward also verify the entire
  boot and unchanged recovery/misc, then copy/hash-check on this Mac before reset.
- Current entire boot must be Test 07 hash `68db906dd36a53e013ac76cc1bdcb8b8dc195b3c5521604d755272645d74761a`.
  Expected entire boot after Test 08, including untouched tail:
  `1bd3ae30accf2d414aed0e0168ac486605674773315cddfe5fbf9d455f13d115`.
  Padded candidate SHA-256:
  `aff5befd3376b523f948bb07cbab24079650398a531c3991eac78b49c680cbcf`.
  Recovery remains the marked 3.18 control (`29b5052e…34cff8`), misc remains
  zero. Wait for owner-managed EDL; do not repeatedly request entry or send
  another reset to the currently hung image.
- **Test 08 has now been written through EDL.** Owner-managed EDL was detected
  automatically; the pinned programmer loaded in RAM once. Fresh entire boot,
  recovery, misc and GPT matched the expected Test 07 state before writing.
  The bounded boot-only write ACKed and its padded prefix readback matched.
  Separate full-partition after reads verified the expected whole-boot hash
  above, unchanged tail, and unchanged recovery/misc/GPT. Copies are checked
  on both Macs before reset. Private evidence directories:
  `test08-mid-green-full-before`, `test08-mid-green-led`, and
  `test08-mid-green-full-after` under `hardware-tests` locally and the remote
  session. Separate `reset_test08.py` gates a one-shot reset on the complete
  audits and local verification receipt. Consult its evidence for boot state.
- One Firehose reset was sent after both-Mac verification. USB disconnected
  before ACK; EDL was observed disappearing by 3.1 seconds. ADB 29 stayed
  empty through 40 seconds. **Test 08 screen/LED result is pending.** No reset
  retry was sent. Evidence: `hardware-tests/test08-mid-green-reset`.
- **Owner result: red, then green at ZTE.** This supports reaching the
  checkpoint after original entries 0–306, before `keycombo_init`, in the
  Test 08 derivative. It does not establish that the preceding drivers are
  functional or their asynchronous work finished; blacklisted calls remain
  skipped. The owner then explicitly reported EDL on for the next round.

## 24. Ninth diagnostic: end of ordinary level-6 calls (October 16)

- Prepared `test-09-end-level6-green-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `fd9640cdb44b3c5d9081cb91129020e5d2afbe619fdd21b9c33385d055d80568`.
  `qpnp_led_init` moves from table index 307 to 612, after `rmnet_init` and
  immediately before the unchanged `deferred_probe_initcall` at index 613.
  A fresh green transition supports progressing past all other ordinary
  level-6 calls; the sync tail, level 7, and userspace still remain.
- Exactly 468 raw bytes change in `[0x174c7c0, 0x174d150)`. All 690 pointers
  keep their multiplicity; all non-marker relative order, sync/level-7 slots,
  executable code, DT tail, green defaults, adb-only ramdisk, command line,
  addresses, and previous driver fixes remain unchanged. No additional skip.
  Independent permutation/byte checks and complete signature validation pass.
- Padded candidate SHA-256:
  `84ddcb03982b41def3bc60f529a8db450c7469f68cbd12e1325ce37fc6389613`.
  Required full boot before: `1bd3ae30accf2d414aed0e0168ac486605674773315cddfe5fbf9d455f13d115`.
  Expected full boot after: `d5374da02e0eec80d1fb7acdceb06f2961ac119ac1deab93586ba300673a6565`.
  Recovery remains the marked 3.18 control; misc remains zero.
- Private builder `prepare_test09_end_level6.py`; plans/spec named
  `test09-end-level6-green-*`. Files-only preflight passes on both Macs.
  New `edl_full_audit.py` is strictly read-only, with fixed GPT/boot/recovery/misc
  ranges and expected hashes. Use it before and after the existing bounded
  writer; verify full readbacks on both Macs before `reset_test09.py`.
  Consult `session.json` for current write/reset state. Programmer loaded in
  RAM once following the owner's EDL report; do not upload it again in the
  same Firehose session.
- **Test 09 is written and verified on both Macs.** Fresh full before reads
  matched Test 08 boot, marked recovery, zero misc, and original GPT. The
  boot-only program ACKed; its prefix and separate entire 64 MiB after read
  matched the expected hashes. Full boot tail, recovery, misc, and GPT remain
  unchanged outside the candidate prefix. Private evidence:
  `hardware-tests/test09-end-level6-green-full-before`,
  `test09-end-level6-green-led`, and `test09-end-level6-green-full-after`.
  One-shot `reset_test09.py` is gated by the complete after audit and local
  verification receipt; its result/screen observation must be recorded next.
- One Firehose reset was sent; USB disconnected before ACK and EDL immediately
  disappeared. ADB 29 remained empty through the 40-second monitor. **Test 09
  screen/LED result is pending.** No retry. Evidence:
  `hardware-tests/test09-end-level6-green-reset`.

- **Owner result: green on ZTE**, then owner reported EDL on. This supports
  reaching the final ordinary level-6 checkpoint in Test 09; no TWRP or adb
  was observed. Fresh red-to-green timing was not restated for this test.

## 25. Tenth diagnostic: after deferred probing (October 16)

- Prepared `test-10-after-deferred-green-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `b62156cff1a0ddf4c7bb126f19f0b4f9f97c80bfcb0202524cc773a4285b8cac`.
  Swap only the final two level-6 pointers: `deferred_probe_initcall` moves
  from index 613 to 612; `qpnp_led_init` moves from 612 to 613. Level 7 begins
  unchanged at index 614. The initcall loop uses level boundaries, with no
  separate runtime boundary between ordinary level 6 and its sync suffix.
- Exactly eight raw bytes change in `[0x174d148, 0x174d158)`. All 690 pointers
  retain multiplicity and all non-marker relative order remains unchanged.
  Executable code, DT tail, green default, adb-only ramdisk, command line,
  addresses, and previous diagnostic fixes are identical to Test 09.
  Builder and independent table/byte/signature audits pass; files-only
  preflight passes on both Macs. Private builder `prepare_test10_after_deferred.py`;
  plans/spec `test10-after-deferred-green-*`; staged runner `run_test10.py`.
- Fresh green supports return from `deferred_probe_initcall` before the marker.
  A missing green is conditional: moving LED registration past deferred probing
  may itself affect dependency behavior. Neither result proves every preceding
  driver is functional or that all asynchronous work has finished.
- Required full boot before: `d5374da02e0eec80d1fb7acdceb06f2961ac119ac1deab93586ba300673a6565`.
  Expected full boot after: `624418846d1055db5157cbf5e087359b4e6165b035174b0dd6d236ca10c1f657`.
  Padded candidate: `34bcfc82fc06e14509c2fb1cc2d4df15f33a66d3992d313251d0d07b24d12ef3`.
  Recovery/misc remain pinned to the marked 3.18 control and zero BCB.
  Owner reported EDL on, one device was detected, and the verified programmer
  loaded in RAM once. Full fresh before audit is underway; consult session.json
  and evidence directories for write/reset state. Do not reload the programmer
  within this Firehose session.
- **Test 10 written and full readbacks verified on both Macs.** Fresh complete
  before reads matched Test 09 and all protected partitions. The boot-only
  program ACKed and its padded prefix matched. Separate entire boot readback
  matches the expected hash above, with the old tail preserved exactly.
  Recovery, misc and GPT match their unchanged hashes. Evidence directories:
  `hardware-tests/test10-after-deferred-green-full-before`,
  `test10-after-deferred-green-led`, and `test10-after-deferred-green-full-after`.
  A local verification receipt was copied back to the MacBook before the
  separately guarded one-shot `reset_test10.py` was invoked.
- One reset was sent; USB disconnected before ACK, and EDL immediately
  disappeared. ADB 29 remained empty for the 40-second monitor; no competing
  default adb server was running. **Test 10 screen/LED result is pending.**
  No retry was sent. Evidence: `hardware-tests/test10-after-deferred-green-reset`.

- **Owner result: RED LIGHT ON ZTE SCREEN.** Test 10 has no positive green
  marker or adb. Compared with Test 09 green immediately before the deferred
  initcall, this implicates that call or work it activates, conditionally on
  delayed LED registration still succeeding. Inspect its stages next; do not
  treat the result as proof of a specific failing deferred driver.

## 26. Eleventh diagnostic prepared: bracket the deferred cycle (October 16)

- **Prepared locally, not flashed:** `test-11-deferred-pulse-v3-boot-adb-only.img`;
  image SHA-256 `cf98afbfe9bd39cc7177ce35f95824a9fca93b2dd634f6288c42386ee7d5dda6`.
  Earlier Test 11 unversioned/v2 builds are superseded and were never flashed.
  Keep current boot recorded as Test 10 until a new full readback proves a write.
- This derives from **Test 09**, restoring its complete 690-entry initcall
  table, including LED registration immediately before the level-6 sync.
  DTs, ramdisk with adb-only startup, command line, eight existing skips,
  and prior QSEE/QCE changes are preserved exactly.
- The shared `deferred_probe_initcall` runs at sync levels 3, 4, 5 and 6.
  Two guarded instruction hooks bracket its enabled cycle: at
  `0xffffff800867ec48`, a helper replaces `mov w8,#1` and restores w8=1;
  at `0xffffff800867ecd8`, a helper replaces `mov w0,wzr` and restores w0=0.
  The original enable store, mutex/list/queue operations, `flush_workqueue`,
  flag-clear and function return remain intact. Separate late enable is untouched.
- A 322-byte helper occupies part of the already blacklisted `msm_pil_init`
  body `[0xffffff8009786674,0xffffff800978684c)`. No external direct/conditional
  branches enter that body; the original initcall address remains blacklisted.
  Its entry is a harmless return-zero stub; hooks call interior helper entries.
  Only init-time calls reach the helpers, before init memory is freed.
- The helper takes the LED-list read lock, matches exact name `green`, QPNP
  callback, max brightness 255 and RGB ID 4, then uses the already initialized
  driver's synchronous worker. It releases the list lock before any sleep or
  deferred processing, preserves callee-saved registers, bounds traversal, and
  uses aligned literal addresses. Earlier sync levels without the LED just
  continue normally. It never registers the LED twice.
- Before enabling the cycle: green off for 500 ms, on for 500 ms, then off.
  After the unchanged flush returns: green on. **Observe the complete pulse**,
  then its final color. Pulse followed by stable green supports flush return;
  pulse followed by red narrows the enabled cycle or following instrumentation.
  No observed pulse, or green alone, remains inconclusive. Timing changes by
  one second when the matching green LED exists; hardware operation still needs
  the observed pulse as calibration. This is a diagnostic, not a boot fix.
- Source inspection: developer `drivers/base/dd.c` matches exact binary stages;
  offsets/ABI checked separately against the shipped kernel. Local files:
  `prepare_test11_deferred_pulse_v3.py`, `test11_deferred_marker_v3.S`,
  `test11-deferred-pulse-*` plans/audit, `run_test11.py`, `reset_test11.py`.
  Full signature, raw byte intervals, all table entries, payload preservation
  and local files-only preflight pass. Independent final binary review pending.
- Expected full boot before: `624418846d1055db5157cbf5e087359b4e6165b035174b0dd6d236ca10c1f657`.
  Expected full boot after: `0f3431713ee215f602cef9eeda459eaebdb049f41ab2db8458df54dc3084959c`.
  Padded image hash: `8ebc5841656b65d92fc9da5077cfa7bc17f9eff01e1e4c5c87f23c0ba6de6392`.
  Keep full fresh before/after audits and two-Mac verification before reset.
- **Independent final v3 binary review passed.** All ten linked helper calls,
  both hooks, register/stack behavior, literal alignment, bounded lookup, byte
  intervals, preserved probing sequence, payload fields, boot ID and signature
  were checked separately. Both Macs pass files-only preflight. EDL appeared
  automatically; one programmer load succeeded. Fresh entire before reads
  match Test 10 boot, protected recovery/misc and GPT. The boot write is underway;
  consult transaction/after-readback evidence before reset.
- **Test 11 v3 is written and fully verified on both Macs.** Fresh entire
  before reads matched Test 10. Boot programming ACKed and the padded prefix
  matched. Separate entire 64 MiB after readback has the expected full hash
  `0f3431713ee215f602cef9eeda459eaebdb049f41ab2db8458df54dc3084959c`;
  its untouched tail, recovery, misc and GPT remain exact. Evidence:
  `hardware-tests/test11-deferred-pulse-full-before`,
  `test11-deferred-pulse-led`, and `test11-deferred-pulse-full-after`.
  Local verification receipt was returned to the MacBook before invoking
  the separate guarded one-shot reset. Screen/pulse observation is pending.
- One Firehose reset was sent; USB disconnected before ACK and EDL vanished
  immediately. ADB 29 remained empty throughout the 40-second monitor, and no
  competing default adb server was running. **Test 11 pulse/screen result is
  pending.** No retry. Evidence: `hardware-tests/test11-deferred-pulse-reset`.

- **Owner result: red, green, red; stays red.** The observed pulse validates
  the synchronous marker path. No subsequent green supports non-completion
  within the enabled deferred cycle or following marker; it does not identify
  a device or distinguish trigger/queue/flush. Test 12 will move the final
  marker immediately before the unchanged flush to split that interval.

## 27. Twelfth diagnostic: immediately before deferred flush (October 16)

- Prepared `test-12-before-deferred-flush-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `a2eed15eb70e83876dd3e306fadadbf52702d0a80e3b621cfeb237eb9adbb1bb`.
  Exactly 12 raw bytes change from Test 11 v3: `0xffffff800867ecd0` becomes
  a BL to existing marker helper `0xffffff80097866bc`; `0xffffff800867ecd8`
  is restored to `mov w0,wzr`; the helper's final instruction before RET
  reconstructs `ldr x0,[x19,#0xfa8]` for the original flush argument.
- Original queue and flush calls, all 690 initcall pointers, calibrated
  pre-enable pulse, remaining helper code, DTs, adb-only ramdisk, command line,
  addresses and existing diagnostic fixes remain byte-exact. Both Macs pass
  files-only preflight. Independent final artifact review validates the three
  instructions, ABI, full payload preservation, boot ID and signature.
- Interpretation: red-green-red calibration pulse **then a second green**
  supports return from queue_work_on and reaching the marker just before flush.
  It does not prove flush entered or returned. Persistent red is conditional:
  asynchronous deferred work or marker lock contention can prevent the marker.
  This narrows the interval without suppressing deferred retries.
- Builder `prepare_test12_preflush.py`; plans/audit `test12-before-deferred-flush-*`;
  staged runner `run_test12.py`, reset `reset_test12.py`.
  Required entire boot before: `0f3431713ee215f602cef9eeda459eaebdb049f41ab2db8458df54dc3084959c`.
  Expected entire boot after: `fbcdc7ca94e8549fdceff1ed71537e94792264734c5ccea4bdc223bace93f310`.
  Padded candidate SHA: `4b2fba66fed80bfde4d21dd1ffded61dcf70481015e5bf79f1023d7713a0f84a`.
  EDL was detected automatically and the programmer loaded once. Full before
  audit is underway; consult session/evidence for current write/reset state.
- **Test 12 is written and fully readback-verified on both Macs.** Fresh full
  before reads matched Test 11. Boot programming ACKed and padded readback
  matched; separate full boot readback matched the expected entire hash above
  and preserved its previous tail. Recovery, misc and GPT are unchanged.
  Private evidence: `hardware-tests/test12-before-deferred-flush-full-before`,
  `test12-before-deferred-flush-led`, and `test12-before-deferred-flush-full-after`.
  After the local verification receipt was returned to the MacBook, the
  separately guarded one-shot reset was invoked. Pulse/screen result pending.
- **Owner result: red, green; stays green, stuck on ZTE logo.** This supports
  the new pre-flush checkpoint, making unfinished deferred work the leading
  hypothesis. The full intermediate calibration sequence was not explicitly
  restated, so do not claim an independently observed second green transition.
  No TWRP was reported. Investigate the worker's individual device retries next.
- Test 12 reset evidence confirms one reset sent, USB disconnect before ACK,
  EDL disappearance, and no adb through 40 seconds. No reset retry. Private
  evidence: `hardware-tests/test12-before-deferred-flush-reset`.

## 28. Thirteenth diagnostic: seek adb with deferred work outstanding (October 16)

- Prepared `test-13-deferred-observability-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `5181b02e77574c97986ca989d04e7e61336c0d8ded9651c3337e206bb8012129`. **Temporary observability image, not a fix.**
  Aim: allow initramfs adb to start so actual dmesg/worker stacks can be captured.
- A 48-byte conditional helper at `0xffffff80097867b8` retains the original
  deferred flush when no matching green LED exists (earlier sync levels).
  Once the registered LED is found, it returns without waiting. It preserves
  the original workqueue pointer and ABI. Two flush BLs are redirected:
  shared sync at `0xffffff800867ecd4`, late enable at `0xffffff800867ed98`.
  Queueing, retry callbacks, enable/disable stores and list operations remain.
- NOP only the `free_initmem` call at `0xffffff800904453c`, retaining 640 KiB
  until reboot while callbacks may remain outstanding. The preceding global
  `async_synchronize_full` and subsequent memory protection stay intact; exact
  memory-protection ranges exclude this retained init region.
- Retain late power handoff votes by substituting only table entries 686
  `regulator_init_complete`, 687 `regulator_proxy_consumer_remove_all`, and
  688 `clock_late_init` with the already blacklisted return-zero stub
  `msm_pil_init` at `0xffffff8009786674`. The other 687 pointers remain exact.
  These cleanups assume deferred probing has completed; skipping only the
  waits could otherwise remove clocks/regulators from an outstanding probe.
  Core clock/regulator initializers and the last ALSA initcall are retained.
- Exactly 62 raw bytes differ from Test 12, within the new helper, three
  instructions and three pointer entries. Pulse helper, DTs, adb-only ramdisk,
  command line, load addresses and previous diagnostic fixes remain unchanged.
  Private builder `prepare_test13_observability.py`, helper
  `test13_conditional_flush.S`, plans/audit `test13-deferred-observability-*`,
  runner `run_test13.py`, reset `reset_test13.py`. Local checks pass; final
  independent binary review and MacBook preflight are underway.
- If adb appears, capture dmesg and task/worker stacks immediately. The ramdisk
  contains /init and adbd; /init avoids prepare_namespace's probe wait. This is
  not guaranteed to boot: later initcalls, global async work, device/parent
  locks, USB dependencies or a system-wide fault can still block progress.
  A negative result does not justify declaring any particular driver faulty.
- Required entire boot before: `fbcdc7ca94e8549fdceff1ed71537e94792264734c5ccea4bdc223bace93f310`.
  Expected entire boot after: `7ee949dc3658ba7701da63b8548cb934660aec79a38c15cb800d0e12e1489afb`.
  Padded candidate SHA: `d54ca9f08a4b3ea9868dd0be00a52a96b1f80234919c71625d5bfd1e1b5bb207`.
  Continue complete fresh before/after audits and two-Mac verification before
  any separate reset. Current boot remains Test 12 until verified writing.
- **Final independent Test 13 review passed**, including all hook targets,
  both helper branches, original workqueue argument, ABI, cleanup substitutions,
  exact 62-byte delta in five contiguous allowed ranges, retained async wait
  and memory protection, payload preservation, boot ID and full signature.
  Both Macs pass files-only preflight. Programmer loaded once after automatic
  EDL detection; fresh full before audit is underway. Private
  `capture_test13_adb.py` is prepared for immediate read-only live logs/stacks
  if adb appears. Captures stay private and no reboot is part of that script.
- **Test 13 is written and fully verified on both Macs.** Fresh full before
  reads matched Test 12. Programming ACKed and padded readback matched; the
  separate entire boot readback matched
  `7ee949dc3658ba7701da63b8548cb934660aec79a38c15cb800d0e12e1489afb`,
  preserving its previous tail. Recovery, misc and GPT are unchanged.
  Evidence: `hardware-tests/test13-deferred-observability-full-before`,
  `test13-deferred-observability-led`, and `test13-deferred-observability-full-after`.
  Local verification receipt returned to MacBook before the separate one-shot
  reset. If adb connects, use the staged read-only capture immediately.
- One Test 13 reset was sent; USB disconnected before ACK and EDL vanished
  immediately. ADB 29 remained empty through 40 seconds, and no competing
  default adb server was running. **Owner Test 13 screen/LED result pending.**
  No retry. Evidence: `hardware-tests/test13-deferred-observability-reset`.
  Live capture script has not run because adb has not appeared.
- **Owner result: red, green; stays green, no TWRP, ZTE logo.** Test 13 did
  not expose adb or a recovery UI. Its green marker does not prove that the
  main init thread progressed through level 7 or reached userspace; a later
  checkpoint is needed before blaming a specific remaining driver.

## 29. Fourteenth diagnostic: main init return checkpoint (October 16)

- Prepared `test-14-pre-async-green-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `5f64ae91932c0befbbc37f11072f2f444f762230dd6b7040ada2188aae6b4992`.
  The Test 13 conditional deferred-flush helper now turns green OFF. A new
  28-byte wrapper at `0xffffff80097867e8` turns green ON after
  `kernel_init_freeable` returns, then calls the original
  `async_synchronize_full` exactly once. The original async call site at
  `0xffffff8009044538` targets this wrapper. FP/LR and stack alignment persist.
- Exactly 34 raw bytes change within three intended ranges; all 690 Test 13
  initcall pointers, retained init memory and power votes, memory protection,
  DTs, adb-only ramdisk and remaining payload stay exact. Full signature,
  boot ID and independent final binary review pass; both Macs pass preflight.
- Final green after the earlier OFF supports return from the main initialization
  routine, before global async synchronization completes. It does not prove
  userspace started. Persistent red remains conditional on the LED helper
  completing while deferred work runs. This remains a temporary diagnostic.
- Builder `prepare_test14_pre_async.py`, helper `test14_pre_async_marker.S`,
  runner `run_test14.py`, plans/audit `test14-pre-async-green-*`.
  Required entire boot before:
  `7ee949dc3658ba7701da63b8548cb934660aec79a38c15cb800d0e12e1489afb`.
  Expected entire boot after:
  `097c2cf4f6b66746dcc41a96c4cdea9499c4b79d40889497731282092c9643fb`.
  Padded candidate SHA:
  `5a84aefc38509861e5ebbef0813bcd4b135315dd2a8a4ef3cd28d5df64b97190`.
- EDL detected automatically; pinned programmer loaded once. Fresh full before
  audit is underway. No Test 14 phone write or reset yet at this entry.
- Before audit stopped safely: boot, recovery and GPT match, but `misc` now
  contains only `boot-recovery` at offset 0 and `recovery\n` at offset 64
  (22 nonzero bytes; all other bytes zero). Hash:
  `f413538986a6a7d5b21fb83c0271f77d60d091074331edff25298f99759f052f`.
  Its origin is unknown; do not attribute it to a particular boot or owner
  action. No Test 14 boot write occurred. Full captures copied locally and
  verified. Prepared `clear_test14_bcb.py` to clear only those bytes via a
  single fixed 512-byte sector program, with exact fresh before checks and
  full 1 MiB readback. This restores original zero misc and normal boot routing.
- Independent BCB-clear review passed. The single-sector write ACKed and full
  readback matched original zero misc; both Macs verified exactly 22 changed
  bytes and no other differences. No reset sent. Evidence `test14-clear-bcb`;
  stopped before-audit preserved as `test14-pre-async-green-full-before-preclear`
  on both Macs. Repeating the read-only full before-audit with the original
  zero-misc requirement before proceeding to the Test 14 boot write.
- **Test 14 is written and fully verified on both Macs.** Fresh before checks
  passed after the BCB clear. Boot programming ACKed; padded readback and
  separate full 64 MiB readback match their expected hashes above, including
  the preserved boot tail. Recovery and GPT are unchanged; misc is original
  zero. Evidence `test14-pre-async-green-full-before`,
  `test14-pre-async-green-led`, `test14-pre-async-green-full-after`.
  Local verification receipt returned to MacBook before the separate guarded
  one-shot reset. Screen/LED result is pending. Read-only adb capture is staged.
- One reset sent; USB disconnected before ACK and EDL disappeared. No adb
  through 40 seconds and no competing default adb server. No reset retry.
  **Owner Test 14 result: "green is back".** This supports reaching the new
  checkpoint after `kernel_init_freeable`, before the global async wait.
  It does not prove the wait returned or userspace executed. Test 15 will move
  the same marker immediately after that unchanged wait to split the interval.

## 30. Fifteenth diagnostic: immediately after global async wait (October 16)

- Prepared `test-15-after-async-green-boot-adb-only.img`, 26,178,611 bytes,
  SHA-256 `66737d4e93f3387bfbaee67b197916577b54b311b778cad5475264a0b70d6334`.
  Reorder three instruction slots in the existing 28-byte Test 14 wrapper:
  call original `async_synchronize_full`, set brightness 255, call `green_sync`.
  Both calls still run exactly once; the frame and return sequence are exact.
  Only 11 raw bytes change within `0xffffff80097867f0..0xffffff80097867fc`.
- All hooks, 690 initcall pointers, conditional gates, retained memory and
  power votes, DTs, adb-only ramdisk, command line and remaining payload remain
  exact to Test 14. Independent final binary review, boot ID and signature pass.
  Final green after the earlier OFF supports async wait return, not /init
  execution. Red is conditional on reaching/completing the marker helper.
- Builder `prepare_test15_after_async.py`, assembly `test15_after_async_marker.S`,
  runner `run_test15.py`, plans/audit `test15-after-async-green-*`.
  Padded SHA: `a709d8b831b0c18c64b1d3beb90de4f432d5c687853b0161650c938076603a81`.
  Required full boot before: `097c2cf4f6b66746dcc41a96c4cdea9499c4b79d40889497731282092c9643fb`.
  Expected full boot after: `4dbad643723bb189b72b5afa63178ba00eb00afe5b439b56f58252f0d5bf49e0`.
  No Test 15 phone write yet. Current boot is Test 14. Latest USB check has no
  EDL or adb. Detect EDL and continue the audited workflow when available;
  do not repeat reset or ask for routine EDL entry.
- Test 15 files-only preflight now passes on both Macs. Candidate, plan,
  audit specification, guarded reset and read-only adb capture are staged.
  Latest EDL count remains zero; no programmer load or Test 15 write attempted.
- **New Test 14 observation before Test 15: owner reports ZTE logo disappeared,
  green LED still on.** Test 15 is held for live observation; do not auto-flash
  while this observation is being investigated. First fresh MacBook check has
  no adb, no default-port adb server and no EDL. Logo disappearance alone does
  not establish async completion or userspace execution. Requested one brief
  owner Power press (not a hold) to distinguish screen blanking from a visible
  boot/UI state; response pending. Read-only one-minute USB/adb monitoring is
  underway in `test14-late-logo-disappearance`, with live capture if adb appears.
- The one-minute monitor completed: 12 samples, no adb, no EDL, and no USB
  device-list changes. No live logs could be collected. Private observations
  copied locally. Brief Power-press screen result is still pending; Test 15
  remains unflashed and on hold. The current phone image is still Test 14.
- **Owner follow-up: screen does not wake after brief Power press; manually
  rebooted into EDL.** MacBook confirms one EDL device. Test 14 live observation
  is finished without adb or TWRP UI. Release the Test 15 observation hold and
  proceed with the already reviewed candidate and fresh full partition audits.
- Test 15 initial before audit again found exactly the 22-byte `boot-recovery`
  BCB pattern, hash `f413538986a6a7d5b21fb83c0271f77d60d091074331edff25298f99759f052f`.
  Boot/recovery/GPT are exact. This recurred after verified zero misc before
  Test 14; writer remains unidentified. Preserved entire pre-clear evidence on
  both Macs. `clear_test15_bcb.py` is identical to reviewed Test 14 clear code
  except evidence path names: one-sector clear ACKed, full 1 MiB readback is
  original zero misc, exactly 22 bytes changed. No reset or boot write yet.
  Investigate whether early TWRP userspace could set the flag before UI/adb;
  do not treat the BCB alone as proof of a particular execution point.
- **Test 15 is written and fully verified on both Macs.** After the BCB clear,
  fresh full before checks passed. Boot program ACKed; padded readback matches
  and the entire 64 MiB after hash is
  `4dbad643723bb189b72b5afa63178ba00eb00afe5b439b56f58252f0d5bf49e0`.
  Boot tail, recovery and GPT are exact; misc is original zero. Evidence:
  `test15-after-async-green-full-before-preclear`, `test15-clear-bcb`,
  `test15-after-async-green-full-before`, `test15-after-async-green-led`,
  `test15-after-async-green-full-after`. Local verification receipt returned
  before separate guarded reset; owner LED/screen observation pending.
- Independent investigation of the exact shipped recovery binary/library
  supports an early-userspace explanation for the recurring BCB, without
  proving writer identity. `/sbin/recovery` calls `get_args` at offset `0xec98`.
  `libbootloader_message_twrp.so` SHA
  `105e5bd0a13f462d916d99fca3d77e6223d5402a7c845e4737f6d50d45819abf`
  copies the two strings and calls `write_bootloader_message` at `0x3078`.
  With zero BCB and argc=1, that yields exactly the observed 22 nonzero bytes.
  Primary source: [BCB implementation](https://raw.githubusercontent.com/TeamWin/android_bootable_recovery/android-9.0/bootloader_message_twrp/bootloader_message.cpp)
  and [startup order](https://raw.githubusercontent.com/TeamWin/android_bootable_recovery/android-9.0/twrp.cpp).
  `get_args` follows low-level GUI/resource/fstab setup and precedes interactive
  GUI startup. This is compatible with TWRP starting before visible UI/adb;
  it does not rule out a bootloader/button-related writer.
- One Test 15 reset sent; USB disconnected before ACK and EDL disappeared.
  No adb through 40 seconds, and no competing default adb server. No retry.
  Evidence `test15-after-async-green-reset`. **Owner LED/screen result pending.**
- Exact Test 15 ramdisk inspection confirms adb startup is independent of
  interactive TWRP: FunctionFS mounts on `fs`; USB rc requests adb on `boot`,
  starts adbd, then `sys.usb.ffs.ready=1` links `ffs.adb` and binds UDC
  `6a00000.dwc3`. Recovery is a separate default-class service. Debuggable and
  unsecured recovery adb settings and MTP guard are intact. A blank UI alone
  does not account for absent USB; investigate UDC/FunctionFS/init readiness.
  Check whether persistent cache recovery logs exist before adding another
  userspace diagnostic; do not assume they were flushed from `/tmp`.
- Exact shipped binary's first normal `Update_Log_File` call is at `0xf528`,
  after `get_args`, boot scripts and optional decryption UI, before settings,
  ORS, MTP and main UI. It writes `recovery/log.gz`, rotates the previous log
  to `last_log.gz`, then clears BCB at `0x600c4` and syncs at `0x60270`.
  [Primary implementation](https://raw.githubusercontent.com/TeamWin/android_bootable_recovery/android-9.0/twrp-functions.cpp).
  Retained BCB is compatible with not completing this save/clear, a failed
  clear or a later writer. A read-only cache capture may expose partial/new
  logs; establish provenance from contents, not timestamps alone.
- **Owner Test 15 result: green on ZTE, remains green after screen turns off.**
  This supports return from `async_synchronize_full`. No adb on fresh check.
  Next focus is concrete runtime logs and USB/recovery startup, then validated
  AT&T fixes for LOS 23.2. Temporary deferred-wait bypass and resource-retention
  changes still require diagnosis/removal; passing the marker is not a ROM fix.
- Further ramdisk audit qualifies cache-log expectations: `/cache` is declared
  raw `emmc`, so TWRP cannot normally mount it even though `get_log_dir` selects
  it. Cache-path logs can remain in RAM. The working Test 06 baseline proves
  this phone's cache is ext4, mounted from `mmcblk0p36`; GPT start 15204376,
  count 3356672, 1,718,616,064 bytes. Prepare independent bounded RAM collection
  and cache persistence, with a full verified cache backup before running it.
  Preserve all existing cache files and do not format or touch system/userdata.

## 31. Sixteenth diagnostic preparation: persistent runtime logs (October 16)

- Stop adding kernel LED checkpoints: Test 15 supports return from the global
  async wait. Keep its kernel and USB/adb-only configuration exact and add two
  independent, asynchronous post-fs services: bounded RAM collection and a
  separate cache persister. Three snapshots capture kernel/recovery logs,
  init/adbd state, UDC/configfs/FunctionFS state and selected task stacks.
  A stuck mount or sysfs read must not stop init or the independent collector.
- Only a new `/axon-diag-test16` directory on cache may be created. Mount the
  verified cache privately at `/tmp/axon-cache-test16`; leave global `/cache`
  in RAM so TWRP cannot rotate existing on-disk recovery logs. Fail closed on
  wrong UUID, geometry, filesystem type, existing mounts or existing output.
  No formatting, fsck, system/userdata writes or USB-configuration changes.
- Private scripts `test16-collect.sh`, `test16-persist.sh`, `test16-init.rc`;
  builder `prepare_test16_runtime_logs.py` refuses to create a candidate until
  full cache backup verification supplies the filesystem UUID. Runtime capture
  remains diagnostic and retains Test 15's temporary kernel bypasses.
- Read-only backup tooling `backup_test16_cache.py` and
  `run_test16_cache_backup.py` pins GPT and exact cache bounds, checks the
  superblock, reads all 1,718,616,064 bytes, verifies compressed backup content,
  and rereads the actual local sparse copy before issuing a two-Mac receipt.
  EDL became available automatically; programmer loaded once and full cache
  backup is underway. No Test 16 image has been built or flashed at this entry.
- Installed e2fsprogs locally (debugfs 1.47.4, invoked by absolute path without
  changing PATH). `extract_cache_diagnostics.py` uses debugfs's default read-only
  mode and an explicit log-file allowlist on local backup files. Private logs
  stay outside Git. No debugfs command targets the physical phone.
- Full cache backup now verifies on both Macs, SHA
  `2c73c93e82a0d1ed7c1dc8c47595492eb8aac100bb420ffa1d5da64dd5deafd7`.
  Raw size 1,718,616,064 bytes; compressed 7,791,612 bytes. Private evidence
  `hardware-tests/test16-cache-before`. Read-only extraction found only old
  TWRP 3.2.3 `log`/`last_log`, no new diagnostic directory. UUID stays private.
- Prepared `test-16-runtime-logs-boot-adb-only.img`, 26,182,707 bytes, SHA
  `195e811d725dc034826f6bcd6e42448e99d82b25afb1acb4f2100fa849b31859`.
  Kernel/DT/cmdline are byte-exact to Test 15; only init.rc and the two added
  scripts change. Full signature/boot ID and both Macs' files-only preflight
  pass. Scripts pass syntax, bounded-output, atomic-publication, UUID/mount
  rejection, and no-overwrite checks. Final artifact review is underway.
- Required full boot before:
  `4dbad643723bb189b72b5afa63178ba00eb00afe5b439b56f58252f0d5bf49e0`.
  Expected full boot after:
  `5a3569ca898ef91fe742b663e190d200a4ac3df9a6385a5b081e837d97666783`.
  Padded SHA: `5d1f1157846bb8eb8246625ed4f868246293519b7723ba5d994d674b12b09643`.
  Runner `run_test16.py` additionally requires the two-Mac cache receipt and
  rehashes the entire remote cache backup before any boot program operation.
  Programmer remains loaded from the single backup session; do not reload it.
  Fresh full before audit is underway; no Test 16 boot write/reset yet.
- Final independent artifact review passed: exact Test 15 kernel/DT/cmdline,
  only the three intended ramdisk entries, pinned UUID, embedded syntax/tool
  availability, signature and boot ID. First before audit again found only
  the same 22-byte recovery BCB pattern; boot/recovery/GPT match Test 15.
  Full pre-clear evidence preserved as `test16-runtime-logs-full-before-preclear`.
  Reviewed one-sector BCB clear ran once and verifies as original zero misc
  on both Macs (`test16-clear-bcb`). Fresh before audit is being repeated.
- **Test 16 is written and fully verified on both Macs.** Fresh before audit
  passed, cache-backup gate passed, boot program ACKed, padded and entire
  64 MiB readbacks match above, with the boot tail preserved. Recovery/GPT
  unchanged; misc verified zero before boot. Evidence `test16-runtime-logs-*`.
  Two-Mac receipt returned before the guarded one-shot reset. Allow at least
  60 seconds for three snapshots and persistence, even with no UI/adb.
- After-boot read-only cache capture is prepared/staged as
  `backup_test16_cache_after.py` and `run_test16_cache_after.py`; the latter
  verifies the captured filesystem UUID matches the before backup. Use after
  the owner returns to EDL, load the programmer once only, capture/verify, then
  `extract_cache_diagnostics.py .../test16-cache-after/cache.bin --phase after`.
  Do not flash another image before attempting this diagnostic retrieval.
- Test 16 reset was sent once; USB disconnected before ACK and EDL disappeared.
  No adb during the first 40 seconds or a further 25-second monitor; no competing
  default adb server. The >=60-second collection window has elapsed, but actual
  service completion/persistence is not yet proven. Await next EDL connection
  and retrieve cache before any new image write. Programmer is not loaded now.

## 32. LOS 23.2 transfer constraints (October 16)

- LOS boot/recovery share raw kernel SHA
  `d1792237ae69783c646ab25ad94d439c4ad43d76a63bed37164950df4db52def`,
  different from the tested TWRP kernel. Do not copy TWRP raw instruction
  offsets, helper caves, initcall table offsets or pointer values into it.
  Transfer semantic fixes with exact LOS symbol/disassembly validation.
- LOS embedded kernel config has PSTORE disabled. TWRP ramoops logging
  assumptions do not transfer. F2FS is enabled but F2FS_FS_ENCRYPTION and
  FS_ENCRYPTION are disabled. Existing stock userdata is encrypted; the working
  reader could not decrypt it. Do not infer a compatible f2fs filesystem from
  the ROM's fstab or comments, and do not format userdata as part of diagnostics.
- LOS recovery contains adbd but disables it by default and configures USB none
  until menu sideload. It also waits early for display/input nodes. It needs
  its own diagnostic startup changes; TWRP's adb-only patch is not a blind fit.
- LOS boot ramdisk contains legitimate duplicate `dev` archive entries. The
  current strict `cpio_entries` rejects these, so archive handling requires a
  narrow, verified adaptation before editing that ramdisk.
- AT&T GPU shader files are privately captured with verified manifest hashes;
  replacing their counterparts in the LOS block-system payload is not yet
  prepared. Preserve the AT&T bootloader/firmware chain throughout.

## 33. Test 16 observation and startup review (October 16)

- **Owner result: red, green, green on the last booted test.** Latest MacBook
  checks show no adb or EDL. Test 16 remains installed; no new flash/reset.
  The collection window elapsed, but logger execution/persistence is unproven.
  At next EDL, retrieve and verify cache using section 31 before any next write.
- A concrete possible pre-logger stall exists: Test 16's `init.recovery.usb.rc`
  synchronously writes `peripheral` to the DWC3 mode attribute during `fs`,
  before the two diagnostic services start at `post-fs`. In the exact published
  kernel, `mode_store` at `0xffffff80087dc4f0` calls `dwc3_ext_event_notify`
  through `0xffffff80087dc558`; notify calls `flush_delayed_work` at
  `0xffffff80087daee8` before updating inputs/queueing OTG work. This can wait
  for prior USB work, but is **not yet the observed cause**. If probe never
  created the mode attribute, the write instead fails promptly. The published
  binary lacks the newer source branch's extcon early-return guard.
  [Matching earlier developer source](https://github.com/Anya1014CN/android_kernel_zte_msm8996/blob/d90bd3b69fa1a9587212addcfe7c6b5a93da65a5/drivers/usb/dwc3/dwc3-msm.c#L2894).
- Main init actions register before imported-file actions: imports are deferred
  until the main file has been parsed, and matching actions run in registration
  order with synchronous commands. Therefore a fallback logger should start
  immediately after main `on init` creates/configures `/tmp`, before the imported
  qcom brightness/touch writes and before `fs`. Main `on boot` starts the default
  class before imported USB boot actions, so an on-boot-only stall would not
  itself explain recovery never being spawned.
  [AOSP import handling](https://github.com/aosp-mirror/platform_system_core/blob/android-8.1.0_r1/init/import_parser.cpp#L46),
  [action execution](https://github.com/aosp-mirror/platform_system_core/blob/android-8.1.0_r1/init/action.cpp#L277).
- Exact Test 16 ramdisk reinspection confirms `on charger` triggers `late-init`;
  that action queues `fs`, `post-fs` and boot. Do not repeat the older missing
  charger-trigger diagnosis. Empty cache alone still cannot distinguish failure
  before `/init`, an init-action stall, or persister identity/mount failure.
- Recovery is launched by main `on boot` / `class_start default`, after
  `post-fs` on this normal trigger path. If a particular boot's BCB is positively
  attributed to recovery's `get_args`, that boot traversed `post-fs`, contradicting
  a permanent earlier init-action stall. It would still not prove the diagnostic
  children executed successfully. The writer of the earlier recurring BCB is
  unknown, and those earlier boots do not establish Test 16's execution point.
- Conditional local fallback preparation: move only diagnostic startup earlier,
  retain kernel/USB behavior, and use unique Test 17 output directories. The
  early persister cannot require the bootdevice/by-name alias created later by
  qcom `fs`; retain fixed p36 geometry and pinned UUID/type checks instead.
  Do not build/flash this fallback before inspecting Test 16 cache. Do not remove
  the USB flush speculatively: it serializes OTG work and is separate from the
  deferred-probe queue bypassed by earlier diagnostics. Blue LED markers are
  unsuitable because that LED was physically invisible in the working control.
- Local fallback sources are now prepared: `test17-collect.sh`,
  `test17-persist.sh`, `test17-init.rc`, and
  `prepare_test17_early_runtime_logs.py`. Default static validation passes;
  no image was built/signed/staged. The builder requires verified Test 16
  after-cache bytes, extraction, an explicit directory-absence probe and
  hash-bound reviewed absence evidence before `--build` can proceed. These
  sources remain conditional; review any actual Test 16 logs first.
- Full MacBook USB inventory confirms hub/peripherals but no phone enumeration
  at the latest check. Test 16 remains installed; no programmer load, storage
  write or reset occurred during this research round.

## 34. Test 16 runtime logs recovered (October 16)

- Owner returned phone to EDL; pinned programmer loaded once. Complete
  read-only cache-after capture verified on both Macs, 1,718,616,064 bytes,
  SHA `4fc33cbd0de698b47c930eb84a83c4d7b91645dec0f4ca19b961f88881f965f7`.
  Private evidence `hardware-tests/test16-cache-after` and
  `test16-cache-extracted-after`. Extracted 24 files; all 19 diagnostic manifest
  checks pass, no manifest errors. Collector and COMPLETE records are present.
  Existing recovery/log and last_log are still the old reader logs.
- **Userspace is proven.** TWRP 3.7 and adbd execute. PID1 is in `epoll_wait`
  in all three snapshots: the proposed pre-post-fs init mode-write stall did
  not occur here. Do not build the conditional Test 17 earlier-logger fallback.
- FunctionFS ep0/ep1/ep2 and the adb function link exist, but every snapshot
  lacks a UDC and mode attribute; binding reports `No such device`. One stack
  captures deferred_probe_work_func → dwc3_msm_probe+0xca4 →
  of_platform_depopulate → usb_bam_remove → notifier unregister/RCU wait.
  USB probe is unwinding/retrying. k_sm_usb rescuer thread counts grow
  2 → 149 → 385 across the three snapshots; diagnose the probe's failing
  dependency and per-attempt resource leak, not the previously suspected flush.
- Repeated Pericom Type-C I2C NACKs at 7-003d (-107) and audio deferrals appear
  alongside the USB retry storm. Their causal relationship needs source/binary
  verification; do not disable hardware based only on adjacent log lines.
- Display separately reports byte0/pclk0 RCG update warnings, DSI command
  failures and frame timeouts. Recovery initially waits in mdss_fb_pan_idle,
  then reaches crypto preparation and fails keymaster setup (QSEE remains
  deliberately disabled in this diagnostic). No userdata format/write.
- Phone remains in EDL with programmer loaded; Test 16 boot remains installed.
  No storage writes/reset during capture. Next candidate must address the
  demonstrated runtime failure and retain independent logging with unique
  output names. Preserve all captured evidence and do not reuse Test 16 paths.

## 35. Test 17 USB supplier diagnostic (October 16)

- Test 16's ssusb `extcon` phandles 0x159/0x165 point solely at the Pericom
  Type-C node. The absent controller NACKs; its driver defers before publishing
  an extcon supplier, so DWC3 repeatedly unwinds its populated children. Working
  Test 06 instead detects TI at 7-0067; the initial DBM ordering defer appears
  in that working baseline too. Shipped 4.4 TI compatible/supply expectations
  do not match its DT node, and the driver provides no extcon API.
- **Do not delete the ssusb extcon property.** Exact binary review found that
  doing so enables an implicit host-only / ID-GROUND fallback. Test 17 retains
  the property but changes its four-byte value to zero: phandle lookup returns
  -ENODEV (explicitly accepted); neither notifier is registered, NULL reads are
  guarded, and property presence prevents host fallback. Existing `mode
  peripheral` writes set VBUS-present/ID-FLOAT. This is a controlled manual
  peripheral diagnostic, not a production TI role-detection implementation.
- Built `test-17-usb-supplier-boot-adb-only.img`, 26,182,707 bytes, SHA
  `e122e26f40da384a96594cb4826ca5f29fb5c07991d690f12266400c9d4f35af`.
  Both DTs differ only in that property value. Compressed/raw kernel, cmdline,
  header load addresses, second component, USB actions and charger path are
  exact to Test 16. DT reservations and 8 KiB slack remain. Keep temporary
  kernel bypasses for this first controlled USB test.
- Diagnostic startup remains post-fs. New `/axon-diag-test17` output avoids
  overwriting Test 16. Collector now prioritizes PID1/recovery/adbd, then scans
  at most 512 process directories in digit-length order, at most 96 threads.
  This fixes Test 16's worker-storm crowding of service stacks. Original time,
  output, mount, geometry, UUID and no-clobber bounds remain. Independent source
  and final artifact reviews pass; signature and boot ID verify.
- Earlier `prepare_test17_early_runtime_logs.py` and `test17-{collect,persist}`
  are retired conditional fallback sources and were never built/flashed. Active
  builder is `prepare_test17_usb_supplier.py`, scripts `test17-usb-*.sh`, runner
  `run_test17_usb.py`, reset `reset_test17_usb.py`, plans `test17-usb-supplier-*`.
- Padded SHA `84a7144f37e4d3bad66704f78969ec6fe4f909c728b49f07e243531993ed54c8`.
  Required full boot before `5a3569ca898ef91fe742b663e190d200a4ac3df9a6385a5b081e837d97666783`.
  Expected full boot after `4c7fb194e1ae769da5b668a9bbb6d17d0f8eda5eedee1e952247ba9fa35f237c`.
  Write gate requires verified Test 16 cache-after backup and rehashes it.
  Files-only preflight passes on both Macs; fresh full before audit underway.
  Programmer remains loaded from the cache capture; do not reload it.
- Display follow-up: first-frame RCG/DSI failures may be affected by retained
  clock handoff votes and skipped clock_late_init. Once USB probe completes,
  restore genuine deferred synchronization and cleanup coherently before
  changing panel timings. Later MDSS D-state idle waits are not themselves
  evidence of a deadlock. Recovery's decrypt helper has a bounded 30-second
  parent wait; snapshots ended around that window, so permanent crypto hang
  is unproven. Never fake a successful decryption property.
- **Test 17 is written and fully verified on both Macs.** Initial before
  audit again found the exact 22-byte BCB pattern, otherwise unchanged Test 16
  boot/recovery/GPT. Full pre-clear evidence preserved on both Macs; identical
  guarded one-sector clear code (only evidence paths changed) restored original
  zero misc with full readback verified. Fresh full before audit then passed.
  Boot program ACKed; prefix and separate full 64 MiB after readbacks match
  the pinned hashes above, preserving boot tail. Recovery/GPT unchanged and
  misc zero. Evidence `test17-usb-supplier-*` and `test17-clear-bcb`.
  Two-Mac receipt returned before the separate guarded reset invocation.
- Read-only fallback cache retrieval is prepared/staged:
  `backup_test17_cache_after.py`, `run_test17_cache_after.py`,
  `extract_test17_cache_diagnostics.py`. It pins UUID to the verified Test 16
  cache-after backup; no capture yet. Prefer staged live adb capture
  `capture_test17_adb.py` if connected. Keep Test 16 logs intact.

## 36. Test 17 live adb breakthrough (October 16)

- One guarded reset sent after full verification; USB disconnected before ACK,
  EDL disappeared. No adb during the first 40 seconds. A later check found
  `recovery` transport. Host detection time was not recorded precisely. Persisted kernel logs now
  establish USB CONNECTED at 6.176 s and CONFIGURED at 7.933 s; do not describe
  this as a minutes-long kernel USB startup delay.
- Live identity confirms **kernel 4.4.302-fujisan+, TWRP
  3.7.0_9-Android8_Anya1014**, USB state `adb`, and absence of the 3.18 recovery
  slot marker. Runtime `/proc/device-tree/soc/ssusb@6a00000/extcon` is exactly
  four zero bytes. This is the new image running, not a fallback to the reader.
- Live USB mode is peripheral, UDC `6a00000.dwc3` is bound/configured at high
  speed. Only two k_sm_usb rows remain in the live process dump, versus 385 in
  Test 16's last snapshot. The null-supplier diagnostic opens working adb.
- Both-Mac-verified evidence: `hardware-tests/test17-usb-supplier-live-v2`,
  with `local-verification.json`. Its cache diagnostic archive was safely
  unpacked by fixed filename/type/size allowlist; all 19 manifest hashes pass.
  Earlier `test17-usb-supplier-live` is preserved: its dmesg worked, but compound
  commands were overquoted and produced 'not found'. Corrected v2 removes the
  extra shlex.quote around argv's `sh -c` argument; benign two-command probe
  verified behavior before capture. Do not trust first capture's compound files.
- Recovery's live log reaches the decrypt UI and later dims/blanks brightness.
  Persistent first-frame byte0/pclk0 RCG and DSI command/frame failures remain;
  successful userspace/adb is not proof of visible working UI. Owner's actual
  screen/LED report is pending. Stock encrypted data remains untouched.
- Mounted debugfs in RAM through live adb to collect clock state, without
  changing clock controls. Evidence `hardware-tests/test17-clock-state` verified
  against the MacBook manifest. Legacy `enabled_clocks` is available; this
  kernel lacks `devices_deferred` and `clk_summary` even after debugfs mount.
  DSI/byte/pixel software clock holds remain, consistent with retained handoff
  votes. Next investigate coherent restoration of genuine deferred waits and
  late cleanup before changing panel timings. Keep this adb connection alive;
  no second boot-image change or reboot has been made.

- Independent live-log review confirms k_sm_usb remains exactly two across all
  three snapshots and the later live capture. Recovery reports the bounded
  decrypt timeout, selects its decrypt page, then dims brightness 5 → 0.
  This explains software blanking but does not establish physical display output.
- Additional read-only resource capture `hardware-tests/test17-display-state`
  is verified on both Macs. Both framebuffer nodes report 1080×1920, 32 bpp;
  the separate fujisan_display diagnostic remains idle with seq=0 (not used by
  TWRP, so last_error=0 is not evidence that TWRP rendered successfully).
  Regulator summary and enabled_clocks are saved before any next image change.
  No debug clock, regulator, panel or framebuffer controls were changed.
- Planned next controlled test restores seven original kernel sites: preflush
  argument load, both genuine deferred flushes, free_initmem, and the three
  late cleanup pointers. Exactly 23 raw bytes change. Preserve the pre-enable
  calibration pulse and after-async marker; both finish before free_initmem.
  Remove the earlier preflush green hook so green after the calibration pulse
  is not mistaken for the later checkpoint. This tests cleanup restoration;
  it is not yet a proven display fix. Test17 remains running via adb.


## 37. Test 18 coherent cleanup candidate (October 16)

- Local builder `prepare_test18_cleanup.py` creates immutable
  `test-18-cleanup-boot-adb-only.img` from exact Test17. Seven original sites
  are restored: raw offsets 0x5fecd0, 0x5fecd4, 0x5fed98, 0xfc453c,
  0x174d398, 0x174d3a0, 0x174d3a8. Exactly 23 raw bytes differ; resulting raw
  SHA `66833e48a3ae42833801f8919ac65bccf6211274671d5a58b0d7f1e7ad81cc41`.
- This restores both genuine deferred workqueue waits, init-memory release,
  regulator_init_complete, regulator_proxy_consumer_remove_all and
  clock_late_init. Removing the preflush green hook restores its original
  workqueue argument load. Remaining helper branches are the pre-enable pulse
  and after-async marker, both completed before the restored free_initmem.
  The synchronous LED helper installs no new deferred callback into that memory.
- Device-tree tail is byte-exact to Test17. Ramdisk changes only the three
  diagnostic entries' Test17/test17 names to Test18/test18; unique output
  `/axon-diag-test18`. USB activation, MTP-disabled defaults, charger startup,
  logger timing and cache identity guards stay unchanged.
- Image is 26,182,707 bytes, SHA
  `f9924f43f50689bb05982897f4410a4039f22284b068735fbf642b5592dcb9ba`.
  Padded SHA `838d57535f222d8d938e0e81106960225daed7e4fd745403ff9722861224c46b`.
  Full boot before must be current verified Test17:
  `4c7fb194e1ae769da5b668a9bbb6d17d0f8eda5eedee1e952247ba9fa35f237c`.
  Expected full boot after, preserving its tail:
  `1af22309c02a580d8ffcc27dc568533de13e379ae17fec507885026b441402ff`.
- Signature/boot ID, exact byte scope, CPIO metadata/entries, shell syntax,
  non-overwrite guard and files-only local preflight pass. Test18 has not been
  flashed; Test17 remains live via adb. Cleanup remains a hypothesis for the
  display failure, and can expose another probe or an unvoted resource.
- Prepared harness: `run_test18_cleanup.py`, `reset_test18_cleanup.py`,
  `clear_test18_bcb.py`, `test18-cleanup-{local,remote}-plan.json`, EDL spec
  `test18-cleanup-independent-audit.json`. Every runner stage requires a passing
  separate `test18-cleanup-independent-review.json` tied to the image hash.
  Do not reload a programmer unless a new EDL session is confirmed. Always
  retain fresh before/after full audits, full two-Mac verification and separate
  one-shot reset. BCB clear is conditional on the exact backed-up 22-byte pattern.
- `capture_test18_adb.py` is prepared for bounded read-only capture to unique
  `test18-cleanup-live-v1` if the next boot reaches adb. No software reboot of
  the known-problematic 4.4 restart path; the owner handles physical reentry.

- **Final Test18 independent review passes**, including exact raw/DT/ramdisk
  scope, full initcall table, original restored bytes, helper lifetime and
  harness gates. Candidate and capture/BCB/reset scripts are staged on the
  MacBook; files-only preflight passes on both Macs. Test18 is NOT flashed.
  Phone remains Test17 in adb recovery, programmer not loaded. On the next
  owner EDL entry, use the prepared reviewed workflow without repeating
  permission questions. LED green after OFF/ON/OFF indicates restored initcalls,
  cleanup and async returned, but precedes free_initmem and proves neither
  userspace nor visible rendering; use actual logs and owner observations.

- Before concluding staging, adb disappeared. Fresh MacBook USB inventory
  confirms one QUSB__BULK 05c6:9008 EDL device. Cause of mode transition is
  unreported; do not infer a manual restart or kernel crash. Proceed with
  the validated Test18 workflow and fresh partition audit.

- **Test18 is flashed and fully verified on both Macs.** Fresh full before
  capture matched Test17 boot/recovery/GPT, with only the exact recurring BCB
  pattern. Backed up that full audit on both Macs, cleared the single BCB
  sector once, verified all 1 MiB of misc and exactly 22 changed bytes, and
  repeated a passing fresh before audit. Test18 boot program ACKed; both
  prefix and separate full64 MiB after readbacks match the pinned hashes,
  preserving the boot tail. Recovery/GPT unchanged and misc zero before boot.
  Local receipt was returned to the MacBook before a single guarded reset.
  Evidence `test18-cleanup-*` and `test18-clear-bcb`; no automatic write retry.


## 38. Test18 working 4.4 recovery baseline (October16)

- One guarded reset was sent after full two-Mac verification. USB disconnected
  before ACK; no retry. Host saw adb recovery24.7seconds after reset. Owner
  initially saw TeamWin splash, then confirmed it progresses into TWRP.
- Verified live captures `hardware-tests/test18-cleanup-live-v1` match their
  MacBook manifest. Fixed-allowlist archive extraction verifies all19 persisted
  diagnostic hashes and COMPLETE.txt. Runtime extcon remains four zero bytes.
- Cleanup now executes: regulator proxy cleanup5.451458s,
  clock_late_init5.451803s, free_initmem releases640KiB at5.454862s.
  Full dmesg captures contain no RCG-update warnings, DSI DMA failures or
  frame timeouts, unlike Test17. Owner-visible UI corroborates that difference.
  Do not carry Test13's deferred/cleanup bypasses into later candidates.
- USB configures at11.081s kernel time; live modeperipheral, UDC high-speed,
  two k_sm_usb threads across snapshots. No panic/BUG/WARNING in reviewed logs.
- Decrypt still waits for its bounded timeout and selects the decrypt page,
  consistent with the retained QSEE disable. Do not claim stock-data decrypt
  works or fake success. No format, system replacement or userdata modification.
- Preserve Test18 image, raw/full boot hashes and logs as the working baseline.
  Recovery partition still contains the separately marked3.18 control; Test18
  currently runs from boot. Local LOS-recovery transfer work has begun, using
  LOS's own kernel addresses and ramdisk. No LOS candidate flashed yet.


## 39. Local LOS23 transfer preparation after Test18 (October16)

- LOS recovery source/ZIP extraction are identical, SHA
  `5d76032e77d24a364bfd733369470abd516c198e8217c590d286dc16ab527a5a`.
  Own recovered symbol map uses base **0xffffff8010080000**, unlike TWRP.
  `prepare_los23_recovery_kernel.py` validates its own exact source/raw/map,
  QSEE context and988 initcall pointers. It changes the early QSEE query at
  raw0x672ca0 from BL16efff97 to MOVN40028012 (-ENODEV) after queue initialization,
  preserving original unlock/error cleanup. Eight diagnostic blacklist names
  are validated at their own pointers. No LED cave, deferred-wait, cleanup,
  free_initmem or table patch. Not a production QSEE/GPU/radio solution.
- Module applies only own recovery DT semantic changes: 8KiB free space,
  0x9ff00000 no-map reservation, two QCE nodes disabled and present-null USB
  extcon. It returns kernel/cmdline in memory; report
  `los23-recovery-kernel-transfer.json`; no complete LOS image built yet.
  Patched raw SHA `0c14d626fcd2ea4e35895b0db4801d3b5aaf150a62806c7a90fcb4ee9a5accaa`.
- LOS ramdisk startup proposal `los-recovery-ramdisk-startup-proposal.json`
  records its593 unique entries, disabled adb policy, charger omission, early
  display waits and logger-tool differences. A dedicated port is in preparation;
  do not copy TWRP startup scripts/LD_LIBRARY_PATH blindly. Preserve stock data.
- Local-only system payload preparation is now tangible. Pinned ROM ZIP SHA
  `d9b4caca37dc906c4f9b4700bc8d24fe6fe5757e8eeba7c45fe2c55143883456`.
  `extract_los23_system.py` streamed Brotli directly into a sparse ext4 image
  using all new/zero/erase ranges, verifying ZIP CRC, range coverage, every
  written range readback, stream length, ext4 superblock and read-only fsck.
  No incremental transfer commands. Original at `los23-system-original/system.img`,
  logical6,979,321,856bytes, allocatedabout2.62GB, SHA
  `90aea590dd4921df4bd78ebcdcd6c10d93eebe27e8d70d501d8a59e7f495899d`.
- `prepare_los23_att_gpu.py` created an APFS clone and patched only mapped file
  data for verified AT&T `a530_zap` files. All five lengths match LOS; b00/b02
  already identical, mdt/elf/b01 differ. Exactly7047 bytes changed. Every other
  image byte and inode metadata/xattr is exact; each extracted file matches
  its pinned Test06 AT&T manifest; read-only fsck passes. Candidate system at
  `los23-system-att-gpu/system.img`, SHA
  `0271379d1402dc727b1c5f4a48333cf3db1f799d86370c19b5cafdecb4846f27`.
  This is local preparation ONLY, not a validated install package. Original
  ROM installer overwrites system, boot and recovery; coordinated patched
  boot/recovery and a deliberate userdata decision remain required.


## 40. Test19 LOS recovery diagnostic candidate (October16)

- `prepare_los23_recovery_ramdisk.py` ports native LOS startup/logging, using
  the published toybox's proven registered blkid applet (direct `toybox blkid`;
  no TWRP binary/library transplant). New early independent services precede
  imported display writes, remove two early display waits, explicitly enable
  adb after FunctionFS setup and trigger late-init for charger bootmode.
  Charger service is disabled so it cannot compete with recovery UI.
- Keep ro.build.type=user to avoid userdata adb-key import; all relevant
  ro.debuggable/ro.secure/ro.adb.secure defaults change for diagnostic USB adb.
  Recovery gets explicit --show_text --reason=axon-diag-test19. Fstab omits
  data/cache/persist/dcmlog; checked all rc direct mounts/execs for bypasses.
  Only the separate bounded logger mounts fixedp36 after geometry/UUID/ext4
  checks, at private/tmp/axon-cache-test19, writing a unique/axon-diag-test19.
  It does not depend on a late bootdevice/by-name alias.
- Shipped user init **ignores permissive cmdline and forces enforcing**.
  Its own ELF SetupSelinux was independently decoded: retain getenforce,
  conditional branch, setenforce call and failure handling; change desired1→0
  in CMP at0xfc078 and MOV at0xfc080. Only two bytes differ (fc079/fc080).
  Original initSHA58b17089c9ccd12f43c3b263d12b4204015bd92a14643ece08d51a69cff07d70;
  diagnostic initSHA714ecace1ad409d588f497d51c738cf0bdb0a1d23ee3029c5b976db5f0e468eb.
  This is recovery diagnostic behavior, not a production Android security fix.
- Immutable pre-enforcement CPIO preserved. Active
  `prepared/test-19-los-recovery-ramdisk-v2.cpio`,32703488bytes,
  SHAbe30850f2a904535803d21366e226a5ebcdd0358f1430829c7082d494f1b96d2.
  Five existing entries changed and two scripts added; all other encoded
  entries and existing metadata exact. Native tools/shell/CPIO checks and10
  focused offline rejection/mount-identity checks pass; only mock mounts used.
- `prepare_test19_los_recovery.py` assembles the own-kernel/own-DT transform
  and pinned v2CPIO, adds diagnostic SELinux cmdline declaration and signs/boot.
  Image `test-19-los-recovery-boot-adb-only.img`,26625075bytes,
  SHA7464779eaa501e58b9b1b78b09676786c98e154de6631f82f8d2bc8a37d1ed46.
  Padded26625536bytes/52003sectors, SHA
  280b615c87daf67f871d800d9c3d400c1f3b5c3f89cc99ce700a14251f4687f7.
  Expected full boot before is Test18
  1af22309c02a580d8ffcc27dc568533de13e379ae17fec507885026b441402ff;
  after preserving tail:da1ca2689b3bbb16d9783c48b1ab26809184a31f8efa650dac1cadd029f1399d.
- Local-only image preflight passes. Harness prepared:
  run_test19_los_recovery.py, reset_test19_los_recovery.py, clear_test19_bcb.py,
  test19-los-recovery-{local,remote}-plan.json and independent-audit spec.
  Every runner stage requires a separate passing image-hash-bound final review.
  `capture_test19_adb.py` uses native/system/bin and unique live capture paths.
  No LOS system/data installation or Test19 phone write has occurred.

- **Final independent Test19 image and harness review passes**; gate saved
  `test19-los-recovery-independent-review.json`. Image/reset/capture/BCB scripts
  staged on MacBook, files-only preflight passes on both Macs. Latest mode:
  adb recovery present, zero EDL devices. Test18 remains running; no Test19
  write/reset yet. At next owner EDL entry, proceed with this prepared test
  and the established fresh full audit/readback workflow. Keep the3.18 recovery
  partition control unchanged. LOS system stays local-only; data remains intact.


## 41. Test19 hardware run (October16)

- Owner explicitly returned to EDL and requested Test19 flash. Confirmed one
  05c6:9008 device on MacBook, loaded pinned programmer once. Fresh full before
  audit matches Test18 boot, marked3.18 recovery, original GPT and zero misc.
  No BCB clear was necessary or performed.
- Boot program ACKed and padded prefix readback matches
  280b615c87daf67f871d800d9c3d400c1f3b5c3f89cc99ce700a14251f4687f7.
  Separate full64MiB boot readback matches
  da1ca2689b3bbb16d9783c48b1ab26809184a31f8efa650dac1cadd029f1399d.
  Before/after backups copied locally and verified on both Macs; exact intended
  prefix and preserved tail checked. Recovery/GPT/misc unchanged. Two-Mac
  verification receipt returned before one guarded restart invocation.
  Evidence: hardware-tests/test19-los-recovery-{full-before,led,full-after}.
  This writes only the boot diagnostic; no LOS system install or data format.

- Test19 reset sent once; USB disconnected before ACK and EDL disappeared.
  No adb/EDL in initial40seconds or additional25second monitor; full MacBook
  USB inventory shows no phone. Collection window exceeds60seconds, but logger
  execution/persistence remains unproven until retrieval. Owner screen result
  requested and pending; no further restart or write.
- Read-only fallback prepared: `run_test19_cache_after.py`,
  `backup_test19_cache_after.py` (staged), `extract_test19_cache_diagnostics.py`.
  Same fixed GPT/cache geometry and two-Mac verification as prior retrievals,
  unique Test19 paths, pinned cache UUID from verified Test16 backup. At next
  EDL entry retrieve these logs before selecting another image; load programmer
  only once for that new entry. No LOS system installation or data format.


## 42. Test19 LOS recovery success and Android transfer (October16)

- Owner confirms LineageOS recovery menu boots. Subsequent MacBook check finds
  adb recovery, USB18d1:d001, no EDL. Captures at
  hardware-tests/test19-los-recovery-live-v1 verify on both Macs, including all19
  persistent log hashes, COMPLETE marker and null extcon. No fallback-cache
  EDL read is needed for these already recovered logs.
- Running kernel4.4.302-cip112-fujisan, LOS23.2-20261006-UNOFFICIAL-fujisan,
  ro.debuggable1, ro.secure0, ro.adb.secure0, SELinux Permissive, USB config/state
  adb. Task credentials confirm adbd UID0. Kernel logs show adbd6.599s,
  USB connected6.869s/configured6.876s. These are kernel-relative timestamps;
  actual host discovery occurred later and reset-to-kernel timing is unproven.
- Normal cleanup4.215–4.216s, free_initmem releases704KiB4.219s. Two k_sm_usb
  threads across snapshots; no captured RCG/DSI/frame/panic failures or deferred
  USB unwind stacks. Recovery falls back from DRM to1080×1920 framebuffer;
  owner-visible menu corroborates rendering.
- Begin local full-Android transfer using LOS boot's own DTs and ramdisk.
  GPU needs BOTH kgsl_3d_init and generic pil_tz_init: a5xx_rb_start calls
  subsystem_get for a530_zap, whose DT provider is qcom,pil-tz-generic/PAS13.
  Merely replacing GPU firmware while retaining both blacklist entries cannot
  enable graphics. Detailed scope/other generic-PIL device handling is under
  review. QSEE remains a diagnostic limitation, not a production fix.
- GPT confirms system is6,979,321,856bytes (exact prepared image size), userdata
  52,766,424,576bytes. Current free space approximately3.44GB local/96.2GB
  MacBook. Read-only compressed stock-system backup started via rooted recovery
  adb; backup_stock_system_adb.py checks fixed p20 geometry, no writable system
  mount, exact byte count, compressed readback and fresh source-partition hash.
  No userdata backup/format or full Android installation yet.


## 43. Stock-system rollback backup and full-Android audit (October16)

- Completed a read-only adb backup of stock p20 system: 6,979,321,856 bytes,
  raw SHA256 `13c66498cc6c8f5c4a32e9d813f5515d87f92e618d7619fa06f40658ee1bda9f`.
  Compressed size2,404,324,644bytes. Saved-copy decompression and a fresh
  device-partition hash agree on MacBook; copied and decompressed/hash-verified
  independently on this Mac. Local receipt returned to MacBook. Evidence in
  `.axon-m-private/hardware-tests/stock-system-adb-backup/`. No phone writes
  or resets for this backup; Test19 remains the running recovery control.
- Full boot ramdisk has24 ordered CPIO records, including two identical empty
  dev directories except inode. Parser now allows this only through explicit
  `allow_duplicate_directories={"dev"}`; preserves both encoded records and
  default strict rejection. All40 repository tests pass, including duplicate
  file/symlink, metadata/payload mismatch and third-occurrence rejection.
- Local startup audit: `.axon-m-private/los23-boot-startup-review.json`.
  Full Android adbd is an APEX override, with additional USB and charger
  actions requiring coordinated changes. Native second-stage init differs
  from recovery; enforcement behavior/patch sites remain unresolved. Never
  reuse recovery binary offsets. Software KeyMint is present, but vendor
  Gatekeeper still depends on QSEE; existing-data decryption is not proved.
- Published full startup expects plain F2FS userdata, with formattable/check
  flags. init.target.rc also directly mounts persist writable outside fstab;
  post-fs-data performs required mutations. Removing ramdisk data entries is
  not a data-preserving full-Android test. No userdata backup, formatting, or
  full Android installation occurred. Owner data decision is still pending,
  and no destructive permission has been requested or inferred.
- Prepared LOCAL-ONLY kernel/DT component:
  `.axon-m-private/prepared/los23-full-boot-kernel-diagnostic.bin`, SHA256
  `e2a3d345537c95f115ca9c1cfb20c3622e6f32c739f37801dc675ff48850ecdf`.
  Uses full boot's own DTs and reviewed four-byte QSEE diagnostic patch;
  restores kgsl_3d_init and pil_tz_init, preserving a530_zap/PAS13 provider.
  Isolates ADSP/PAS1, Venus/PAS9 and SLPI/PAS12 providers by DT status, while
  retaining other diagnostic skips. GPU/PIL behavior is hardware-UNTESTED.
  This is not a complete/signed boot image or an install-ready package.
- Next: finish own-system init/APEX adb/charger/USB/logging changes and a
  coordinated boot/system package; retain verified recovery and rollback
  copies. Before full startup, back up every additional writable partition
  (including persist/dcmlog), and settle userdata preservation/formatting
  with owner. Do not install original ZIP: it overwrites boot AND recovery.

- Full-boot component reproduced byte-for-byte by root, including command
  line and normalized validation JSON. Five focused offline checks pass:
  mutated-source rejection, reviewed-module pin rejection, deterministic
  reproduction, immutable-output rejection with unchanged files, and syntax.
  Reports: los23-full-boot-kernel-plan.json,
  los23-full-boot-kernel-offline-checks.json and
  los23-full-boot-kernel-root-review.json under the private artifacts root.
- Owner asked whether existing photos/files/app data must be preserved, to
  select the eventual backup plan. Answer pending; this question neither
  initiates nor authorizes formatting.


## 44. Test20 full-Android package prepared; NOT installed (October16)

- Owner answered **"nah"** when asked whether existing phone data needs saving.
  This settles the preservation preference. No userdata backup is requested.
  No format/install has run; a concrete clean-install approval is the final
  pending step after installer review. Phone remains Test19 LOS recovery/adb.
- Three additional full-Android payload sets are prepared and reviewed locally:
  own system-init permissive patch (two bytes; distinct native binary), three
  property-byte changes plus duplicate adb-auth consistency;12 same-size USB
  and charger rc replacements; and3 new bounded diagnostic files. Signed adb
  APEX and policy remain unchanged. Six security helper tests,12 adb checks,
  16 USB checks and14 logger mocks passed. Diagnostic settings are temporary.
- Full Android USB retains a single FunctionFS-ready adb bind and explicit
  peripheral mode; no MTP/composite binds. USB HAL/usbd/legacy composition
  controllers are disabled for this fixed-role diagnostic. Charger enters
  normal late-init. **Adb may wait behind APEX/KeyMint/ART/odsign/zygote** because
  property-trigger actions queue; do not claim immediate adb after APEX.
- Early logger services start directly after first perform_apex_config, using
  native tools and RAM /dev/axon-diag-test20.28 bounded jobs sample nominal
  0/15/45/120seconds. Persister verifies p36 geometry/device/ext4/UUID and the
  existing /cache mount before creating exclusive /cache/axon-diag-test20.
  It never mounts/formats. First-stage cache mount is retained; no retry/reuse
  of old diagnostic directories. Independent mock/source review passed.
- `test20-system-v1/system.img`:6,979,321,856bytes, SHA256
  `7c32f735219768f31444400c67cf996b5f80de4c17d0d1c1ed65a7d0acf0883a`.
  Sixteen existing files changed with same-size data-block patches, preserving
  every existing inode/xattr/block mapping. Three new logger files have explicit
  root ownership,0644 mode and system_file SELinux labels. Read-only e2fsck and
  independent content/metadata review passed. All4 vendor-fstab formattable
  flags removed: formatting must be explicit, never an automatic mount fallback.
- `test20-boot-v1/boot.img`:13,976,627bytes, SHA256
  `0651435c4575980f2a851bb1f47d59f4a72a1bb56ccebd56904886e8282991b6`.
  Own full-boot kernel/DT component as section43, GPU/PIL reenabled with scoped
  other-provider disables. First-stage ramdisk changes only two formattable
  flags; original init and every other ordered CPIO record remain exact,
  including duplicate dev entries. Signature /boot and boot ID verified.
- `test20-boot-v1/recovery-control.img`:26,625,079bytes, SHA256
  `1a0c052cbc5561c50bd4dc9fde6d36573bda8beb04e5b5574e04c8a5fe9f6a9f`.
  Byte-identical working Test19 payload, re-signed for /recovery with same
  local certificate. Proven payload in boot slot; recovery-slot selection is
  still untested. Retain prior3.18 control backups and Test18 TWRP fallback.
- All three images staged on MacBook under session-20261016-003529/
  test20-package-v1, exact hashes checked there; system streaming and saved
  sparse-copy readback both verified. No phone partition writes from staging.
- Fresh stock persist33,554,432bytes and dcmlog104,857,600bytes backups verified
  against saved gzip and fresh source hashes, copied/verified on both Macs.
  Evidence hardware-tests/android-aux-adb-backup. Fresh boot/recovery/misc/GPT
  snapshot at hardware-tests/test20-before-adb verified both Macs; all original
  system/persist/dcmlog hashes still match, misc remains entirely zero.
- Scratch-only formatter test used a256MiB file on recovery tmpfs, **not /data**
  and not a phone partition. Native make_f2fs -t0 -r -T0 produced feature0 F2FS;
  this4.4 kernel mounted/read/wrote it, and dry-run fsck passed. Loop autocleared
  on unmount; scratch file/directory removed. Evidence test20-f2fs-ram-check-v2.
- Raw adb exec-in worked for direct dd but FAILED both piped gzip transfer
  probes (zero-byte RAM output). Do not use exec-in for installation pipelines.
  `adb shell -T sh /tmp/helper.sh` with gzip|dd/fsync passed a1MiB exact binary
  RAM readback. All probe files removed; no partition was written.
- Guarded `install_test20_adb.py` defaults to read-only preflight. MacBook
  preflight passed image hashes and exact partition geometry; authorization
  absent. Writes require a separate package-bound explicit approval receipt.
  Order: recovery control → system → explicit plain-F2FS userdata format →
  boot → final verification. No misc/GPT/bootloader/foreign firmware changes.
  Boot/recovery full64MiB host readbacks preserve untouched tails; system full
  native SHA readback; F2FS format uses dry-run fsck and mirrored geometry-checked
  superblock readbacks, not a precomputed whole-userdata image hash. Durable
  started-phase journal prevents automatic retry after an interrupted write.
  Host and remote deadlines bound attempts, but kernel D-state I/O may outlive
  cancellation. No automatic software reset; known4.4 restart limitation remains.
- Install plan: `.axon-m-private/test20-install-plan.json`. Before owner restart,
  retrieve and verify final host readbacks/state locally and return the receipt.
  Userdata compatibility is no longer a migration target; this is a first clean
  Android diagnostic with GPU runtime and several hardware services still
  unproved. Do not describe it as a production-ready ROM.

- **Final installer review passed**, exact script SHA256
  `c6ad97577eeb0b8e7d090e603132bbed97c3ee30376ee58ea1733d5e014de7ec`.
 24 local gate/framing checks plus mismatched-journal rejection passed.
  Same script passed read-only MacBook preflight. All preparation is complete;
  explicit package+userdata-format approval is pending. No authorization.json
  exists, no installer write stage ran, and Test19 recovery remains running.


## 45. Test20 clean install authorized (October16)

- Owner explicitly answered **"yes"** to the concrete Test20 clean-install
  question covering boot/recovery/system flashing and userdata erasure.
  Approval recorded in private test20-owner-authorization.json, bound to exact
  reviewed images, p48 geometry and installer SHA. Do not ask again for this
  approved operation. Run stages serially and never retry an interrupted phase
  without reviewing its journal and actual partition contents.
- Fresh read-only preflight passed. Recovery partition has been written and
  full64MiB readback independently verified on both Macs, including the exact
  new image and preserved tail. Full recovery SHA256
  `f5bb5bf5d70ab1e44fd5ac9d888270e219f527d21a67796cf683cef5521ecb35`.
  System full native readback matches the prepared image. Userdata was
  explicitly formatted F2FS; dry-run fsck, mirrored superblocks and repeated
  metadata readback passed. Boot write and full host readback also passed.
  Final rechecks are running; Test19 remains running in RAM, no reset yet.


## 46. Test20 installed and verified; first Android boot pending (October16)

- Explicit owner-approved stages completed serially: recovery, system, userdata,
  boot, final. No retries, software reboot, EDL or programmer operation.
- Boot and recovery full64MiB native/host readbacks match exact padded images
  plus preserved original tails. System full native hash matches Test20.
  Boot full SHA256 `4434306a5c58d4de5ee018a59a04ae3f551d7073efae1fe7a07bd07e468a17d6`.
  Recovery full SHA256 `f5bb5bf5d70ab1e44fd5ac9d888270e219f527d21a67796cf683cef5521ecb35`.
- Userdata p48 explicitly formatted plain feature0 F2FS; native dry-run fsck,
  mirrored superblock geometry and repeated8KiB readback passed. Stock userdata
  is no longer preserved. GPT/misc/persist/dcmlog final checks remain unchanged.
- Evidence at private hardware-tests/test20-install: final state, write logs,
  full boot/recovery readbacks, userdata headers and local-verification.json.
  Both-Mac checks pass; local receipt copied back and SHA-verified on MacBook.
- Test19 recovery is still running in RAM. Next is owner physical Power-key
  restart into normal boot, USB attached. Do not use the unreliable4.4 software
  restart path. Allow at least150seconds for Test20 logger; first Android boot
  may take longer. Collect read-only adb/log evidence if available. No full
  Android success, GPU success or screen result is claimed before observation.
- Read-only `capture_test20_adb.py` is staged and hash-verified on MacBook.
  Local framing/identity/cap checks and a live printf-only transport probe pass.
  It rejects recovery, requires exact Test20 identities, and bounds capture to
  240seconds with fixed diagnostic filenames. No full capture has run; use
  its unique test20-full-android-live-v1 output only after Android adb appears.


## 47. Test20 Android animation and Gatekeeper blocker (October16)

- Owner reports Lineage loading animation. MacBook sees root adb device, own
  LOS23.2 kernel/init identities. At487seconds uptime boot_completed is unset.
  APEX ready, odsign key/verification done, SurfaceFlinger and both zygotes run.
- Verified all13 captured files on both Macs, private evidence
  hardware-tests/test20-full-android-live-v1. RAM archive contains30 checked
  members; cache archive contains none. SurfaceFlinger reports Qualcomm
  Adreno530 OpenGL ES3.2 V@269.0 with actual display/layer state.
- Concrete blocker: Qualcomm gatekeeper.msm8996 fails opening /dev/qseecom,
  aborting HIDL gatekeeper HAL. Native gatekeeperd waits indefinitely for HAL
  registration. BiometricService then throws Gatekeeper service not available,
  repeatedly killing system_server. Waiting alone cannot resolve this loop.
- Additional live inventory/hashes captured and verified both Macs under
  test20-gatekeeper-live-v1. Original gatekeeperd44800B SHA256
  `a4ecd5222e7e935057a867f97b2a425c90fa5a1fd7576207d212ee0c20238c94`
  backed up both Macs under test21-gatekeeper-before-live. No corrective
  phone change yet; diagnostic constructor patch is under independent review.
- Original gatekeeperd metadata root:shell0755, gatekeeperd_exec SELinux label.
  PID1, adb shell and current gatekeeperd share mount namespace, /dev is tmpfs.
  Preserve executable label before any diagnostic bind mount; init still
  checks domain transitions even in permissive mode. Both service rc files
  have no critical/reboot flags. No phone/zygote software reset planned.
- Cache logger race: persister starts7.462s, while actual cache mount completes
  8.563676s. Its one-shot mount gate runs too early. RAM logs survived; fix
  future persistence timing while preserving strict cache identity checks.


## 48. Test21 runtime Gatekeeper fix; next GPU-statistics abort (October16)

- Reviewed one-instruction gatekeeperd patch applied as a temporary tmpfs bind,
  preserving uid0/gid2000/mode0755/gatekeeperd_exec label. Target system image
  was not modified. Original binary backed up and verified on both Macs.
  File0x4678 changes CBNZ to B0x4754; output SHA256
  `6ad0a440825550c3f5ec504bf438cabcbbb987cf581f088cb939d52164deb5f6`.
  Native null-HAL enrollment/verification errors and permission checks remain.
  This supplies no software credentials, PIN/password or authenticated keys.
- Single apply stopped gatekeeperd and crashing vendor.gatekeeper-1-0, bound
  /dev/axon-test21-gatekeeper/gatekeeperd over /system/bin/gatekeeperd, then
  started only gatekeeperd. Namespace/mount ownership/hash/metadata checked.
  New PID10554 executes exact patch and framework Gatekeeper binder is found.
  Vendor HAL remains stopped; no phone/zygote restart or partition write sent.
- Four samples over30seconds prove Gatekeeper stable, but system_server keeps
  restarting. Dedicated crash buffer shows new SIGABRT in libmeminfo
  BpfMapRO::abortOnMismatch, called from ReadProcessGpuUsageKb, JNI Debug GPU
  memory query and AppProfiler.reportMemUsage. Rendering remains distinct.
  Binary audit locates abort on invalid map fd before native error handling;
  scoped native failure-path patch is in local preparation.
- All trial state/mount records,13 after-capture files and3 dedicated crash
  logs verified on both Macs under hardware-tests/test21-gatekeeper-live,
  test21-gatekeeper-after-live and test21-gatekeeper-crashes. Original Test20
  system/boot remain installed. Temporary Gatekeeper overlay disappears on
  restart; do not assume it persists across a disconnect without live checks.
- Latest USB: adb empty and MacBook inventory contains no Android or EDL.
  No restart was sent; cause unknown. Owner screen/connection observation is
  pending. Planned live libmeminfo backup aborted at no-device guard before
  directory creation or any phone operation. Continue preparation locally.


## 49. Test22 system prepared and staged; phone connection pending (October16)

- Native libmeminfo149304B source SHA256
  `c818331ef3c3ee086fd832a3f06c2039259d16023f17bd7e2dba4d8bf677e64d`.
  ReadProcessGpuUsageKb BL at0x1419c becomes B0x141fc to its original false
  result/fd-cleanup path. Output SHA256
  `040e0c8f97434b8d101914901f55b346c4b27eee8dc82b43f2a766258245a028`.
  Exact JNI maps false to Java-1 and framework skips optional GPU statistics.
  Generic BPF checks, rendering and separate ReadPerProcessGpuMem remain exact.
  Underlying BPF map failure errno/cause is not established; runtime untested.
- Seven same-size file-data changes from exact Test20 system: reviewed native
  Gatekeeper and libmeminfo patches; vendor Gatekeeper rc disabled with lazy
  interface removed; four logger files retain physical filenames/inodes but
  use Test22 services/RAM/cache identities. Collector remains early; persister
  starts first in main post-fs, after cache mount and before vdc checkpoint IPC.
  Existing bounded job/identity/UUID/filesystem checks remain unchanged.
- Test22 system image6979321856B SHA256
  `508cd08359c6602c36d1bf0a2711dc064bfae509b5773b55933d68ad1f2570a8`.
  Private test22-system-v1. Full outside-patch byte comparison, all inode
  metadata/xattrs/extents/content checks, read-only e2fsck and source rehash
  passed. Independent final seven-file/image-hash review passed. Individual
  native patches and logger/service payloads have separate pinned reviews.
- MacBook test22-package-v1/system.img staged via13 verified changed blocks
  in an APFS clone of its Test20 system. Full saved-image hash matches; Test20
  source rehash unchanged. Receipt test22-staging-verification.json copied
  locally. No phone operation or flash for this staging. Read-only Test22
  collector is staged, not run; physical script filenames remain Test20.
- New plan test22-install-plan.json is SYSTEM-ONLY, preserving current
  Test20 boot/recovery and userdata. No repeat formatting. Do not reuse the
  Test20 clean-install runner: prepare a fresh guarded system-only runner
  after connection/mode and current partition audit. Back up/check actual
  boot/recovery/GPT/misc on both Macs and verify every system write.
- Latest MacBook adb/USB has no phone. Owner connection/screen question is
  pending; no cause/reboot inferred and no software reset sent. Test22 has
  NOT been hardware-tested or flashed. Gatekeeper workaround does not supply
  PIN/password/biometric credentials; optional GPU accounting stays unavailable.


## 50. Test22 EDL repair and recovery-entry investigation (October16, in progress)

Owner reports menu recovery loops and normal Android remains at Lineage animation;
owner manually returned to EDL. Fresh MacBook USB05c6:9008 was verified, and the
known eMMC programmer was loaded once in RAM. Root is the sole device operator.

Fresh full GPT/boot/recovery/misc and system reads are saved privately in
`hardware-tests/test22-edl-before` and the matching MacBook session directory.
All five backups were verified on both Macs before writing. The full live
system matches exact Test20 SHA `7c32f735219768f31444400c67cf996b5f80de4c17d0d1c1ed65a7d0acf0883a`.
Boot/recovery match section49 expected full hashes: neither image was corrupted.
Misc SHA is now `07e3021342d8a12056e9faf36ade8832e1d24e8daaa6930516da3ed88412183e`;
its first2KiB are zero, with only10 nonzero bytes at offsets32896/32960. There is
no stuck BCB command. Preserve those unrelated bytes.

A new fixed system-only runner `run_test22_edl_system.py` writes exactly13 pinned
4096-byte blocks. Runner SHA `8f0231674bc620b550e8baf024661a6f5218b3b34d9b486ff3218f3492c28d1e`.
Eight mocked tests plus root independent source review passed. All13 actual
writes and immediate readbacks passed; **full-system after readback is still
running at this note's initial creation**. No reset, userdata format, recovery,
boot, bootloader or misc write has been performed in this repair round yet.
Do not infer full installation success until the transaction and both-Mac
receipt are complete. Private log: `test22-edl-write.log`.

Independent exact-aboot disassembly found the same recovery flag selects the
GPT recovery partition and `/recovery` signature target. Unlock bypass is common
to boot/recovery; no separate recovery certificate gate was found. The menu uses
a PMIC reboot reason; a `boot-recovery` BCB command independently sets recovery
selection before the common loader. Aboot does not clear that command. Exact
Test19 recovery's FinishRecovery clears the first2048 BCB bytes before showing
the menu, preserving the unrelated offsets above. Cause of menu return remains
unproved. A separate bounded BCB menu-only test and matching EDL clear operation
are being prepared; no such test has been executed yet. Never leave a failed
recovery selection forced indefinitely; preserve a verified clear path.


**Test22 installation now complete:** the full6979321856-byte live system
readback matches `508cd08359c6602c36d1bf0a2711dc064bfae509b5773b55933d68ad1f2570a8`.
Full GPT/boot/recovery/misc after-readbacks match the fresh before capture.
All block readbacks, full-system and protected-partition evidence are verified
on both Macs, and the receipt is returned to the MacBook. No reboot yet.
Test22 runtime remains untested. The full local system backup/readback copies
use APFS clones of byte-identical prepared images, separately rehashed against
the full live EDL captures; this avoids transferring identical multi-GB data
and preserves local free space. This does not substitute for the actual full
phone read, which was completed before each receipt.


**BCB recovery-entry trial has now been executed:** explicit `boot-recovery`
plus `recovery\n--show_text\n` changes exactly34 bytes in misc's first512-byte
sector. Full misc target SHA
`155bf281f1d80e27de1cd3e801586a4d3927118370931f0bca01fd977905a039`;
full GPT/boot/recovery remained unchanged. Before/after evidence and returned
receipt are verified on both Macs (`test22-recovery-bcb-setup`). Separate reset
passed its fresh GPT/misc gate and was sent once; USB disconnected before ACK,
as with prior successful tests. **Do not repeat reset or reload a programmer
unless a fresh EDL entry is actually observed.** Runtime recovery/BCB auto-clear
is awaiting observation. If it fails before recovery can clear BCB, use the
reviewed `run_test22_recovery_bcb.py --mode clear --execute` after fresh EDL and
load; this restores exact misc baseline with full protected readbacks. Do not
leave the forced request set during an unsuccessful recovery attempt.


**Recovery entry succeeded.** After the single verified BCB reset, adb returned
in recovery state at16.4s. Both native recovery processes match exact Test19
executable SHA `492b14d1ef9d3f269716465d4d492689e6a41df018f86e4efac139bf34bee220`;
bootmode and cmdline report recovery. Full boot still matches Test20, proving
this is the actual recovery slot. Recovery automatically restored the complete
1MiB misc partition to baselineSHA `07e3021342d8a12056e9faf36ade8832e1d24e8daaa6930516da3ed88412183e`.
Full live misc bytes, unchanged boot, fixed geometry, recovery identity before/
after, and F2FS metadata observations are saved in
`hardware-tests/test22-recovery-bcb-capture-v3`, verified on both Macs with a
returned receipt. This establishes a working direct-BCB recovery route; it does
not establish that the bootloader menu's PMIC reboot-reason route is repaired.

Capture-v1 stopped safely because it assumed only one recovery PID; this native
recovery has two processes with the same executable. Independently reviewed v2
accepts1–8 matching stable PIDs, but stopped on another overstrict guard: this
recovery exposes the correct fixed mmcblk partition nodes/sysfs geometry but no
`/dev/block/bootdevice/by-name` alias. Root's read-only v3 permits an absent alias
while checking it if present; exact block type/start/count/dev/size checks and
all running-image/full-boot/BCB checks remain. V3 completed successfully. Failed
captures and original scripts are preserved, not rewritten as successes.

The owner has been asked to physically hold Power until restart, then choose
Start if needed, to test full Android. Do not send the known-hanging4.4 software
reboot. BCB is clear and no EDL rollback is needed. Root is watching adb; Android
Test22 must still be checked for sys.boot_completed, stable system_server PID,
Gatekeeper binder, exact patch hashes and dedicated crash-buffer logs. The
staged read-only `capture_test22_android_supplement.py` provides60s stability
observations and specific crash/framework buffers alongside the main capture.

## 51. Test22 black screen diagnosed; Test23 installed (October16)

Owner reports the Lineage animation completes, followed by a black screen.
Root captured exact Test22 Android identities and patched native hashes over
MacBook ADB. Gatekeeper binder is present; the cache timing repair also works
(32 archived members, alongside30 RAM members). Boot completion remains unset.
A60-second stable system_server observation was insufficient: the dedicated
event buffer and watchdog dump prove subsequent framework restarts.

The decisive evidence is saved and hash-verified on both Macs under
`hardware-tests/test22-black-screen-stacks-v1`. In watchdog ANR, android.display
blocks in CompletableFuture.join → UsbService.Lifecycle.onBootPhase →
ActivityManagerService.finishBooting → bootAnimationComplete. The USB init
worker waits in IUsb.getService → UsbPortHidl.isServicePresent →
UsbPortHalInstance → UsbPortManager → UsbService. The Test20 diagnostic had
disabled vendor.usb-hal-1-0 and removed its init interface line, but retained
its VINTF declaration. This causes service discovery to wait indefinitely.
User0 BOOTING, locked CE state and Settings FallbackHome are downstream evidence;
do not wipe data or invent an unlock/launcher workaround for this stack.

Test23 restores only the exact published175-byte file
`/vendor/etc/init/android.hardware.usb@1.0-service.rc`, restoring the interface
line and removing disabled. Original/restored SHA256
`77b3cb1253f3c113cc783d298a1e2dd603f14bc56fbe280f8f7b51aa1de37c9f`;
Test22 diagnostic file SHA256
`386ee38f0e558cefe689dba87a513d311380d98906a279d2775ec0773987db92`.
There are89 changed bytes in one4096-byte system block at offset2215178240.
Full Test23 system6979321856B SHA256
`33db1d4d4e5e49f5dc1c06cbd6a0e39b07fd9b6d886941e33f165b7876fccc5a`.
Local `test23-system-v1` and MacBook `test23-package-v1` are fully verified.
Read-only e2fsck, complete outside-block comparison, metadata/xattrs/extents,
native/gadget/logger equality and source rehash pass. Component15, final-image18
and writer independent checks pass; private JSON reviews bind exact hashes.

Published native USB port HAL remains31576B, SHA256
`6ef50f071c02fa5e13dd3541cce9c276186f600ea6abb8d18ae00ba7e587968d`.
Exact native and framework source review: constructor/register/query do not
configure gadget or MTP. canSwitchRole opens role nodes writable but closes
without writing; actual role writes require explicit switchRole RPC. Service
initialization sets callback and queries. Existing adb-only gadget guards are
unchanged. Resuming UsbService may still cause framework USB reconfiguration;
verify final sys.usb.config/state=adb and peripheral mode after the trial.

No phone mutation occurred during this diagnosis/preparation. Phone disappeared
from MacBook ADB and USB before the planned live trial; no reset was sent.
`capture_test23_usb_before.py` stopped at its no-device guard before any phone
command. Preserve that failed-v1 record; use a new output directory next time.
An owner connection/screen question is pending. Do not infer the physical state.

Next actions once connected:
1. If Android ADB returns, verify exact Test22/root/native HAL/RC and current
   USB state, save before evidence, then start existing vendor.usb-hal-1-0 once.
   Observe boot_completed, user/launcher state, ADB and system_server for more
   than two minutes, with dedicated crash/watchdog logs. A later live stack
   showed sensor-HAL waiting in another incarnation; additional blockers remain
   possible. Do not claim a complete boot from this USB diagnosis alone.
2. If fresh EDL is detected, load the programmer once, then use the new read-only
   `audit_test23_before.py` for full GPT/boot/recovery/misc/system capture.
   Verify backups on both Macs. Source system must match exact Test22, and misc
   must still match section50 baseline; review any change before proceeding.
   Reviewed `run_test23_edl_system.py` permits only physical0 LBA5639288 count8,
   with immediate block readback and full system/protected readbacks. Never
   raw-write system while Android has it mounted. Never format userdata again.
3. Writer SHA256
   `59eb68812b68373ea3d420bc257d69e6b2c13b084f424dfb78673e7eaa12b9f3`;
   delta SHA256
   `8fcfb957f737c58e3510a0d87150121a0805eaa59560ab955b5aa136c9af142b`.
   Test23 runner gate is `test23-edl-system-independent-review.json`. It does
   not reset or load a programmer. Both-Mac full readback receipt is required
   before a separately guarded reset. All Test20 boot/recovery protections stay.

Test23 intentionally retains Test22 diagnostic service/directory names. Existing
cache archives may belong to the preceding boot: use fresh RAM/live captures
and boot identity to establish results. Gatekeeper credential functionality,
optional GPU accounting, QSEE/ADSP/camera/fingerprint and4.4 software reboot
limitations remain. The direct BCB recovery route is verified; bootloader-menu
recovery selection itself is still not established as repaired.

**Test23 installation completed after owner reported fresh EDL.** Verified
QUSB__BULK05c6:9008, loaded the pinned eMMC programmer once, and read fresh full
GPT/boot/recovery/misc/system. The complete source matched Test22 exactly; all
protected hashes and empty BCB matched section50. Before backups were verified
on both Macs with a returned receipt. The reviewed writer changed its single
4096-byte block and immediately verified it, then read the complete6979321856B
system back to exact Test23SHA33db1d4d4e5e49f5dc1c06cbd6a0e39b07fd9b6d886941e33f165b7876fccc5a.
GPT/boot/recovery/misc remained unchanged. Both-Mac after evidence and returned
receipt are complete in `hardware-tests/test23-edl-before` and
`hardware-tests/test23-edl-system-write`. Userdata was not written.

Reviewed `reset_test23_verified.py` SHA256
`6911cb4e8006d4171ccc2cdab03587e57779d836f553392aefb99f48920217d5`
passed14 offline guards and exact evidence gates. A single reset was sent after
fresh GPT/misc checks; USB disconnected before ACK. EDL disappearance is actually
observed. Journal is `hardware-tests/test23-edl-reset`; do not repeat reset or
load the programmer again without fresh EDL. Runtime boot remains pending.

Read-only `capture_test23_android_supplement.py` is staged and hash-verified on
MacBook, SHA256
`b0d67ee734cccd26e9a16a88aa0fc8462c461ad70edcb88acdd6a2d5c24c7072`.
Author28 and independent57 checks pass. Default is files-only; `--execute`
captures seven observations over at least180seconds (480-second overall cap),
checks exact USB RC/native and retained patches before/after, and records
USB/user/foreground/boot/watchdog state. Successful collection does not itself
prove boot completion or framework stability. Test22 logger names stay intact.

Post-reset initial50-second and subsequent60-second monitors observed no EDL
and no ADB. Owner screen observation has been requested; no screen state is
inferred. The new read-only Android collector has not executed. Do not reflash,
repeat the reset, or reload a programmer based only on absent USB. Use the
owner's screen report to determine whether normal physical Start/Power is
needed, or capture immediately if Android ADB returns.

## 52. Full Android boot and automatic dual-screen span confirmed (October16)

Owner subsequently reports "it finally boots". ADB returned in full Android
state. Reviewed Test23 collector completed all seven observations spanning
185.767seconds: sys.boot_completed=1 throughout, same system_server PID and
starttime, USB port HAL running, adb-only USB configured in peripheral mode.
Exact Test23 USB RC/native and retained diagnostic patch hashes match before
and after. User0 is RUNNING_UNLOCKED, CE/system unlocked users include0,
QuickstepLauncher is resumed, mBooted=true and mBooting=false. All capture files
and a returned verification receipt are checked on both Macs in
`hardware-tests/test23-android-supplement-v1`. This verifies the USB-service
restoration resolved the captured final-boot deadlock; it does not certify all
hardware. Camera-daemon crashes remain visible in the dedicated crash buffer.

Owner clarified the feature concern: **both screens work perfectly**, single
while folded and one display spanning both when unfolded. They are comparing
against the stock ZTE ROM's additional modes, not reporting a broken panel.
Read-only evidence under `hardware-tests/test23-display-modes-v1`, verified on
both Macs, confirms com.zte.fujisan.primarypanel is installed/running and its
PrimaryPanelTileService is already in sysui_qs_tiles. fujisan_halld is running;
both Small1080x1920 and Wide2160x1915 endpoints are registered. The initial
snapshot was folded (hall1, closed_a, display_mode single), consistent with
the owner's subsequent unfolded result. No settings/service writes were made.

Upstream device-tree commit3ab8b8d3895a9e78f77d237809761119552e44a7
(2026-10-05, before the shipped October6 build) documents the current controls:
`dualscreen/FujisanPrimaryPanel` provides a Quick Settings tile named
**Main screen switch**. Tapping selects A or B while folded; it is unavailable
when unfolded and has no long-press mode-picker activity. The hall daemon
publishes single or zoom (wide) automatically; device-state/layout XML supplies
only Small and Wide postures. Current composer has no mirror mode enum or
dual_internal property consumer. Do not change that leftover property or force
both display endpoints on: they share one hardware route. A mirror or separate
per-panel app mode would require additional feature implementation, not a
reinstall or enabling a missing app. XDA was inaccessible (HTTP403); do not
claim to have verified its current screenshots. Pinned source files and URLs
are saved privately under `test23-dual-screen-source-review`.

No new flash, reset, firmware change, or repeat userdata format is needed for
this reported concern. Keep the verified Test23 boot and existing backups.

**ROM provenance clarified for owner:** Test23 derives from the developer's
published `lineage-23.2-20261006-UNOFFICIAL-fujisan.zip`, obtained through
AxonMUpdates post36 and the developer's alist download (saved source receipt).
The original1068692459-byte ZIP was rehashed and still matches SHA256
`d9b4caca37dc906c4f9b4700bc8d24fe6fe5757e8eeba7c45fe2c55143883456`.
The saved system-image chain is published raw90aea590… → AT&T GPU0271379d… →
Test20 7c32f735… → Test22 508cd083… → Test23 33db1d4d…. Each preparation manifest
pins its exact source and output. This is the existing unofficial LOS23.2
release adapted for the AT&T Z999, not a substitute ROM or a new full ROM
build. The extra stock ZTE display modes were not removed by these patches.
Current live XDA access remains blocked; provenance here rests on the saved
download/extraction/patch records, not a newly verified XDA page revision.

## 53. Public findings and source publication (October16)

The owner requested publishing findings and files to GitHub. The current
summary is [docs/ATT_PORT_STATUS.md](docs/ATT_PORT_STATUS.md). Runnable offline
image/GPT/initcall helpers and40 synthetic tests are under `scripts/` and
`tests/`. The [investigation archive](archive/att-port-2026-10/README.md)
preserves155 Python,18 authored shell/init and6 assembly source files, plus25
preparation/review metadata records. The archive manifest maps original source
hashes to public-copy hashes and records redaction of local paths, session/host
names and private UUIDs. Historical code is reference text with `.txt` suffixes;
some scripts perform real hardware operations at import. Never run test
discovery against that archive or treat its sanitized metadata as execution
approval. Original private hash-bound helpers and artifacts remain unchanged.

Firmware/images, Firehose programmers, keys, raw device captures, partition
backups and encoded block-delta payloads are not published. Old preparation
metadata can legitimately say `hardware_tested: false`; the later verified
results are in sections50–52 and the current status document. Preserve this
distinction when continuing work. No phone changes were part of publication.

## 54. Owner reports inconsistent Start/recovery routing (October16, open)

During publication the owner clarified: selecting Recovery from the bootloader
Start menu does not boot recovery; selecting normal Start instead enters LOS
recovery, and choosing Restart there finally reaches LineageOS. This is an owner
observation, not yet matched to a fresh cmdline, BCB capture or slot readback.
Do not assume the images are swapped: Test20 boot/full recovery hashes and the
earlier actual recovery-slot BCB trial were verified separately. Preserve the
working Android baseline and userdata. Next investigate startup reason, current
misc/BCB, running init/recovery identity and full current slot hashes, followed
by exact bootloader routing if needed. No corrective flash is authorized by
evidence yet; root must identify the cause before choosing a bounded repair.

**Fresh investigation (October16):** owner clarified the normal Start recovery
entry followed a Settings factory reset. Captures `test23-boot-route-v1/v2`
and `test24-recovery-preflight-v1` are complete and hash-verified on both Macs.
Current full boot/recovery/misc hashes still match the exact Test20 baseline;
boot and recovery are not swapped. Android reports normal bootmode and
boot_completed=1. BCB first2048 bytes are zero; actual mounted cache has no
recovery/command. Previous-boot pstore records incoming `boot-recovery`, its
replacement with `--show_text --reason=axon-diag-test19`, native BCB clearing,
and the owner's normal Restart (`reboot,userrequested,recovery`). That suffix
is the native normal-restart reason, not an explicit recovery-target request.

The diagnostic recovery service passes argc>1. Exact native analysis confirms
this bypasses BCB/cache operation-argument parsing, replacing a possible
Settings --wipe_data request with diagnostic menu arguments. Its fstab also
omits cache/data. Thus the owner’s reported reset must not be treated as a
proven wipe. This explains the captured one-shot recovery entry; it does not
prove the separate bootloader-menu/PMIC route fixed. Do not patch aboot.

Test24 local candidate restores native `service recovery /system/bin/recovery`,
restores the published cache ext4 and userdata F2FS rows with wait-only fs_mgr
flags, and stops starting the private cache persister so native recovery owns
cache. Kernel/DT/cmdline, native binaries and adb-only setup stay exact.
Only two of595 CPIO records differ. Signed /recovery image26625079B SHA256
`cb56783c82110e2bc6a9356999f7e4197a5cb56167087dc06e8b9cfc955d43e5`;
sector-padded26625536B SHA256
`ed465040ef7ca9b22189f63aed47c45cd29039c9b5ca844a15d221d40bf64670`.
Prepared privately in `prepared/test24-usable-recovery-v1`; NOT yet flashed.
Fresh empty BCB and absent cache command are mandatory before its first boot.
The installed full recovery tail is not all zero: preserve the pinned full
partition tail when constructing a full64MiB write artifact.

Native recovery formats F2FS with `-g android -O project_quota,extra_attr`
regardless of the fstab quota flag. Prior Test20 scratch validation covered
feature0 only. This is an unvalidated compatibility question, not a proven
formatter defect. Verify the exact native arguments on a RAM-backed regular
file/loop device before allowing a native factory reset; never use userdata
for that capability test. No new userdata reset has been authorized.

## 55. GApps requested; official package staged, not installed (October16)

Selected official MindTheGapps Android16 ARM64 release20260915_222150:
511299883B, SHA256
`d60f550e4dc96606644fbbf886a9892d1391a607225e861ceaef27bd999bc6a3`.
GitHub release digest, byte size, ZIP CRC and all44 member hashes were checked.
ZIP and verification receipt are staged on both Macs; expanded size1138465773B.
Live device is SDK36/arm64 with about4.25GB system space available. Installer
mounts monolithic system and writes system/product/system_ext plus addon.d;
it does not write boot/recovery/firmware or format data. Its exit0 does not
prove all copies succeeded; verify payload hashes/permissions and retained
AT&T patches after installation. Never reinstall the original ROM ZIP, which
would replace the proven AT&T boot adaptation.

Official Lineage instructions require factory reset when Android has already
booted before GApps installation. Current device_provisioned and user_setup_complete
are both1. Root asked for fresh permission to erase current apps/settings/files;
answer is pending. Original Test20 wipe authorization is not reusable. Continue
recovery preparation/validation while waiting; do not wipe or install GApps
against this already-configured userdata without resolving this requirement.
Sources: https://github.com/MindTheGapps/16.0.0-arm64/releases/tag/MindTheGapps-16.0.0-arm64-20260915_222150
and https://github.com/LineageOS/lineage_wiki/blob/4edbf1aabad1ed98ab265ced65788a47c1c9e2bb/pages/gapps.md .

**Test24 recovery-only installation completed (October16):** fresh full boot,
recovery, misc and both GPT copies matched their pinned baseline. Before copies
were verified on both Macs with returned receipt. Reviewed writer
`install_test24_recovery_adb.py` SHA256
`a36e613b2c2de994175000a6e6612c74a7ca02bf6a1f3b5524310ad24e8a9e76`
passed10 author tests and43 independent checks. It wrote only inactive p19,
preserving40483328 tail bytes beyond the sector-padded signed candidate.
Complete64MiB recovery readback SHA256
`52d50365ec73d60af80e235b776069fe5f2b85338a68126c2c0ea00f103170d9`.
Full boot/misc/mainGPT/backupGPT were byte-identical before/after. Before and
after backups and returned verification receipts are in
`hardware-tests/test24-recovery-install-v1` on both Macs. No reset, system
write, data write or GApps installation was performed. Phone remains in the
same full Android boot; BCB is clear and cache command absent.

Next: after the owner's pending reset decision, enter Test24 recovery using
a separately guarded menu-only route and verify native runtime identity,
filesystem paths and memory. Do not assume the bootloader Recovery menu works.
`test24-recovery-capture.sh` is read-only. The fixed RAM-only formatter checker
SHA256 `5392afda9f3fb17507017ac1e52707253e1aca8a5c9354be86e1dc665e04e26d`
has15 independent confinement/cleanup checks; superseded0d717... was never run.
Bound the actual run to180seconds and inspect cleanup on failure. The runtime
boot and native formatter test remain pending, as does GApps installation.
Local free space is below1GiB; plan adequate space before capturing a changed
full GApps system image. Preserve existing baseline images and backups.

## 56. GApps clean installation authorized (October16, in progress)

The owner answered **yes** to: “May I erase the current apps, settings, and
files after validating recovery, then install GApps?” This is fresh explicit
authorization for the clean installation. Do not ask again for the same reset.
First validate Test24 recovery and the RAM-only native formatter test.

ADB was absent at the start of this turn; MacBook USB inventory shows fresh
QUSB__BULK05c6:9008. The pinned eMMC programmer was loaded successfully once
(`test25-loader.log`). Do not load it again in this EDL session. Read-only
`audit_test25_before.py` is capturing fresh main/backup GPT, boot, recovery,
misc and system to `test25-edl-before` on MacBook. Expected recovery isTest24
full52d50365..., system remainsTest23 full33db1d4d.... No new writes or resets
have occurred yet. Recovery entry must be menu-only, without a wipe command,
until runtime and formatter validation finish.

**Recovery first boot and native formatter validation passed.** After the
verified menu-only BCB setup and one EDL reset, ADB reports recovery; live native
recovery/init/fstab hashes matchTest24, USB isadb-only, and BCB is cleared.
Evidence `test24-recovery-runtime-v1` includes exact native formatter execution
on a256MiB RAM file, successful kernel mount/write/read, dry-run fsck and full
scratch cleanup. Native profile uses F2FS features0x499 (encrypt,extra_attr,
project_quota,quota,verity); availability does not enable data encryption by
itself. No real userdata format occurred in this capability test.

The first runtime collector had an AND-list/errexit bug: it reported cache
command absent even though cache was unmounted. Its other identity/BCB and
formatter evidence remain valid. Preservev1; use corrected v2 collector
SHAe86b689ae7d22c510d65ec8c8cdfd3a955dae6fd88484e84a70b67dea0cb726f.
Unmounted cache is normal after native FinishRecovery, which unlinks its command
then unmounts cache. Do not claim a fresh command-file check from an unmounted
placeholder. Explicit --show_text BCB precedence prevented a stale cache
operation from running on this boot.

The owner additionally said “edl on nuke and ensure everything is perfect”;
live USB was already Androidrecovery18d1:d001, so no additional programmer load
or reset was sent. Clean reset remains authorized, not a blanket firmware wipe.
The owner then explicitly declined a userdata backup; none has been created.
Do not archive or publish personal phone data. Existing ROM/partition baseline
backups are retained. Root asked the owner to choose Factory reset -> Format
data/factory reset, then stay in recovery. That physical UI result is pending;
do not run a competing reset/installer while the owner may be operating it.

Official GApps ZIP is retained and rehashed on MacBook; duplicate local
download cache was removed to free511MB. All package member hashes and original
installer remain local. Verification v1 had an AND-list absent-path bug; use
immutable `prepared/test25-gapps-verification-v2/verify-mounted-system.sh`,
SHAa7dffda8371a25527131f3520bb9c7a369943e3eab21c7c443921e6bee8a61f5.
It checks36 Google payload files and27 retained AT&T patches plus addon.d and
metadata. Root will use the original hash-verified cache-staged installer after
reset, keeping native recovery idle. Native user-build sideload may reject
unknown signing keys without offering override. This shell installation uses
the unchanged official package, avoids a second recovery process, and requires
explicit file/fullsystem verification before boot. No GApps writes yet.

**Native reset completed and verified.** Owner reports “data wipe complete.”
Fresh recovery log records successful native F2FS format of userdata and ext4
format of cache, followed by “Data wipe complete” and BCB clearing. Corrected
v2 identity collector passed on the still-running Test24 recovery. Cache was
mounted from geometry-verified p36; its actual filesystem has no pending
recovery/command. BCB first2048 bytes are zero. Post-reset evidence is verified
on both Macs in `test25-post-reset`. No userdata backup was made. GApps has
not yet been installed at this checkpoint; keep recovery idle until verified.

**GApps installed; file verification passed, first Android boot pending.**
The exact official MindTheGapps16 ARM64 package passed on-phone SHA/size and
original updater checks. Reviewed wrapper83d8758c... invoked that updater once,
with no second recovery process or ROM ZIP reinstall. It returned0. The first
read-only verifier failed because recovery exports TMPDIR=/data/local/tmp,
which is absent after reset. The unchanged v2 verifier passed after exporting
TMPDIR=/tmp: all36 Google payload files,27 retained AT&T files, expected
Provision/Titan absence and generated addon.d content/mode/owner/labels match.
System was then cleanly unmounted for the complete after readback.

Two evidence-tool limitations were found and preserved: original updater's
ui_print reopens /proc/self/fd/3 with truncation, so directing fd3 to a regular
journal loses earlier installer log messages. Exit0 is never sufficient; the
independent complete file verification above is the installation evidence.
Do not rerun the installer to recover logs. Initial readback helper used awk,
which native recovery lacks; it aborted before creating its output directory.
Immutable capture_test25_after_v2.py replaces those two awk expressions with
shell read loops, preserving all byte-stream/digest logic;20 focused review
checks pass. It reads no userdata and makes no device writes. Full post-install
system/protected readback is in progress at this checkpoint.

**Complete Test25 after readback passed on MacBook.** All6979321856 system
bytes were read after clean unmount; the host SHA and a separate native full
partition SHA agree at
`257967d70da94070625fbc0dfee0880929f0d8a282b9986c72e71e29fd2b4d36`.
Full boot/recovery/misc and both GPT copies remain exact baseline bytes;
protected hashes were checked again after the system capture. No userdata was
read. An offline compressed changed-block representation is being created for
this Mac, retaining the complete exact Test23 baseline. First Android boot with
GApps is pending until both-computer verification completes.

**Both-Mac verification is complete; owner restart requested.** The system delta
contains703 changed1MiB chunks compressed to312204492 bytes. Both computers
streamed the complete reconstructed6979321856-byte image and verified the exact
Test25 SHA above; its manifest SHA is
`8edb6c65a3e00b00b201441c631a3b69b11eb7bb1676939991b7e4a81b41be10`.
The complete remote readback and local exact baseline+delta are retained;
returned local-verification receipt is saved in remote test25-after. No userdata
backup exists. The temporary511MB ZIP was removed from the phone after its
journal capture; cache was cleanly unmounted and BCB remains zero. Owner was
asked to select Reboot system now. First Android startup is pending.

## 57. Owner confirms post-GApps Android and recovery boot (October16)

Owner reports: “boots to recovery and lineage os just fine,” but says the START
menu is needed and Volume Up does not seem to enter recovery. Treat this as
successful owner-observed boots, not a completed ADB Google-package/runtime
validation. The phone is currently in native Test24 recovery: exact executable
hash, recovery bootmode, adb-only USB and zero BCB are verified in the read-only
`test25-recovery-key-route` capture on both Macs. No writes or resets were sent.

Do not conflate three bootloader entry paths: the START menu Recovery action
uses PMIC reboot reason1; normal boot can honor misc boot-recovery; physical
Volume Up is sampled early by aboot. The exact AT&T bootloader is being reviewed
for that physical-key branch. No failed key timing or root cause is yet proved.
Root asked whether the owner used Power+VolumeUp from fully off or VolumeUp
during startup. Preserve the working images; no bootloader replacement or
additional format is warranted by this report.

**Physical-key route and factory-mode flag checked.** Exact AT&T aboot samples
Up(key0x115) held with Down(key0x116) released at0x9183dc54–70. Its normal branch
directly selects recovery. Persistent bootmode=1 instead makes Up exit factory
mode. The literal key is `bootmode`, not the analyst label _LMP. The table is
ztecfg p16 byte4096 length4096 (partition start917504,1024 sectors). Root verified
GPT and the literal, then read only that table through native recovery. Exactly
one record has valid header/signature and value0, ruling out current FTM
diversion. Other configuration values were not retained or published.

An earlier PMIC power-off-reason branch can bypass key sampling; no current
trace proves it did. Key timing and USB-powered startup remain unresolved.
Owner was given ZTE's general guidance: fully power off, disconnect USB, hold
Power+VolumeUp, release Power at vibration while keeping Up held. This has not
yet been confirmed on this unit. No phone writes or resets occurred this turn.
Static evidence: archive/att-port-2026-10/test25/aboot-physical-key-analysis.json.

## 58. Owner authorizes publishing patched binaries (October17)

The owner explicitly overrode the earlier AGENTS binary restriction and asked
for patched TWRP/LOS downloads plus a total-work summary. This supersedes prior
statements excluding ROM/recovery binaries. Release `att-z999-los23.2-test25-20261017`
contains exact tested Test18 TWRP BOOT-target, Test20 LOS boot, Test24 LOS recovery,
and gzip packages of Test23 vanilla and Test25 GApps raw system. These are
component images, not sideload ZIPs; TWRP and LOS boot occupy the same partition.
See docs/RELEASE_2026-10-17.md and docs/releases/att-z999-20261017-manifest.json.

Independent review rehashed the three signed images, validated their signatures,
and reconstructed the full GApps SHA from the local exact baseline+delta. System
packaging checks both original and decompressed complete hashes. Private keys,
programmers, userdata, GPT/misc and full partition tails are excluded. Exact
images retain device-specific cache-UUID diagnostic pins; this is documented,
not represented as universal configuration. No phone access/write is part of
publication. Published GitHub asset size/digest checks are required before the
draft release is made public. Existing historical source-only archives remain
unchanged and retain their original scope descriptions.

**Publication completed October17 07:24 UTC.** Public prerelease
`att-z999-los23.2-test25-20261017` contains all eight intended assets. GitHub's
reported sizes and SHA-256 digests match the five binary packages and three
metadata files. Anonymous release lookup and checksum download also passed.
Receipt: docs/releases/att-z999-20261017-publication.json. After MacBook SSH
became unavailable, both gzip systems were reconstructed from the verified local
Test23 baseline and Test25 changed-block archive; their complete compressed
hashes exactly matched the already verified MacBook packages before streaming
to GitHub. No phone access or writes occurred during publication.
