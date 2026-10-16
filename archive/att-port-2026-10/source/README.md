# Historical investigation source

This directory preserves the preparation, inspection, capture, and guarded
write code used during the October 2026 AT&T Z999 investigation. Read the
repository's [AGENTS.md](../../../AGENTS.md) for outcomes and remaining limits.
An older candidate's script is evidence of an experiment, not a recommendation
to repeat it or a claim that its image booted.

Python sources are published as `*.py.txt`. They are reference text, not
installed tools or a supported flashing workflow. Some originals perform
device operations at module import or script startup. In particular,
`test_reader_recovery_route.py` is a hardware experiment despite its name;
do not discover or execute this archive as a unit-test suite.

The runnable offline utilities are in [scripts](../../../scripts):
`fujisan_image.py`, `check_backups.py`, and `initcall_order.py`. Their
self-contained tests are in [tests](../../../tests).

## Provenance and redaction

The export manifest records each private source's original SHA-256, the public
copy's SHA-256, and the transformations applied. Machine-specific home paths,
SSH configuration locations, and connection aliases are replaced with neutral
placeholders. Any published logger text uses a placeholder for the private
cache filesystem UUID. Synthetic identifiers in offline tests are fixtures.

Original image hashes, instruction offsets, partition geometry, and review
hashes remain visible because they explain precisely what was checked. A
SHA-256 digest is not the corresponding firmware, key, device identifier, or
backup contents. Existing source and review hash guards are deliberately not
rewritten to match redacted copies. Thus a public copy does not inherit the
private file's reviewed identity, and copying it back into the old environment
does not recreate a validated transaction.

No signing keys, Firehose programmers, stock firmware, ROM/TWRP binaries,
partition backups, raw phone captures, extracted native libraries, or
base64-encoded system-block deltas belong in this archive. A generated JSON
file is not safe merely because it is text: the staged delta JSON files contain
real image block bytes. Generated logger payloads can also contain the private
cache UUID. Full source images and private receipts must be supplied and
verified separately to reproduce an experiment.

Small expected-instruction byte sequences, authored assembly, Firehose XML,
and init/service text embedded in preparation code document the transformation;
they are distinct from distributing an extracted executable or firmware image.
Preserve any source notices and attribution when retaining source excerpts.

## Inventory guide

The initial inventory comprised 155 top-level Python sources. Useful groups
and representative files are listed below; the export manifest is the exact
file inventory.

| Group | Representative source | Interpretation |
|---|---|---|
| Published image parsing and preparation | `prepare_los23_recovery_kernel.py`, `prepare_los23_recovery_ramdisk.py`, `prepare_los23_full_boot_kernel.py`, `prepare_los23_att_gpu.py` | Preserve each published image's own kernel/DT/ramdisk; apply guarded changes to private inputs. |
| Full Android startup and native diagnostics | `prepare_los23_full_security.py`, `prepare_los23_full_usb.py`, `prepare_test21_gatekeeper_diagnostic.py`, `prepare_test22_gpu_meminfo_diagnostic.py`, `prepare_test22_gatekeeper_service.py`, `prepare_test23_usb_port_service.py` | Exact input hashes and bounded edits; security/credential limitations remain documented in AGENTS. Test23 restores the port HAL disabled by the earlier USB diagnostic. |
| System and boot assembly | `assemble_test20_boot.py`, `assemble_test20_system.py`, `assemble_test22_system.py`, `assemble_test23_system.py` | Local image construction, metadata checks, and full output validation; requires omitted private inputs and receipts. |
| Bounded runtime logging | `prepare_test20_logging.py`, `prepare_test22_logging.py`, associated authored shell/init text | RAM capture and exclusive cache persistence; requires freshly verified cache identity. Test22 corrects the persister startup timing. |
| Live observation | `capture_test22_adb.py`, `capture_test23_android_supplement.py`, `capture_test23_display_modes.py` | Read-only capture logic with identity, time, and output bounds. Captures themselves remain private. |
| EDL transport and evidence | `sahara_load.py`, `firehose_read.py`, `backup_session.py`, `edl_full_audit.py` | Device-facing protocol implementations and backup checks, not offline utilities. |
| Writes, installation, and resets | `firehose_boot_test.py`, `adb_recovery_control.py`, `install_test20_adb.py`, `run_test22_edl_system.py`, `run_test23_edl_system.py`, `run_test22_recovery_bcb.py`, `reset_test23_verified.py` | Historical, exact-device transactions gated by backups and readback. Do not reuse old partition/hash assumptions on another phone or current state. |
| Staging and two-computer verification | `stage_test20_package.py`, `stage_test22_delta.py`, `stage_test23_delta.py`, `verify_test23_before_evidence.py`, `verify_test23_after_evidence.py` | Machine/session-specific orchestration; some run commands at import. |
| Offline failure tests | `test_adb_recovery_control.py`, `test_test22_edl_system.py`, `test_test23_edl_system.py`, `test_test23_reset_guards.py`, `test_test20_logging_mocks.py` | Mocked guards and protocol behavior; requirements vary and some depend on private payloads. Not evidence of a new live write. |
| Superseded experiments | `prepare_test03_*` through `prepare_test18_*`, corresponding captures/runners/resets and earlier variants | Preserve the diagnostic chain, including unflashed or abandoned variants; consult AGENTS before interpreting a result. |

## Dependencies and reconstruction limits

The original private directory was a sibling of the repository. Several
builders added `../ZTE-Axon-M-Flash-Tool/scripts` to Python's import path and
imported other private modules from the same directory. The text archive
deliberately does not reproduce that import layout.

Important dependencies include:

- `prepare_los23_full_boot_kernel.py` imports the LOS recovery kernel
  transformation; both depend on `fujisan_image.py`.
- `prepare_test20_logging.py` imports the verified cache identity loader from
  `prepare_los23_recovery_ramdisk.py` and transforms the authored Test19 shell
  collector. Later logging preparation reads the exact earlier image/scripts.
- `assemble_test22_system.py` and `assemble_test23_system.py` reuse helpers from
  `assemble_test20_system.py`; native patches, RC inputs, manifests, and image
  files must have the expected private identities.
- `capture_test23_android_supplement.py` and several other captures import the
  bounded `Capture` implementation from `capture_test22_adb.py`.
- EDL runners use `firehose_read.py`, `firehose_boot_test.py`, and repository
  backup/image validation helpers. The BCB runner also imports the Test22
  system runner. These are hardware operations, not test fixtures.

Depending on the experiment, the original environment required Python 3,
OpenSSL, adb 29.0.6, PyUSB/libusb, e2fsprogs `debugfs`/`e2fsck`, macOS APFS
clone support, or clang's AArch64 assembler. Some older LED builders also need
the accompanying authored `.S` source and exact extracted kernel symbol data.
Merely installing these dependencies does not satisfy the missing firmware,
signing, backup, independent review, or current-device gates.

## Public validation

From the repository root, validate the supported offline utilities with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

The source archive can be checked without executing it: verify every public
file against the export manifest, parse Python text with `ast.parse`, inspect
shell text with `sh -n` where placeholders preserve syntax, and scan for
private paths, actual device identifiers, UUIDs, keys, credentials, binary
magic, and encoded image payloads. Do not import archived modules to check
syntax. Do not run their command-line help, since some originals perform work
before argument handling.

The repository's 40 offline tests passed during this publication review. That
result covers the three offline tools; it does not make historical phone
scripts safe to run or validate an arbitrary replacement image.
