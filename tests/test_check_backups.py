import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_backups.py"
SPEC = importlib.util.spec_from_file_location("check_backups", SCRIPT)
backups = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backups)


def gpt_fixture(overlap=False):
    array = bytearray(128 * 128)
    for i, (name, low, high) in enumerate((
            ("boot", 2048, 133119), ("recovery", 133120, 264191),
            ("misc", 264000 if overlap else 264192, 264195))):
        struct.pack_into("<16s16sQQQ72s", array, i * 128, b"type-guid-16byte",
                         bytes([i + 1]) * 16, low, high, 0, name.encode("utf-16-le"))
    header = bytearray(struct.pack("<8sIIIIQQQQ16sQIII", b"EFI PART", 0x10000,
                                  92, 0, 0, 1, 300000, 34, 299966, b"disk-guid-16byte",
                                  2, 128, 128, zlib.crc32(array)))
    struct.pack_into("<I", header, 16, zlib.crc32(header))
    return b"\0" * 512 + header.ljust(512, b"\0") + array


class BackupChecks(unittest.TestCase):
    def test_initial_header_determines_full_read_length(self):
        initial = gpt_fixture()[:1024]
        result = backups.read_header(initial)
        self.assertEqual(result["primary_dump_sectors"], 34)
        self.assertEqual(result["backup_header_sector"], 300000)
        with self.assertRaisesRegex(ValueError, "truncated"):
            backups.read_gpt(initial)

    def test_gpt_bounds_crc_and_partition_sizes(self):
        result = backups.read_gpt(gpt_fixture())
        self.assertEqual(result["partitions"]["boot"]["bytes"], 64 * 1024 * 1024)
        self.assertEqual(result["partitions"]["recovery"]["start_sector"], 133120)
        self.assertEqual(result["partitions"]["misc"]["bytes"], 2048)

    def test_corrupted_header_fails(self):
        data = bytearray(gpt_fixture())
        data[512 + 56] ^= 1
        with self.assertRaisesRegex(ValueError, "header CRC"):
            backups.read_gpt(data)

    def test_corrupted_array_fails(self):
        data = bytearray(gpt_fixture())
        data[1024 + 60] ^= 1
        with self.assertRaisesRegex(ValueError, "array CRC"):
            backups.read_gpt(data)

    def test_truncated_array_fails(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            backups.read_gpt(gpt_fixture()[:-1])

    def test_overlap_fails_even_with_correct_crc(self):
        with self.assertRaisesRegex(ValueError, "overlapping partitions"):
            backups.read_gpt(gpt_fixture(overlap=True))

    def test_backup_lengths_hashes_and_misc_flag(self):
        # Small synthetic partition sizes exercise file validation without a
        # 128 MiB fixture. Real GPT parsing separately enforces 64 MiB above.
        gpt = {"partitions": {name: {"bytes": 2048} for name in backups.REQUIRED}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in backups.REQUIRED:
                (root / (name + ".bin")).write_bytes(b"\0" * 2048)
            (root / "misc.bin").write_bytes(b"boot-recovery".ljust(2048, b"\0"))
            result = backups.check_files(gpt, root)
            self.assertTrue(result["misc"]["boot_recovery_flag"])
            self.assertEqual(len(result["boot"]["sha256"]), 64)
            (root / "boot.bin").write_bytes(b"\0" * 2047)
            with self.assertRaisesRegex(ValueError, "wrong size"):
                backups.check_files(gpt, root)


if __name__ == "__main__":
    unittest.main()
