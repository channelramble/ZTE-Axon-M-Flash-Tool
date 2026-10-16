# Local preparation for the AT&T Android 16 investigation

Read [current port status](ATT_PORT_STATUS.md) and [AGENTS.md](../AGENTS.md)
first. Test23 now boots full LineageOS23.2 on the AT&T unit, with verified
framework stability and working single/wide screen switching. Test18 TWRP3.7
and Test19 Lineage recovery also boot. The dated observations below describe
earlier preparation and are historical, not pending tasks or current phone state.
Local signature/structure checks alone are not phone boot tests.

The [source archive](../archive/att-port-2026-10/README.md) contains the later
builders, patch descriptions, diagnostics and verification sources. Those
session-specific reference files are separate from the runnable offline tools
documented here; no ready-to-flash image or firmware is redistributed.

## Original downloads

- [Unjustified Dev's Z999-TWRP.zip](https://androidfilehost.com/?fid=6006931924117940985)
  contains the eMMC programmer and TWRP 3.2.3. Published archive MD5:
  `0f7e13270b4467a72a3ae60bdd7ade75`.
- [The developer's update channel](https://t.me/s/AxonMUpdates) links
  `TWRP-3.7.0_9-O-fujisan-20260809.img`,
  `lineage-23.2-20261006-UNOFFICIAL-fujisan.zip`, and its recovery image.
  Keep source URLs, local SHA-256 digests, and archive checks in a private
  manifest. Extract only `boot.img` and `recovery.img` for this work.
- [Google platform-tools 29.0.6 for macOS](https://dl.google.com/android/repository/platform-tools_r29.0.6-darwin.zip)
  supplies the adb version required by the 3.2.3 reader. This old macOS binary
  is Intel; check whether the machine running it has x86_64 execution support.
  A staged ZIP is not an installed or tested adb connection.

Keep all binaries, backups, logs, and signing keys **outside the Git checkout**.
The session's private sibling directory is `.axon-m-private`; its `prepared`
subdirectory contains candidate images, JSON manifests, and validation results.
Do not use the original ZIP's `rawprogram0.xml`: its recovery offset is wrong.

## Offline image tool

`scripts/fujisan_image.py` uses Python 3.9+ and the OpenSSL CLI. It never opens
USB, adb, SSH, or EDL. Every input signature is checked before patching, and
every output is checked before it is saved. An existing output is not replaced.

```sh
python3 scripts/fujisan_image.py inspect /private/path/original.img
```

Create a private local RSA signing key and matching certificate once, outside
the repository. The unlocked test phone previously accepted locally signed
images. Signature verification here uses the embedded certificate; it does
not establish trust by a stock locked bootloader.

```sh
umask 077
openssl req -new -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 \
  -subj '/CN=Axon M local debug images/' \
  -keyout /private/path/local.key -out /private/path/local.pem

python3 scripts/fujisan_image.py patch /private/path/TWRP-3.7.0_9-O-fujisan-20260809.img \
  /private/path/twrp-3.7.0-att-boot.img \
  --target /boot --key /private/path/local.key --certificate /private/path/local.pem \
  --att-dt --charger --adb-only --append-cmdline 'ignore_loglevel initcall_debug'

python3 scripts/fujisan_image.py patch /private/path/twrp-3.2.3-0_fujisan.img \
  /private/path/reader-3.2.3-recovery.img \
  --target /recovery --key /private/path/local.key --certificate /private/path/local.pem \
  --reader --adb-only
```

The `--att-dt` option reserves `0x9ff00000`–`0x9fffffff` with `no-map` and
places 8192 unused bytes after each DTB's strings block. The original compressed
kernel and ramdisk are retained. The tool rejects conflicting reservations or
unexpected Fujisan IDs. TWRP 3.7.0's legacy Qualcomm SHA-1 ID convention is
preserved; the LineageOS images use the AOSP convention.

The `--reader` option appends the documented charger and USB actions to the
old recovery's `init.rc`. Other cpio records, including permissions and
symlinks, and the complete original kernel/DTBs remain unchanged. Output
manifests record source hash, output hash, target, changes, and lack of hardware
testing. `/boot` and `/recovery` signatures are not interchangeable.

For TWRP 3.7.0, use `--charger` to append only `on charger` → `trigger late-init`
to its recovery ramdisk. The published image lacks this action. This option
keeps its USB policy intact and is mutually exclusive with `--reader`; it is
intended for recovery ramdisks, not normal Android boot images.

**Include `--adb-only` for all new TWRP test images**, per the owner's request.
This separate option changes only `prop.default` and `init.recovery.usb.rc`:
it normalizes the USB default to adb, uses TWRP's existing startup guard to skip
MTP, and replaces MTP activation actions with adb redirects. Legacy USB
function writes are made explicit to avoid a queued action reading a later MTP
request. The configfs adb readiness/UDC sequence and FunctionFS mounts remain
unchanged. A later GUI request to enable MTP can still reconnect adb, but it
cannot bind MTP through these patched handlers. Unknown USB layouts are rejected.
The flag is for the two inspected TWRP ramdisks, not the LOS Android ramdisk.

These images have no new `epstore.c`, entry-marker, or halting-checkpoint patches.
Do not add `fj_reboot_at` to a shipped kernel expecting those absent patches to
work. The TWRP candidate's `initcall_debug` argument enables ordinary kernel
logging; it does not create an early persistent console.

## MacBook connection and backups

The phone remains connected to the MacBook. Keep reads and device commands on
that computer; local preparation does not require moving the USB cable.
The installed EDL environment is `~/.local/share/axon-m-edl`, pinned to
`bkerler/edl` commit `1cda1a616748d608667b2d13b73a28d3197ceb45`.

1. Recheck SSH and USB 05c6:9008 on the MacBook. Stage the verified eMMC
   programmer and scripts there, and compare their SHA-256 hashes after transfer.
2. Use a new private backup directory. The installed EDL client's reconnect
   probe is incompatible with this legacy programmer: a 48-byte read overflows
   on Firehose XML, and endpoint `clear_halt` fails. Use the private
   `sahara_load.py` for a fresh EDL arrival and `firehose_read.py` once the
   programmer is running. These use bounded transactions, 64 KiB receive
   buffers, 512-byte sectors, eMMC physical partition 0, and `SkipWrite=1`.
   Read sectors 0 and 1 first. Preserve logs privately; require both ACKs and
   the exact byte count. A successful exit alone is not proof of a read.
3. Validate that initial file and determine the complete GPT read length:

   ```sh
   python3 scripts/check_backups.py /private/path/gpt-header.bin --header-only
   ```

4. Read from sector 0 for the reported `primary_dump_sectors`, save it as
   `gpt_main0.bin`, then run:

   ```sh
   python3 scripts/check_backups.py /private/path/gpt_main0.bin
   ```

5. Use the validated GPT's **actual** start/size values with the private reader to save
   `boot.bin`, `recovery.bin`, and `misc.bin`. Keep a separate raw copy of the
   backup GPT as well. Validate the primary GPT and partition backups:

   ```sh
   python3 scripts/check_backups.py /private/path/gpt_main0.bin \
     --directory /private/path/backups
   ```

6. Preserve backups on both computers. Inspect existing boot/recovery images
   before selecting a test: a previous debug build may still be on the phone.
   Check the reported misc BCB flag; do not blindly clear or overwrite misc.
   Every later partition write needs a matching SHA-256 readback of the exact
   image length before any restart.

The pinned EDL client's `gpt` handler has its file writes commented out while
still printing “Dumped GPT.” Its named-partition reads also rely on `get_gpt`.
Use explicit raw reads and local validation for this workflow. The checker
validates the primary header/array CRCs, partition bounds and overlaps, required
partition sizes, and complete backup lengths. It reports a `boot-recovery` flag
without printing its contents or partition GUIDs. It does not yet validate a
separate secondary GPT dump against the primary table.

The October 15 evening session completed these backups. The private
`backup_session.py` additionally checked both secondary GPT CRCs, matching disk
metadata, and identical partition arrays. Full boot/recovery/misc and both GPT
copies have matching SHA-256 hashes on both Macs. Misc is all zero. At backup
time both slots held the old reader with valid BootSignatures. Stale nonzero bytes after the
signed image remain in the full backups; trim only separate inspection copies.

The subsequent Firehose reset removed the EDL USB device but reached the Start
menu saying "your device is corrupt." Recovery selection returns to that menu,
as the original handoff already documented. Continue with the EDL/boot-slot
approach; successful recovery-menu entry is not a prerequisite. The later test
01 wrote only boot, passed exact SHA-256 readback on both Macs, and was reset.
USB/adb did not appear in the following ~45 seconds, before the owner selected
Start. The owner then reported a ZTE-logo hang and confirmed manual EDL entry.
Test 02 was written/readback-verified, but no boot result was confirmed before
the owner requested a new image. Tests 03 and 04 were subsequently written
and readback-verified; test 04 reached the ZTE screen with a red LED, without a
positive blue marker. Test 05 also stayed at the ZTE logo with a red LED during
owner-confirmed normal boot. Test 06, the published 3.18 boot-slot control, is
now boots TWRP 3.2.3 with working adb. Live captures confirm the 3.18 kernel
and charger/adb fixes.
Read private `session.json` and AGENTS.md sections 14–21 for current state and physical steps. The owner handles
EDL reentry between rounds; detect it automatically without repeated prompts.

## Next debugging input

The previous debug build and its patches are still missing. However, the
published TWRP 3.7.0 kernel contains full kallsyms. Using
[vmlinux-to-elf](https://github.com/marin-m/vmlinux-to-elf) at commit
`2d094bc9c220b6b50f8215cbc3c9e581210ce1a6`, we recovered its System.map and
used `scripts/initcall_order.py` to list 690 level 6/7 entries. Every 8-byte
pointer was then read directly from the raw Image using `_text` as its base
and matched to the expected code symbol. The verified JSON and map are in
`.axon-m-private/kernel-analysis`. They apply only to this exact published
kernel. The original candidates have no blacklist. The later
`test-01-remoteproc-boot.img` selects six verified firmware-loading initcalls;
see AGENTS.md section 14. Its full command line is 463 bytes, entirely in the
first header field. Its write and readback are verified, but selecting Start
produced a ZTE-logo hang without a current kernel trace. The next candidate,
`test-02-gpu-tzlog-boot.img`, retains those skips and adds `kgsl_3d_init` and
`tz_log_init`; its 488-byte command line also fits the first header field.
It was written and readback-verified, with its boot result unconfirmed. An
earlier prepared nine-skip variant that also disabled QSEE was rejected before
flashing because QSEE callers can touch uninitialized waitqueues.

The `test-03-qsee-probe-boot.img` instead preserves QSEE initialization
and changes one verified ARM64 call instruction to return `-ENODEV` at the
first SCM query, taking its existing failed-probe cleanup. It retains test 02's
eight skips. Only four raw kernel bytes differ; DTBs, ramdisk, and command line
are unchanged. The guarded private builder, hashes, review evidence, and
interpretation limits are recorded in AGENTS.md section 16. This is a temporary
diagnostic, not a production QSEE fix.

Test 04, `test-04-blue-led-boot.img`, was written/readback-verified on both Macs
and reset. It retains test 03 and changes only the blue RGB LED's
`qcom,default-state` from `off` to `on` in both DTBs. A new blue/purple transition
supports reaching level-6 RGB probe 376; absence remains inconclusive. See
AGENTS.md section 17 and live `session.json` before the next phone operation.

Test 05, `test-05-qce-disabled-boot.img`, retains that marker and suppresses
only the two optional QCE hardware DT nodes while preserving their shared
initializers. Its verified write still produced a red LED/ZTE-logo hang during
normal boot; see AGENTS.md section 18. Avoid adding more unbounded crypto
initcall skips.

Test 06 uses `reader-3.2.3-boot.img` with the published 3.18 kernel, unchanged
DTBs and command line, and only the two established charger/adb ramdisk fixes.
Independent image-format/signature reviews passed. The boot write and full
readback matched on both Macs. An initial 41.4-second no-USB observation was
followed by owner-confirmed TWRP and working adb. This establishes the 3.18
baseline; the 4.4 stall remains unresolved. Live captures revealed that this
reader's RAM console starts at `0xbfc40000`, unlike the older modified reader.
See AGENTS.md section 19 before preparing log captures. The phone's original
B37 AT&T `a530_zap.*` firmware is now archived privately on both Macs for the
eventual LOS package.

A marked copy of the working reader has since been written to recovery with
full 64 MiB readback verification; boot and misc were unchanged. One recovery
reboot produced no adb return in 55 seconds, so its screen result and selection
remain unconfirmed. The normal Start path still holds the proven boot reader.
Capture pstore when it returns. A logged original 4.4 recovery candidate and
an early-LED boot candidate are prepared locally; neither has been flashed.
See AGENTS.md section 20 before choosing the next test.

Use **boot** for the next debug test as the handoff specifies. Remember that
a firehose reset with USB attached can enter charger mode; lack of a UI in
that mode is not sufficient evidence of a kernel stall. Recovery-slot entry
and the 4.4 restart path remain unresolved. The original LineageOS ZIP has not
been modified into an AT&T install package: GPU firmware substitution, the
driver fix, and device data decisions are still pending.

Run the offline checks with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

Format reference:
[AOSP BootSignature.java](https://android.googlesource.com/platform/system/extras/+/android-7.1.2_r39/verity/BootSignature.java).
