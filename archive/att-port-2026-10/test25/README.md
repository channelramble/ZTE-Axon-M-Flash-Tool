# Test25: native recovery reset and Android 16 GApps

These are sanitized historical sources and review records. They are reference
text, **not a portable installation tool or authorization to execute**. Sources
are bound to one AT&T Z999, exact images and private evidence. See
[the current port status](../../../docs/ATT_PORT_STATUS.md) and
[AGENTS sections 54–56](../../../AGENTS.md) for actual hardware results.

The owner-approved native factory reset completed successfully. The original,
checksum-verified MindTheGapps updater ran once. A separate read-only check
verified all36 Google payload files,27 retained AT&T files and addon.d metadata.
Android startup with GApps is tracked in the status document.

Important continuation details:

- Recovery exposes multiple native recovery PIDs; validate the complete set.
- Set `TMPDIR=/tmp` for verifier here-documents after reset. Recovery's inherited
  `/data/local/tmp` does not exist while data is unmounted.
- The recorded installer wrapper sends fd3 to a regular log. Original
  `ui_print` reopens that descriptor with truncation, losing earlier messages.
  Preserve the limitation; do not rerun installation to recreate the log.
  Full file verification, rather than installer exit0, established the result.
- The initial after-reader needs `awk`, absent in this native recovery. V2
  replaces only those two expressions with reviewed shell loops. The binary
  stream and full native/host SHA checks are unchanged.
- The offline delta helper stores changed system blocks privately and verifies
  the entire reconstructed SHA without producing another full image. It needs
  its exact complete baseline permanently. No delta payload is published here.

The manifest records private-source and sanitized-copy hashes separately.
No userdata, raw device logs, partition contents, ROM/recovery binaries,
programmers, signing keys or upstream Google binaries are included.
