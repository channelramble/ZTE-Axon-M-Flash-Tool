# AT&T Axon M: LineageOS 23.2 port status

Updated October 16, 2026. These results apply to one unlocked **AT&T Z999
(`fujisan`), eMMC, stock B37 firmware**. Test23 boots full Android 16 with both
screens working. It is a diagnostic adaptation of the developer's published
unofficial ROM, **not a production-ready release or a replacement firmware
package**. Do not install China/DoCoMo firmware or replace the AT&T boot chain.

## Verified results

| Area | Observed result | Limit of the evidence |
|---|---|---|
| Android startup | `sys.boot_completed=1`, user 0 `RUNNING_UNLOCKED`, CE user 0 unlocked, Quickstep launcher resumed | Does not establish every app or hardware service works |
| Framework stability | Seven samples over **185.767 seconds** retained the same `system_server` PID and process start time | A bounded observation, not a long-term stability test |
| USB | Port HAL running; adb-only configuration/state; peripheral mode and configured UDC | MTP, host/OTG, and role switching are not enabled or validated |
| Displays | Owner confirms single screen folded and one display spanning both screens unfolded | Stock ZTE mirror/independent-screen modes are absent from the current port |
| Recovery | Test18 TWRP 3.7 and Test19 LOS recovery boot with adb; the Test19-derived actual recovery slot also boots through BCB | Bootloader-menu recovery selection remains unreliable |
| Installation | Complete Test23 system readback matches its expected SHA-256; boot/recovery/GPT/misc remained unchanged by Test23 | Geometry and byte-level gates were specific to the tested device |

Before and after evidence was copied and hash-verified on two computers.
The owner's latest report adds an unresolved startup issue: normal **Start**
can enter LOS recovery, whose **Restart** then boots Android; the bootloader's
Recovery choice still fails. This route has not yet been matched to fresh BCB,
boot-reason or slot evidence. Successful Android boot is established, but
reliable direct startup is not. See AGENTS section54.

The Test20 installation used an explicitly approved clean F2FS format. Test22
and Test23 preserved that userdata; **boot or display troubleshooting does not
justify formatting it again**. Existing stock-data decryption was not proved.

## Provenance and exact images

