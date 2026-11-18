# ZTE Axon M Flash Tool

Scripts, a corrected QFIL config, and research notes for the **ZTE Axon M** (Z999, codename `fujisan`, Snapdragon 821 / MSM8996). The original Windows tool fixes QFIL's `SAHARA_NAK_INVALID_CMD` / "Sahara protocol error"; the repository also documents adapting the published unofficial LineageOS 23.2 release to the AT&T model.

**Current AT&T port status — October 17, 2026:** Test23 boots full Android 16. Seven observations over **185.767 seconds** verified boot completion, an unchanged `system_server` process, unlocked user 0, the launcher, and adb-only peripheral USB. The owner confirms both screens work: single while folded, spanning both while unfolded. This remains a **diagnostic build, not a production-ready ROM**: SELinux is permissive, adb runs as root without authentication, credential support is unavailable, and camera crashes remain.

Start with [the AT&T port status](docs/ATT_PORT_STATUS.md) for verified results, exact image hashes, recovery entry, limitations, and next priorities. [AGENTS.md](AGENTS.md) retains the chronological investigation. **Patched TWRP and LOS image downloads are now available in the [October 17 experimental release](https://github.com/channelramble/ZTE-Axon-M-Flash-Tool/releases/tag/att-z999-los23.2-test25-20261017).** Read the [asset targets, checksums, total work summary, and limitations](docs/RELEASE_2026-10-17.md) first. The release includes vanilla and GApps system variants, LOS boot/recovery, and the optional BOOT-target TWRP control. Private keys, programmers, bootloader dumps and userdata are excluded. This is not a one-click LineageOS installer.

> **Warning:** EDL flashing writes straight to the phone's storage. The wrong file or sector can brick it. Use this at your own risk.

## Flashing guides

Platform-specific setup and flashing walkthroughs live under `docs/`, so each can be maintained on its own:

- **[Windows (QFIL)](docs/WINDOWS_SETUP.md)** — the original QFIL workflow (TWRP 3.2.3-0, QFIL 2.0.1.9, Windows 10): requirements, the `SAHARA_NAK_INVALID_CMD` fix, the `FlashTool.cmd` menu, flashing TWRP, and restoring a recovery that won't boot.
- **[macOS (bkerler/edl)](docs/MACOS_SETUP.md)** — a macOS-native flow using [`bkerler/edl`](https://github.com/bkerler/edl) instead of QFIL, including the AT&T LineageOS 23.2 install and a `dd`-over-adb workaround for the firehose system-write collapse on the ~7 GB image.

Shared background for both: [FINDINGS.md](docs/FINDINGS.md) (evidence) and [PARTITIONS.md](docs/PARTITIONS.md) (partition layout).

## Continuing the Android 16 port

For the **Android 16 / TWRP 3.7.0 AT&T port**, read
[the current status](docs/ATT_PORT_STATUS.md), then [AGENTS.md](AGENTS.md)
for the detailed evidence. The older TWRP 3.2.3 log-reader workflow requires
**platform-tools 29.0.6**; the setup menu's adb selection predates that workflow.

The read-only Python helper below lists level 6/7 initcalls in pointer order
from the **exact debug build's** `System.map` (Python 3.9+, no dependencies):

```sh
python3 scripts/initcall_order.py /path/to/System.map
python3 scripts/initcall_order.py /path/to/System.map --level 6 --json
```

It checks table boundaries and completeness, including synchronous initcalls.
Function names are inferred from pointer symbols, including the kernel's Clang
LTO naming format. Confirm them against `vmlinux` or `initcall_debug` logs before
using `initcall_blacklist`. It does not select a blacklist, build an image, or
connect to the phone. Test it with `python3 -m unittest discover -s tests`.

[Local preparation](docs/LOCAL_PREPARATION.md) covers the offline
`fujisan_image.py` tool, signed image candidates, and `check_backups.py` for
validating saved GPT/partition reads. Its early test descriptions are historical;
the status page and latest AGENTS sections take precedence. Test18 TWRP 3.7 and
Test19 LineageOS recovery boot with adb. Test23 full Android retains the Test20
boot image and Test19-derived recovery, adds the reviewed Gatekeeper and optional
GPU-statistics diagnostics, and restores the USB port HAL needed to finish boot.
Actual recovery-slot entry is verified through a menu-only BCB request; the
bootloader menu's recovery route remains unreliable. Keep downloaded/generated
images and signing keys outside this repo.

## Credits

- **Unjustified Dev**: TWRP for fujisan and the working firehose programmer
- **deadman96385**: [Axon M stock firmware and firehose thread](https://xdaforums.com/t/rom-zte-axon-m-stock-firmware-firehose.3909847/) and the original QFIL guide
- XDA thread contributors (ZeroTheSavior, Drakosha, sybob, FF7CloudsNobody, Corekai and others) for the rawprogram typo, dm-verity and flashing tips

## License

MIT for the scripts and docs in this repository (see [LICENSE](LICENSE)). QPST/QFIL, Qualcomm drivers, firehose programmers and TWRP builds belong to their respective owners.
