# AT&T Axon M port investigation files — October 2026

This archive preserves the source files used during tests 01–23, including
unsuccessful experiments. The verified result is **Test23 booting the published
LineageOS 23.2 release on an AT&T Z999**, with automatic single/wide display
switching. Read [current status](../../docs/ATT_PORT_STATUS.md) and the complete
[findings](../../AGENTS.md) before interpreting individual experiments.

## Contents

- [source/](source/): 155 Python source files, including image builders,
  binary-patch preparation, Sahara/Firehose transports, ADB diagnostics,
  recovery-entry experiments, verification helpers and mock tests.
- [payloads/](payloads/): 18 authored diagnostic shell/init source files.
  Six authored assembly sources preserve the earlier LED/checkpoint experiments.
- [metadata/](metadata/): 25 preparation manifests and independent reviews for
  the successful path. These preserve preparation-time statements such as
  `hardware_tested: false`; later runtime results are in the status document.
- [manifest.json](manifest.json): file inventory, original/public SHA-256 values,
  sizes and the redactions applied to each exported file.

The `.py.txt`, `.sh.txt` and `.rc.txt` suffixes deliberately make these reference
files rather than an executable installation kit. Machine-specific paths and
session names use placeholders; private filesystem UUIDs are redacted. Internal
hash gates still describe the original private inputs. Published copies must
not be substituted into those gates or represented as the exact tested private
environment. Some older scripts perform actions at module import or have
hardware-oriented names beginning with `test_`; do not run test discovery here.

The runnable, offline tools are [scripts/fujisan_image.py](../../scripts/fujisan_image.py),
[scripts/check_backups.py](../../scripts/check_backups.py) and
[scripts/initcall_order.py](../../scripts/initcall_order.py). Their synthetic
tests are under [tests/](../../tests/); they do not use the phone.

## Reading the successful path

| Stage | Source references |
|---|---|
| Published 4.4 kernel, DT and USB supplier fixes | `prepare_test17_usb_supplier.py.txt`, `prepare_test18_cleanup.py.txt`, `prepare_los23_full_boot_kernel.py.txt` |
| Original LOS image preparation | `extract_los23_system.py.txt`, `prepare_los23_att_gpu.py.txt`, `assemble_test20_boot.py.txt`, `assemble_test20_system.py.txt` |
| Boot diagnostics and unavailable services | `prepare_los23_full_security.py.txt`, `prepare_test21_gatekeeper_diagnostic.py.txt`, `prepare_test22_gpu_meminfo_diagnostic.py.txt`, `assemble_test22_system.py.txt` |
| Final USB port-service boot fix | `prepare_test23_usb_port_service.py.txt`, `assemble_test23_system.py.txt` |
| Backup, guarded delta write and readback design | `audit_test23_before.py.txt`, `run_test23_edl_system.py.txt`, `verify_test23_before_evidence.py.txt`, `verify_test23_after_evidence.py.txt` |
| Actual recovery-slot selection | `run_test22_recovery_bcb.py.txt`, `capture_test22_recovery_bcb_v3.py.txt` |
| Boot and second-screen verification | `capture_test23_android_supplement.py.txt`, `capture_test23_display_modes.py.txt` |

All filenames in that table are inside `source/`. Earlier versions and failed
approaches are retained to explain the investigation, not recommended for use.
The archive does not contain a supported updater or a ready-to-flash ROM ZIP.

## Inputs kept outside Git

ROM/recovery images, stock firmware, the Firehose programmer, partition backups,
signing/SSH keys, raw device logs and encoded system-block delta payloads remain
private. Obtain upstream binaries from the sources in the status document;
never substitute China/DoCoMo bootloader firmware on an AT&T unit. Device writes
require newly verified geometry, backups, exact source hashes and independent
review. The original clean-install format authorization is historical and must
not be reused to erase a currently working phone.

The scripts use Python 3.9+; individual historical paths additionally use
OpenSSL, e2fsprogs, PyUSB, adb 29.0.6, recovered kernel symbols or external
disassembly tools. Dependencies and private artifacts are referenced in source
but are not vendored. See [source notes](source/README.md) for more detail.

## Recovery and GApps follow-up

[Test24](test24/README.md) records the native recovery argument/fstab repair.
[Test25](test25/README.md) records the successful native reset, original GApps
installation, file verification, and complete readback tooling. Each has a
separate sanitized-source manifest; later hardware outcomes are in the status
document. No userdata or raw partition contents are published.
