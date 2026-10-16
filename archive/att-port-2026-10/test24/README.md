# Test24 recovery preparation and GApps staging

These are historical source and review records for the recovery correction
and GApps preparation described in [AGENTS sections54–55](../../../AGENTS.md)
and the [current port status](../../../docs/ATT_PORT_STATUS.md).

The original diagnostic recovery supplied command-line arguments that caused
native recovery to skip BCB/cache operation arguments. The candidate restores
native argument handling, cache/data filesystem entries, and native ownership
of cache logging. Kernel, DT, native binaries and USB policy are preserved.

The source files have `.txt` suffixes intentionally. They contain real hardware
operations and device-specific hashes. They are **not a portable installation
tool**. Local paths, host/session names and private identifiers are replaced;
these published review records cannot satisfy the original execution gates.
The parent archive contains dependencies used during the investigation.

The separate RAM checker formats only a temporary regular file and mounts its
owned loop device. Its preparation and cleanup tests do not establish that
native factory reset works on the phone. Consult the current status before
using the recovery's wipe function.

GApps metadata identifies the official Android16 ARM64 package and every ZIP
member hash. Package staging is not an installation result. The package itself,
recovery/ROM images, signing keys, partition backups and raw phone logs are
not included. Download GApps from the official release linked in the status
document, not from a historical copied URL in a script.

`manifest.json` records the original and public-copy hashes for17 files,
including all sanitizer transformations. Preparation-time metadata remains
unchanged when later hardware results are added to AGENTS/status documentation.
