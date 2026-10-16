import gzip
import hashlib
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fujisan_image.py"
SPEC = importlib.util.spec_from_file_location("fujisan_image", SCRIPT)
image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(image)


def test_dtb():
    """Independent minimal FDT fixture with two-cell memory addressing."""
    strings = b"#address-cells\0#size-cells\0qcom,msm-id\0qcom,board-id\0ranges\0"
    structure = bytearray(struct.pack(">I", 1) + b"\0" * 4)
    for name, data in ((b"#address-cells", struct.pack(">I", 2)),
                       (b"#size-cells", struct.pack(">I", 2)),
                       (b"qcom,msm-id", bytes.fromhex("0000013100010001")),
                       (b"qcom,board-id", bytes.fromhex("0000006600000000"))):
        structure.extend(struct.pack(">3I", 3, len(data), strings.index(name + b"\0")) + data)
    structure.extend(struct.pack(">I", 1) + b"reserved-memory\0")
    for name, data in ((b"#address-cells", struct.pack(">I", 2)),
                       (b"#size-cells", struct.pack(">I", 2)), (b"ranges", b"")):
        structure.extend(struct.pack(">3I", 3, len(data), strings.index(name + b"\0")) + data)
    structure.extend(struct.pack(">3I", 2, 2, 9))
    return struct.pack(">10I", 0xd00dfeed, 56 + len(structure) + len(strings),
                       56, 56 + len(structure), 40, 17, 16, 0, len(strings), len(structure)) + b"\0" * 16 + structure + strings


def cpio_file(name, data=b"", mode=0o100644, inode=1):
    fields = [inode, mode, 0, 0, 1, 1234, len(data), 0, 0, 0, 0, len(name) + 1, 0]
    header = b"070701" + "".join("{:08x}".format(n) for n in fields).encode()
    header += name.encode() + b"\0"
    result = header + b"\0" * (-len(header) % 4) + data
    return result + b"\0" * (-len(result) % 4)


def ramdisk():
    data = cpio_file("init.rc", b"on boot\n    setprop test.value yes\n", inode=42)
    data += cpio_file("sbin/reader", b"../bin/reader", mode=0o120777, inode=43)
    data += cpio_file("TRAILER!!!", mode=0)
    return gzip.compress(data, mtime=0)


def boot_payload(style="aosp"):
    kernel = gzip.compress(b"Linux version 3.18.71-test\0" + bytes(range(256)), mtime=0) + test_dtb()
    rd = ramdisk()
    header = bytearray(4096)
    header[:8] = b"ANDROID!"
    struct.pack_into("<10I", header, 8, len(kernel), 0x80008000, len(rd),
                     0x81000000, 0, 0x80f00000, 0x80000100, 4096, 0, 0)
    header[64:73] = b"test=boot"
    digest = hashlib.sha1()
    for section in (kernel, rd, b""):
        digest.update(section)
        digest.update(struct.pack("<I", len(section)))
    if style == "qcom-dt-size":
        digest.update(b"\0" * 4)
    header[576:596] = digest.digest()
    return bytes(header) + kernel.ljust(4096, b"\0") + rd.ljust(4096, b"\0")


def properties(node, prefix=""):
    path = prefix + "/" + node.name
    result = {(path, name): value for name, value in node.props.items()}
    for child in node.children:
        result.update(properties(child, path))
    return result