The source is `lineage-23.2-20261006-UNOFFICIAL-fujisan.zip`, obtained through
[the developer's update post](https://t.me/AxonMUpdates/36) and its linked
download. The [ROM thread](https://xdaforums.com/t/rom-unofficial-16-lineageos-23-2-for-zte-axon-m-2026-10-06.4798874/)
is the project's discussion page. It returned HTTP 403 during the latest
review; provenance rests on saved download/extraction records and verified
hashes, not a new reading of that page.

All values below are SHA-256. Image hashes describe the complete named file,
not a padded prefix or a full partition unless explicitly stated. Locally
signed image hashes also depend on the local signing certificate; that key is
not published.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Original ROM ZIP | 1,068,692,459 | `d9b4caca37dc906c4f9b4700bc8d24fe6fe5757e8eeba7c45fe2c55143883456` |
| Published `boot.img` extracted from ZIP | — | `ed5cbf4e9a57ce214c182510fd1db30a59ebda7a88595a901f36a3127b6c388f` |
| Published system, expanded to raw ext4 | 6,979,321,856 | `90aea590dd4921df4bd78ebcdcd6c10d93eebe27e8d70d501d8a59e7f495899d` |
| System with AT&T GPU firmware substitution | 6,979,321,856 | `0271379d1402dc727b1c5f4a48333cf3db1f799d86370c19b5cafdecb4846f27` |
| Test20 system | 6,979,321,856 | `7c32f735219768f31444400c67cf996b5f80de4c17d0d1c1ed65a7d0acf0883a` |
| Test22 system | 6,979,321,856 | `508cd08359c6602c36d1bf0a2711dc064bfae509b5773b55933d68ad1f2570a8` |
| **Test23 system, currently installed** | **6,979,321,856** | `33db1d4d4e5e49f5dc1c06cbd6a0e39b07fd9b6d886941e33f165b7876fccc5a` |
| **Test20 boot image, retained** (`/boot` signature) | **13,976,627** | `0651435c4575980f2a851bb1f47d59f4a72a1bb56ccebd56904886e8282991b6` |
| **Test19-derived recovery control, retained** (`/recovery` signature) | **26,625,079** | `1a0c052cbc5561c50bd4dc9fde6d36573bda8beb04e5b5574e04c8a5fe9f6a9f` |

Full 64 MiB installed partition readbacks include preserved bytes beyond the
signed image: boot SHA-256
`4434306a5c58d4de5ee018a59a04ae3f551d7073efae1fe7a07bd07e468a17d6`;
recovery SHA-256
`f5bb5bf5d70ab1e44fd5ac9d888270e219f527d21a67796cf683cef5521ecb35`.
These are verification records, not portable write targets or evidence that
another device has the same GPT or partition contents.

## Changes that got Android booting

1. **AT&T bootloader handoff:** preserve each source image's own DTBs, add
   8 KiB of DT slack, reserve the AT&T 1 MiB region at `0x9ff00000`, and sign
   for the correct boot/recovery target. LOS boot DTs differ from recovery DTs.
2. **Kernel and USB probe:** make QSEE fail through its initialized error path,
   disable the two optional QCE nodes, and retain a present-null USB extcon
   supplier rather than the unavailable supplier dependency. Explicit
   peripheral mode then permits UDC registration. Normal deferred work flushing,
   `free_initmem`, and late cleanup are restored; earlier cleanup bypasses and
   LED instrumentation are not part of the current LOS boot.
3. **Graphics:** substitute the AT&T B37 GPU zap firmware and enable both KGSL
   and the GPU's generic PIL provider. Other incompatible firmware providers
   remain isolated. Rendering works; this does not validate all multimedia.
4. **Full Android startup:** coordinate adb-only FunctionFS readiness with the
   native APEX service, bridge charger startup to normal boot, add bounded logs,
   and remove automatic `formattable` fallback flags. Diagnostic system init
   and security properties allow permissive SELinux and root adb.
5. **Gatekeeper diagnostic:** skip the blocking unavailable HIDL lookup while
   preserving null-HAL handling, so `gatekeeperd` can register its framework
   binder. Enrollment/verification still fail; no success or authentication
   token is fabricated. The unavailable vendor Gatekeeper HAL is disabled.
6. **Optional GPU statistics:** use the native false/error return and cleanup
   path when GPU BPF accounting is unavailable. JNI reports `-1`, which the
   framework excludes from optional accounting. This avoids the observed
   `system_server` abort without changing GPU rendering.
7. **Test23 final-boot fix:** restore the published USB port HAL init file.
   Disabling it while keeping its VINTF declaration had left `UsbService`
   waiting for `IUsb`, blocking `finishBooting`. This change is **89 bytes in
   one 4096-byte system block**. The native HAL and adb-only gadget setup stay
   unchanged. Boot completion and the stability observation followed.

## Recovery entry

The bootloader menu's recovery selection returned to the start screen even
with the verified recovery image intact. Exact bootloader analysis showed a
separate normal-boot BCB path selecting the actual recovery partition.

A guarded trial wrote only the first misc sector: command `boot-recovery`
and recovery arguments `recovery\n--show_text\n`, preserving all unrelated
bytes. There were no wipe, update, or sideload arguments. Full misc and protected
partition readbacks preceded a separately gated restart. Recovery appeared in
adb after 16.4 seconds, with the expected executable and recovery boot mode;
unchanged Android boot bytes confirmed this was the recovery slot. Native
recovery cleared the complete misc partition back to its captured baseline.

This establishes a working route, not a repair to menu/PMIC routing. Do not
blindly copy a BCB sector or leave `boot-recovery` set after a failed attempt.
Any repeat requires the current misc backup, validated GPT/geometry, exact
field edits, full readback, and an available clear/restore path. The 4.4
software-reboot path is unreliable; the verified workflow uses controlled
physical restarts. [AGENTS sections 50–52](../AGENTS.md) preserve the evidence.

## Display controls and feature gap

The installed `com.zte.fujisan.primarypanel/.PrimaryPanelTileService` is already
in Quick Settings. **Main screen switch** selects A or B while folded; its
subtitle reads **A screen** or **B screen**. When unfolded it is unavailable
and says **Please fold the device**. There is no dedicated long-press mode
chooser in this app. The hall daemon automatically selects single or spanning
display according to posture after boot completion.

The reviewed upstream device source is commit
[`3ab8b8d3895a9e78f77d237809761119552e44a7`](https://github.com/Anya1014CN/android_device_zte_fujisan/tree/3ab8b8d3895a9e78f77d237809761119552e44a7),
dated October 5, 2026, before the ROM filename date; this does not prove the
ROM's exact build commit. Its
[tile implementation](https://github.com/Anya1014CN/android_device_zte_fujisan/blob/3ab8b8d3895a9e78f77d237809761119552e44a7/dualscreen/FujisanPrimaryPanel/src/com/zte/fujisan/primarypanel/PrimaryPanelTileService.java)
and [display layout](https://github.com/Anya1014CN/android_device_zte_fujisan/blob/3ab8b8d3895a9e78f77d237809761119552e44a7/configs/display/display_layout_configuration.xml)
define Small 1080×1920 and Wide 2160×1915 endpoints sharing one hardware route;
they must not be enabled together. The
[`dual_internal` property is explicitly a compatibility placeholder](https://github.com/Anya1014CN/android_device_zte_fujisan/blob/3ab8b8d3895a9e78f77d237809761119552e44a7/system.prop#L109-L119).
Changing it does not enable stock independent-screen mode. Mirror or separate
per-panel app modes require new functionality; they were not removed by the
AT&T patches. Ordinary split-screen on Wide is a possible smaller starting
point, not a newly validated stock-equivalent mode.

## Remaining limitations and priorities

- **Security:** permissive SELinux; root, unauthenticated adb; QSEE deliberately
  unavailable; no working Gatekeeper credentials or authenticated-key claim.
  The shipped software KeyMint does not fix the QSEE-backed Gatekeeper. Do not
  treat this build as suitable for sensitive accounts, secure lockscreen use,
  or encrypted-data migration.
- **Hardware:** camera-daemon crashes remain in the captured crash buffer.
  ADSP/audio, modem/radio, sensors/SLPI, video acceleration, and fingerprint
  need work or validation; several related kernel initializers/providers are
  deliberately disabled. Wi-Fi, Bluetooth, calls, suspend, thermals, charging,
  battery life, and extended stability are not certified by the boot result.
- **USB/restart:** adb-only peripheral policy is intentional; MTP and host/OTG
  are outside the tested configuration. ADB can still wait behind normal
  APEX/KeyMint/ART/odsign startup. Software reboot and menu recovery remain
  unreliable. Restoring the USB port HAL must not be confused with enabling
  arbitrary gadget composition or role switching.
- **Diagnostics:** Test23 retains Test22 logger names. A cache archive can be
  from an earlier boot; use fresh live/RAM evidence and boot identity. Optional
  GPU memory accounting remains unavailable, with its original BPF failure
  cause unresolved.

Preserve the verified baseline and rollback copies. Next work should capture
each hardware failure independently, restore compatible services/providers
without foreign firmware, repair credential/security functionality, and test
longer uptime and power transitions. Extra display modes are a separate feature
project, not grounds to reinstall or format the working phone.

## Repository entry points

- [Investigation files](../archive/att-port-2026-10/README.md): historical patch
  builders, diagnostics, transports, assembly, logger payloads and review
  metadata, with a public hash inventory and documented redactions.
- [AGENTS.md](../AGENTS.md): chronological findings, exact test transitions,
  safeguards, and continuation notes; older “pending” entries are historical.
- [Local preparation](LOCAL_PREPARATION.md): early offline workflow and tool
  limits; it is not a complete recipe to reproduce Test23.
- [`fujisan_image.py`](../scripts/fujisan_image.py): boot-image inspection and
  narrowly guarded offline transformations.
- [`check_backups.py`](../scripts/check_backups.py): saved GPT/partition checks.
- [`initcall_order.py`](../scripts/initcall_order.py): read-only ordering from
  an exact kernel's `System.map`.
- [Partition notes](PARTITIONS.md) and [original QFIL findings](FINDINGS.md).

The repository does not redistribute the ROM, patched images, proprietary
firmware/programmers, signing keys, device identifiers, or private captures.
Public hashes document provenance; they do not make the old one-device write
plans safe to rerun on another phone.
