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
| Recovery | Test24 LOS recovery boots through BCB with adb; native data/cache factory reset succeeded | Bootloader-menu recovery selection remains unreliable |
| Installation | Complete Test23 system readback matches its expected SHA-256; boot/recovery/GPT/misc remained unchanged by Test23 | Geometry and byte-level gates were specific to the tested device |

Before and after evidence was copied and hash-verified on two computers.
The owner's latest report followed a Settings factory reset: normal **Start**
entered LOS recovery, whose **Restart** then booted Android. Fresh full-slot
hashes prove the images are not swapped. Previous-boot pstore records an incoming
BCB recovery request; diagnostic command-line arguments suppressed processing
of the requested operation. Test24 recovery removes that restriction
and restores cache/data access. Full readback, native recovery boot, a RAM-only
formatter compatibility test, and the owner-approved factory reset all passed. The bootloader's
Recovery choice remains a separate unresolved route. See AGENTS section54.

The Test20 installation used an explicitly approved clean F2FS format. Test22
and Test23 preserved that userdata. The later GApps installation used a new,
explicitly approved native factory reset; no additional wipe is needed for
verification. Existing stock-data decryption was not proved.

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
| **Test23 system, pre-GApps baseline** | **6,979,321,856** | `33db1d4d4e5e49f5dc1c06cbd6a0e39b07fd9b6d886941e33f165b7876fccc5a` |
| **Test25 system with GApps, installed** | **6,979,321,856** | `257967d70da94070625fbc0dfee0880929f0d8a282b9986c72e71e29fd2b4d36` |
| **Test20 boot image, retained** (`/boot` signature) | **13,976,627** | `0651435c4575980f2a851bb1f47d59f4a72a1bb56ccebd56904886e8282991b6` |
| **Test24 recovery, installed and booted** (`/recovery` signature) | **26,625,079** | `cb56783c82110e2bc6a9356999f7e4197a5cb56167087dc06e8b9cfc955d43e5` |

Full 64 MiB installed partition readbacks include preserved bytes beyond the
signed image: boot SHA-256
`4434306a5c58d4de5ee018a59a04ae3f551d7073efae1fe7a07bd07e468a17d6`;
recovery SHA-256
`52d50365ec73d60af80e235b776069fe5f2b85338a68126c2c0ea00f103170d9`.
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
software-reboot path has been unreliable, although the owner's latest native
recovery Restart succeeded. Its `userrequested,recovery` boot reason denotes
normal Restart from recovery, not an explicit recovery-target request.
[AGENTS sections 50–54](../AGENTS.md) preserve the evidence.

The previous diagnostic recovery passed `--show_text --reason=axon-diag-test19`
at service startup. Native recovery skips parsing BCB/cache operation arguments
when explicit command-line arguments are present. It also lacks cache/data
fstab entries. A Settings factory reset can therefore enter the menu without
performing the requested wipe. Test24 restores native argument handling and
those filesystem entries with wait-only flags, and disables the separate cache
log persister. This candidate preserves the proven kernel/DT and USB setup.
Full recovery readback verified the installation; boot, misc and both GPT
copies remained byte-identical. Native recovery then booted successfully. Its
exact F2FS formatter completed a RAM-backed format/mount/write/read/fsck test.
After explicit owner approval, the recovery UI formatted data as F2FS and cache
as ext4 and reported success. Fresh logs and cleared BCB verify that reset.
No userdata backup was made, following the owner’s preference.

## GApps installation

The owner requested Google apps. Official
[MindTheGapps Android 16 ARM64, September 15 release](https://github.com/MindTheGapps/16.0.0-arm64/releases/tag/MindTheGapps-16.0.0-arm64-20260915_222150)
is installed after a verified native factory reset. All 36 Google payload files
and 27 retained AT&T patch/firmware files passed hash, size, owner, mode and label
checks, together with the generated addon.d script. **First Android boot with
GApps is pending** at this checkpoint. Package size is 511,299,883 bytes, SHA-256
`d60f550e4dc96606644fbbf886a9892d1391a607225e861ceaef27bd999bc6a3`.
Complete post-install system readback and a separate on-phone SHA agree.
Boot, recovery, misc and both GPT copies are unchanged. The full resulting
system is verified on both computers; the local representation uses the exact
Test23 baseline and a 312,204,492-byte compressed delta. No userdata backup or
personal data publication was performed. The temporary package was removed
from the phone and its pending recovery command is clear.

The phone is SDK 36/ARM64 and has about 4.25 GB free before installation in its monolithic system
filesystem. The package expands to 1,138,465,773 bytes before installation.

Because Android has already completed setup, the
[Lineage installation instructions](https://github.com/LineageOS/lineage_wiki/blob/4edbf1aabad1ed98ab265ced65788a47c1c9e2bb/pages/gapps.md#L17-L22)
require a fresh factory reset before installing GApps. The owner approved that
reset and its successful completion is now verified in native recovery logs.
Do not reinstall the original ROM ZIP over the AT&T adaptations. After
GApps installation, verify payload files and retained patches explicitly: this
installer can finish without propagating every copy error.

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

- [Test24 recovery and GApps preparation files](../archive/att-port-2026-10/test24/README.md): bounded recovery writer, builder, diagnostics, tests and reviews; runtime validation remains pending.

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