class ImageFormatTests(unittest.TestCase):
    def test_both_boot_id_formats_roundtrip_and_recalculate(self):
        for style in ("aosp", "qcom-dt-size"):
            original = boot_payload(style)
            boot = image.BootImage(original)
            self.assertEqual(boot.id_style, style)
            self.assertEqual(boot.rebuild(), original)
            changed = image.BootImage(boot.rebuild(ramdisk=boot.ramdisk + b"123"))
            self.assertEqual(changed.id_style, style)
            self.assertNotEqual(changed.header[576:596], boot.header[576:596])

    def test_truncated_payload_and_new_headers_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            image.BootImage(boot_payload()[:-1])
        data = bytearray(boot_payload())
        struct.pack_into("<I", data, 40, 1)
        with self.assertRaisesRegex(ValueError, "header v0"):
            image.BootImage(data)

    def test_long_command_line_crosses_extra_field(self):
        boot = image.BootImage(boot_payload())
        cmdline = "a" * 510 + " " + "b" * 600
        changed = image.BootImage(boot.rebuild(cmdline=cmdline))
        self.assertEqual(changed.cmdline, cmdline)
        self.assertEqual(changed.kernel, boot.kernel)
        self.assertEqual(changed.ramdisk, boot.ramdisk)
        with self.assertRaisesRegex(ValueError, "1535 bytes"):
            boot.rebuild(cmdline="a" * 1536)

    def test_att_dtb_changes_preserve_all_original_properties(self):
        tree = image.Fdt(test_dtb())
        original = properties(tree.root)
        self.assertTrue(tree.add_att_reservation())
        changed = image.Fdt(tree.serialize())
        self.assertEqual(changed.free_tail, 8192)
        self.assertEqual(changed.reserve, tree.reserve)
        self.assertTrue(original.items() <= properties(changed.root).items())
        reservation = changed.root.child("reserved-memory").child("ap_share_region@9ff00000")
        self.assertEqual(reservation.props["reg"], struct.pack(">4I", 0, 0x9ff00000, 0, 0x100000))
        self.assertEqual(reservation.props["no-map"], b"")
        self.assertFalse(changed.add_att_reservation())
        self.assertEqual(changed.serialize(), tree.serialize())

    def test_conflicting_reserved_memory_rejected(self):
        tree = image.Fdt(test_dtb())
        node = image.Node("conflict@9fe00000")
        node.props["reg"] = struct.pack(">4I", 0, 0x9fe00000, 0, 0x200000)
        tree.root.child("reserved-memory").children.append(node)
        with self.assertRaisesRegex(ValueError, "conflicts"):
            tree.add_att_reservation()

    def test_malformed_dtb_offsets_and_truncation_rejected(self):
        data = bytearray(test_dtb())
        struct.pack_into(">I", data, 12, len(data) + 4)
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            image.Fdt(data)
        with self.assertRaisesRegex(ValueError, "FDT v17"):
            image.Fdt(test_dtb()[:-1])

    def test_appended_dtbs_preserve_kernel_gzip_bytes(self):
        compressed = gzip.compress(b"unchanged machine code", mtime=0)
        kernel = compressed + test_dtb() * 2
        actual, raw, trees = image.kernel_dtbs(kernel)
        self.assertEqual(actual, compressed)
        self.assertEqual(raw, b"unchanged machine code")
        self.assertEqual(len(trees), 2)
        with self.assertRaisesRegex(ValueError, "unexpected data"):
            image.kernel_dtbs(kernel + b"unexpected")

    def test_reader_preserves_every_other_archive_record_and_file_mode(self):
        old = image.cpio_entries(gzip.decompress(ramdisk()))
        patched = image.patch_reader(ramdisk())
        new = image.cpio_entries(gzip.decompress(patched))
        self.assertEqual(old[1:], new[1:])
        self.assertEqual(old[0][1][:6], new[0][1][:6])
        self.assertEqual(new[0][2], old[0][2] + image.READER_PATCH)
        self.assertEqual(image.patch_reader(patched), patched)

    def test_reader_rejects_duplicate_or_missing_init(self):
        data = cpio_file("init.rc") * 2 + cpio_file("TRAILER!!!")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            image.patch_reader(gzip.compress(data))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            image.patch_reader(gzip.compress(cpio_file("TRAILER!!!")))

    def test_duplicate_directory_requires_explicit_name_and_preserves_records(self):
        first = cpio_file("dev", mode=0o040755, inode=11)
        middle = cpio_file("fstab.qcom", b"unchanged", inode=12)
        second = cpio_file("dev", mode=0o040755, inode=13)
        trailer = cpio_file("TRAILER!!!", mode=0)
        archive = first + middle + second + trailer
        with self.assertRaisesRegex(ValueError, "duplicate"):
            image.cpio_entries(archive)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            image.cpio_entries(archive, allow_duplicate_directories={"other"})
        entries = image.cpio_entries(archive, allow_duplicate_directories={"dev"})
        self.assertEqual([entry[0] for entry in entries],
                         ["dev", "fstab.qcom", "dev", "TRAILER!!!"])
        self.assertEqual([entry[3] for entry in entries], [first, middle, second, trailer])

    def test_duplicate_directory_option_never_allows_file_or_symlink_replacement(self):
        for mode, content in ((0o100644, b""), (0o120777, b"elsewhere")):
            with self.subTest(mode=mode):
                archive = cpio_file("dev", content, mode=mode) * 2 + cpio_file("TRAILER!!!")
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    image.cpio_entries(archive, allow_duplicate_directories={"dev"})

    def test_duplicate_directory_rejects_metadata_changes_and_nonempty_payload(self):
        first = cpio_file("dev", mode=0o040755, inode=11)
        for second in (cpio_file("dev", mode=0o040700, inode=12),
                       cpio_file("dev", b"unexpected", mode=0o040755, inode=12),
                       cpio_file("dev", mode=0o100755, inode=12)):
            with self.subTest(second=second):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    image.cpio_entries(first + second + cpio_file("TRAILER!!!"),
                                       allow_duplicate_directories={"dev"})

    def test_duplicate_directory_rejects_third_occurrence(self):
        archive = b"".join(cpio_file("dev", mode=0o040755, inode=i) for i in (1, 2, 3))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            image.cpio_entries(archive + cpio_file("TRAILER!!!"),
                               allow_duplicate_directories={"dev"})

    def test_charger_preserves_archive_and_does_not_change_usb_policy(self):
        old = image.cpio_entries(gzip.decompress(ramdisk()))
        patched = image.patch_charger(ramdisk())
        new = image.cpio_entries(gzip.decompress(patched))
        self.assertEqual(old[1:], new[1:])
        self.assertEqual(old[0][1][:6], new[0][1][:6])
        self.assertEqual(new[0][2], old[0][2] + image.CHARGER_PATCH)
        self.assertNotIn(b"sys.usb.config", image.CHARGER_PATCH)
        self.assertEqual(image.patch_charger(patched), patched)

    def test_reader_rejects_truncated_cpio(self):
        with self.assertRaisesRegex(ValueError, "truncated cpio"):
            image.patch_reader(gzip.compress(cpio_file("init.rc", b"123456")[:-5]))


class SigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.key, cls.cert = cls.directory / "test.key", cls.directory / "test.pem"
        subprocess.run(["openssl", "req", "-new", "-x509", "-newkey", "rsa:2048",
                        "-nodes", "-days", "1", "-subj", "/CN=Ephemeral unit test/",
                        "-keyout", str(cls.key), "-out", str(cls.cert)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_signed_target_length_and_content_verified(self):
        payload = boot_payload()
        for target in ("/boot", "/recovery"):
            signed = image.sign_image(payload, target, self.key, self.cert)
            info = image.verify_signature(payload, signed[len(payload):])
            self.assertEqual(info["target"], target)
            self.assertEqual(info["length"], len(payload))
            with self.assertRaisesRegex(ValueError, "OpenSSL failed"):
                image.verify_signature(payload[:-1] + b"\x01", signed[len(payload):])
            with self.assertRaisesRegex(ValueError, "length disagrees"):
                image.verify_signature(payload[:-1], signed[len(payload):])

    def test_padding_allowed_but_unknown_trailer_rejected(self):
        payload = boot_payload()
        signed = image.sign_image(payload, "/boot", self.key, self.cert)
        image.verify_signature(payload, signed[len(payload):] + b"\0" * 4096)
        with self.assertRaisesRegex(ValueError, "zero padding"):
            image.verify_signature(payload, signed[len(payload):] + b"extra")

    def test_cli_does_not_overwrite_source(self):
        source = self.directory / "source.img"
        data = image.sign_image(boot_payload(), "/boot", self.key, self.cert)
        source.write_bytes(data)
        proc = subprocess.run([sys.executable, str(SCRIPT), "patch", str(source), str(source),
                               "--target", "/boot", "--key", str(self.key), "--certificate", str(self.cert)],
                              capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"already exists", proc.stderr)
        self.assertEqual(source.read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
