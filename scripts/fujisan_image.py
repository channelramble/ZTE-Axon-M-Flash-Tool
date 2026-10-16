#!/usr/bin/env python3
"""Offline tools for Fujisan Android v0 boot images; never accesses a device.

Python 3.9+ and OpenSSL are the only dependencies. The BootSignature encoding
follows AOSP system/extras/verity/BootSignature.java (android-7.1.2_r39).
Verifying a trailer checks its embedded certificate, not a vendor trust chain.
"""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zlib


PARTITION_LIMIT = 64 * 1024 * 1024
SHA256_RSA = bytes.fromhex("06092a864886f70d01010b")
READER_PATCH = b"""
# Fujisan AT&T pstore reader: see AGENTS.md section 6.3.
on charger
    trigger late-init

on property:sys.usb.config=mtp,adb
    setprop sys.usb.config adb
"""
CHARGER_PATCH = b"""
# Fujisan AT&T recovery: start the recovery UI after a USB-powered boot.
on charger
    trigger late-init
"""
ADB_ONLY_MARKER = b"# Fujisan AT&T diagnostic USB: disable MTP on startup."


def aligned(n, alignment):
    return (n + alignment - 1) // alignment * alignment


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def gzip_member(data):
    decoder = zlib.decompressobj(31)
    raw = decoder.decompress(data)
    if not decoder.eof:
        raise ValueError("truncated gzip member")
    used = len(data) - len(decoder.unused_data)
    return data[:used], raw, decoder.unused_data


def tlv(tag, data):
    n = len(data)
    length = bytes([n]) if n < 128 else n.to_bytes((n.bit_length() + 7) // 8, "big")
    if n >= 128:
        length = bytes([0x80 | len(length)]) + length
    return bytes([tag]) + length + data


def integer(n):
    value = n.to_bytes(max(1, (n.bit_length() + 7) // 8), "big")
    return tlv(2, (b"\0" if value[0] & 128 else b"") + value)


def der_item(data, offset=0):
    start = offset
    if offset + 2 > len(data):
        raise ValueError("truncated DER")
    tag, size = data[offset:offset + 2]
    offset += 2
    if size & 128:
        count = size & 127
        if not 1 <= count <= 4 or offset + count > len(data):
            raise ValueError("invalid DER length")
        encoded = data[offset:offset + count]
        size = int.from_bytes(encoded, "big")
        if encoded[0] == 0 or size < 128:
            raise ValueError("noncanonical DER length")
        offset += count
    end = offset + size
    if end > len(data):
        raise ValueError("truncated DER value")
    return tag, data[offset:end], data[start:end], end


def der_children(data):
    result, offset = [], 0
    while offset < len(data):
        item = der_item(data, offset)
        result.append(item)
        offset = item[3]
    return result


def openssl(*args, data=None):
    proc = subprocess.run(["openssl", *map(str, args)], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode:
        raise ValueError("OpenSSL failed: " + proc.stderr.decode(errors="replace").strip())
    return proc.stdout


def signature_info(trailer):
    tag, body, encoded, end = der_item(trailer)
    if tag != 0x30 or any(trailer[end:]):
        raise ValueError("expected a BootSignature followed only by zero padding")
    fields = der_children(body)
    if len(fields) != 5 or [f[0] for f in fields] != [2, 0x30, 0x30, 0x30, 4]:
        raise ValueError("invalid BootSignature fields")
    if fields[0][1] != b"\x01":
        raise ValueError("unsupported BootSignature format")
    if fields[2][1] not in (SHA256_RSA, SHA256_RSA + b"\x05\x00"):
        raise ValueError("only SHA256/RSA BootSignature is supported")
    attrs = der_children(fields[3][1])
    if len(attrs) != 2 or [f[0] for f in attrs] != [0x13, 2]:
        raise ValueError("invalid BootSignature attributes")
    target = attrs[0][1].decode("ascii")
    if target not in ("/boot", "/recovery"):
        raise ValueError("unsupported BootSignature target")
    return {"target": target, "length": int.from_bytes(attrs[1][1], "big"),
            "certificate": fields[1][2], "attributes": fields[3][2],
            "signature": fields[4][1], "trailer_bytes": len(encoded)}


def verify_signature(payload, trailer):
    info = signature_info(trailer)
    if info["length"] != len(payload):
        raise ValueError("BootSignature length disagrees with image header")
    public_key = openssl("x509", "-inform", "DER", "-pubkey", "-noout",
                         data=info["certificate"])
    openssl("rsa", "-pubin", "-noout", data=public_key)
    with tempfile.TemporaryDirectory(prefix="fujisan-verify-") as directory:
        key = Path(directory) / "public.pem"
        sig = Path(directory) / "signature"
        key.write_bytes(public_key)
        sig.write_bytes(info["signature"])
        openssl("dgst", "-sha256", "-verify", key, "-signature", sig,
                data=payload + info["attributes"])
    return info


def sign_image(payload, target, key, certificate):
    if target not in ("/boot", "/recovery"):
        raise ValueError("target must be /boot or /recovery")
    cert = openssl("x509", "-in", certificate, "-outform", "DER")
    attrs = tlv(0x30, tlv(0x13, target.encode("ascii")) + integer(len(payload)))
    sig = openssl("dgst", "-sha256", "-sign", key, data=payload + attrs)
    trailer = tlv(0x30, integer(1) + cert + tlv(0x30, SHA256_RSA) + attrs + tlv(4, sig))
    verify_signature(payload, trailer)  # also rejects mismatched key/certificate
    result = payload + trailer
    if len(result) > PARTITION_LIMIT:
        raise ValueError("signed image exceeds the 64 MiB partition limit")
    return result


class BootImage:
    def __init__(self, data):
        if len(data) < 1632 or data[:8] != b"ANDROID!":
            raise ValueError("not an Android v0 boot image")
        values = struct.unpack_from("<10I", data, 8)
        self.page = values[7]
        if values[8] != 0:
            raise ValueError("only header v0 with appended DTBs is supported")
        if self.page < 2048 or self.page > 65536 or self.page & (self.page - 1):
            raise ValueError("invalid boot page size")
        sizes = values[0], values[2], values[4]
        if not sizes[0] or not sizes[1]:
            raise ValueError("empty kernel or ramdisk")
        self.payload_length = self.page + sum(aligned(n, self.page) for n in sizes)
        if self.payload_length > len(data) or len(data) > PARTITION_LIMIT:
            raise ValueError("truncated or oversized boot image")
        self.original = data
        self.header = data[:self.page]
        self.payload = data[:self.payload_length]
        self.trailer = data[self.payload_length:]
        parts, offset = [], self.page
        for n in sizes:
            parts.append(data[offset:offset + n])
            offset += aligned(n, self.page)
        self.kernel, self.ramdisk, self.second = parts
        self.cmdline = (data[64:576] + data[608:1632]).split(b"\0", 1)[0].decode("ascii")
        # Older Qualcomm mkbootimg also hashes its zero dt_size word. The
        # published TWRP 3.7.0 uses that layout; LineageOS uses AOSP v0.
        self.id_style = next((style for style in ("aosp", "qcom-dt-size")
                              if self.digest(parts, style) == data[576:596]), None)
        self.id_valid = self.id_style is not None

    @staticmethod
    def digest(parts, style="aosp"):
        digest = hashlib.sha1()
        for part in parts:
            digest.update(part)
            digest.update(struct.pack("<I", len(part)))
        if style == "qcom-dt-size":
            digest.update(b"\0" * 4)
        return digest.digest()

    def rebuild(self, kernel=None, ramdisk=None, cmdline=None):
        parts = [self.kernel if kernel is None else kernel,
                 self.ramdisk if ramdisk is None else ramdisk, self.second]
        header = bytearray(self.header)
        for offset, part in zip((8, 16, 24), parts):
            struct.pack_into("<I", header, offset, len(part))
        header[576:608] = self.digest(parts, self.id_style) + b"\0" * 12
        if cmdline is not None:
            encoded = cmdline.encode("ascii")
            if b"\0" in encoded or len(encoded) > 1535:
                raise ValueError("command line must be ASCII, without NUL, at most 1535 bytes")
            padded = encoded.ljust(1536, b"\0")
            header[64:576], header[608:1632] = padded[:512], padded[512:]
        payload = bytes(header)
        for part in parts:
            payload += part + b"\0" * (aligned(len(part), self.page) - len(part))
        return payload


class Node:
    def __init__(self, name):
        self.name, self.props, self.children = name, {}, []

    def child(self, name):
        return next((node for node in self.children if node.name == name), None)


class Fdt:
    def __init__(self, blob):
        if len(blob) < 40:
            raise ValueError("truncated FDT header")
        magic, total, off_struct, off_strings, off_reserve, version, last, bootcpu, strings_len, struct_len = struct.unpack_from(
            ">10I", blob)
        if magic != 0xd00dfeed or total != len(blob) or version != 17 or last > 17:
            raise ValueError("unsupported or invalid FDT v17 header")
        if off_struct % 4 or off_reserve % 8:
            raise ValueError("unaligned FDT blocks")
        for offset, length in ((off_struct, struct_len), (off_strings, strings_len), (off_reserve, 16)):
            if offset < 40 or offset + length > total:
                raise ValueError("FDT block out of bounds")
        end = off_reserve
        while end + 16 <= total:
            entry = blob[end:end + 16]
            end += 16
            if not any(entry):
                break
        else:
            raise ValueError("unterminated FDT reservation map")
        spans = sorted([(0, 40), (off_reserve, end),
                        (off_struct, off_struct + struct_len), (off_strings, off_strings + strings_len)])
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            raise ValueError("overlapping FDT blocks")
        self.reserve = blob[off_reserve:end]
        self.last, self.bootcpu = last, bootcpu
        self.free_tail = total - max(end, off_struct + struct_len, off_strings + strings_len)
        strings = blob[off_strings:off_strings + strings_len]
        tree = blob[off_struct:off_struct + struct_len]
        stack, offset, self.root = [], 0, None
        while offset + 4 <= len(tree):
            token, = struct.unpack_from(">I", tree, offset)
            offset += 4
            if token == 1:
                stop = tree.find(b"\0", offset)
                if stop == -1:
                    raise ValueError("unterminated FDT node name")
                node = Node(tree[offset:stop].decode("ascii"))
                offset = aligned(stop + 1, 4)
                if stack:
                    if stack[-1].child(node.name) is not None:
                        raise ValueError("duplicate FDT node")
                    stack[-1].children.append(node)
                elif self.root is None and node.name == "":
                    self.root = node
                else:
                    raise ValueError("invalid FDT root")
                stack.append(node)
            elif token == 2:
                if not stack:
                    raise ValueError("unbalanced FDT END_NODE")
                stack.pop()
            elif token == 3:
                if not stack or offset + 8 > len(tree):
                    raise ValueError("invalid FDT property")
                size, nameoff = struct.unpack_from(">2I", tree, offset)
                offset += 8
                stop = strings.find(b"\0", nameoff)
                if nameoff >= len(strings) or stop == -1 or offset + size > len(tree):
                    raise ValueError("FDT property out of bounds")
                name = strings[nameoff:stop].decode("ascii")
                if name in stack[-1].props or stack[-1].children:
                    raise ValueError("duplicate or misplaced FDT property")
                stack[-1].props[name] = tree[offset:offset + size]
                offset = aligned(offset + size, 4)
            elif token == 4:
                continue
            elif token == 9:
                if stack or self.root is None or any(tree[offset:]):
                    raise ValueError("invalid FDT END")
                break
            else:
                raise ValueError("invalid FDT token")
        else:
            raise ValueError("missing FDT END")

    def serialize(self, free=8192):
        strings, structure, offsets = bytearray(), bytearray(), {}

        def emit(node):
            structure.extend(struct.pack(">I", 1))
            structure.extend(node.name.encode("ascii") + b"\0")
            structure.extend(b"\0" * (-len(structure) % 4))
            for name, value in node.props.items():
                if name not in offsets:
                    offsets[name] = len(strings)
                    strings.extend(name.encode("ascii") + b"\0")
                structure.extend(struct.pack(">3I", 3, len(value), offsets[name]))
                structure.extend(value)
                structure.extend(b"\0" * (-len(structure) % 4))
            for child in node.children:
                emit(child)
            structure.extend(struct.pack(">I", 2))

        emit(self.root)
        structure.extend(struct.pack(">I", 9))
        off_struct = 40 + len(self.reserve)
        off_strings = off_struct + len(structure)
        total = off_strings + len(strings) + free
        header = struct.pack(">10I", 0xd00dfeed, total, off_struct, off_strings,
                             40, 17, self.last, self.bootcpu, len(strings), len(structure))
        return header + self.reserve + structure + strings + b"\0" * free

    def add_att_reservation(self):
        parent = self.root.child("reserved-memory")
        if parent is None:
            parent = Node("reserved-memory")
            parent.props = {"#address-cells": self.root.props.get("#address-cells", struct.pack(">I", 2)),
                            "#size-cells": self.root.props.get("#size-cells", struct.pack(">I", 1)),
                            "ranges": b""}
            self.root.children.append(parent)
        if parent.props.get("ranges") != b"":
            raise ValueError("reserved-memory must have empty ranges")
        counts = []
        for key in ("#address-cells", "#size-cells"):
            value = parent.props.get(key, b"")
            if len(value) != 4 or int.from_bytes(value, "big") not in (1, 2):
                raise ValueError("unsupported reserved-memory cells")
            counts.append(int.from_bytes(value, "big"))
        address_bytes, size_bytes = (n * 4 for n in counts)
        width = address_bytes + size_bytes
        for child in parent.children:
            reg = child.props.get("reg", b"")
            if len(reg) % width:
                raise ValueError("malformed reserved-memory reg")
            for i in range(0, len(reg), width):
                address = int.from_bytes(reg[i:i + address_bytes], "big")
                size = int.from_bytes(reg[i + address_bytes:i + width], "big")
                if address < 0xa0000000 and address + size > 0x9ff00000:
                    if address == 0x9ff00000 and size == 0x100000 and child.props.get("no-map") == b"":
                        return False
                    raise ValueError("existing reservation conflicts with AT&T ap_share_region")
        child = Node("ap_share_region@9ff00000")
        if parent.child(child.name):
            raise ValueError("ap_share_region node already exists without the expected reg")
        child.props = {"reg": (0x9ff00000).to_bytes(address_bytes, "big") +
                              (0x100000).to_bytes(size_bytes, "big"), "no-map": b""}
        parent.children.append(child)
        return True


def kernel_dtbs(kernel):
    compressed, raw, tail = gzip_member(kernel)
    result, offset = [], 0
    while offset < len(tail):
        if offset + 8 > len(tail) or tail[offset:offset + 4] != b"\xd0\x0d\xfe\xed":
            raise ValueError("unexpected data after kernel gzip / appended DTB")
        size, = struct.unpack_from(">I", tail, offset + 4)
        if size < 40 or offset + size > len(tail):
            raise ValueError("truncated appended DTB")
        blob = tail[offset:offset + size]
        result.append((blob, Fdt(blob)))
        offset += size
    if not result:
        raise ValueError("no appended DTBs")
    return compressed, raw, result


def cpio_entries(data, *, allow_duplicate_directories=()):
    """Read ordered newc records without extracting or collapsing names.

    Duplicate names remain errors by default. A caller auditing a known
    archive may allow one repeat of a named empty directory, with metadata
    identical except for its inode number. Both encoded records are retained.
    """
    entries, offset, names, repeated = [], 0, {}, set()
    allowed = set(allow_duplicate_directories)
    while offset + 110 <= len(data):
        start = offset
        magic = data[offset:offset + 6]
        if magic not in (b"070701", b"070702"):
            raise ValueError("expected newc or crc cpio")
        fields = [int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
        size, namesize = fields[6], fields[11]
        name_end = offset + 110 + namesize
        if namesize < 1 or name_end > len(data) or data[name_end - 1] != 0:
            raise ValueError("invalid cpio name")
        name = data[offset + 110:name_end - 1].decode("utf-8")
        if "\0" in name:
            raise ValueError("duplicate or invalid cpio name")
        if name in names:
            if (name not in allowed or name in repeated
                    or fields[1] & 0o170000 != 0o040000 or size
                    or fields[1:] != names[name][1:]):
                raise ValueError("duplicate or invalid cpio name")
            repeated.add(name)
        else:
            names[name] = fields
        payload_start = aligned(name_end, 4)
        offset = aligned(payload_start + size, 4)
        if offset > len(data):
            raise ValueError("truncated cpio file")
        content = data[payload_start:payload_start + size]
        if magic == b"070702" and (sum(content) & 0xffffffff) != fields[12]:
            raise ValueError("cpio CRC mismatch")
        entries.append((name, fields, content, data[start:offset]))
        if name == "TRAILER!!!":
            if size or any(data[offset:]):
                raise ValueError("unexpected data after cpio trailer")
            return entries
    raise ValueError("missing cpio trailer")


def patch_init_rc(ramdisk, patch, marker):
    _, raw, tail = gzip_member(ramdisk)
    if tail:
        raise ValueError("unexpected data after ramdisk gzip")
    entries = cpio_entries(raw)
    names = [e[0] for e in entries if e[0] in ("init.rc", "./init.rc")]
    if len(names) != 1:
        raise ValueError("expected exactly one ramdisk init.rc")
    result = bytearray()
    for name, fields, content, encoded in entries:
        if name == names[0]:
            if fields[1] & 0o170000 != 0o100000 or fields[4] != 1:
                raise ValueError("init.rc must be a regular file without hardlinks")
            if patch in content:
                return ramdisk
            if marker in content:
                raise ValueError("init.rc already has a different version of this patch")
            content = content.rstrip(b"\n") + b"\n" + patch
            fields[6] = len(content)
            if encoded[:6] == b"070702":
                fields[12] = sum(content) & 0xffffffff
            header = encoded[:6] + "".join("{:08x}".format(n) for n in fields).encode("ascii")
            header += name.encode("utf-8") + b"\0"
            encoded = header + b"\0" * (-len(header) % 4) + content
            encoded += b"\0" * (-len(encoded) % 4)
        result.extend(encoded)
    result.extend(b"\0" * (-len(result) % 512))
    return gzip.compress(bytes(result), mtime=0)


def patch_reader(ramdisk):
    return patch_init_rc(ramdisk, READER_PATCH, b"# Fujisan AT&T pstore reader:")


def patch_charger(ramdisk):
    return patch_init_rc(ramdisk, CHARGER_PATCH, b"# Fujisan AT&T recovery:")


def patch_adb_only(ramdisk):
    """Disable MTP in the known legacy/configfs TWRP ramdisks.

    TWRP loads its saved tw_mtp_enabled setting independently of the USB
    default. Its existing mtp.crash_check startup guard suppresses that first
    Enable_MTP call. Remove the MTP hardware actions too, so later requests
    cannot briefly enumerate MTP before a property callback switches to adb.
    Keep the published adb/FunctionFS readiness and charger paths unchanged.
    """
    _, raw, tail = gzip_member(ramdisk)
    if tail:
        raise ValueError("unexpected data after ramdisk gzip")
    entries = cpio_entries(raw)
    files = {}
    wanted = {"prop.default", "init.recovery.usb.rc", "sbin/recovery"}
    for name, fields, content, encoded in entries:
        canonical = name.removeprefix("./")
        if canonical in wanted:
            if canonical in files or fields[1] & 0o170000 != 0o100000 or fields[4] != 1:
                raise ValueError("expected unique regular TWRP USB files without hardlinks")
            files[canonical] = content
    if set(files) != wanted:
        raise ValueError("expected prop.default, init.recovery.usb.rc, and sbin/recovery")
    recovery = files["sbin/recovery"]
    if b"mtp.crash_check\0" not in recovery or b"tw_mtp_enabled\0" not in recovery:
        raise ValueError("recovery does not have the known TWRP MTP startup guard")
    props, usb = files["prop.default"], files["init.recovery.usb.rc"]
    configfs = b"mount configfs none /config" in usb
    guard = b" && property:sys.usb.configfs=1" if configfs else b""
    redirects = b"".join(b"on property:sys.usb.config=" + request + guard
                         + b"\n    setprop sys.usb.config adb\n\n"
                         for request in (b"mtp", b"mtp,adb"))
    marked = [ADB_ONLY_MARKER in content for content in (props, usb)]
    if any(marked):
        defaults = re.findall(rb"(?m)^persist\.sys\.usb\.config=([^\r\n]*)", props)
        if (not all(marked) or props.count(ADB_ONLY_MARKER) != 1
                or usb.count(ADB_ONLY_MARKER) != 1 or not defaults
                or any(value != b"adb" for value in defaults)
                or re.findall(rb"(?m)^mtp\.crash_check=([^\r\n]*)", props) != [b"1"]
                or usb.count(redirects) != 1
                or b"mtp" in usb.replace(redirects, b"").replace(ADB_ONLY_MARKER, b"").lower()):
            raise ValueError("incomplete or conflicting adb-only patch")
        return ramdisk
    props, replacements = re.subn(rb"(?m)^persist\.sys\.usb\.config=[^\r\n]*",
                                 b"persist.sys.usb.config=adb", props)
    if not replacements:
        raise ValueError("missing published persist.sys.usb.config default")
    props = re.sub(rb"(?m)^mtp\.crash_check=[^\n]*\n?", b"", props)
    props = props.rstrip(b"\n") + b"\n\n" + ADB_ONLY_MARKER + b"\nmtp.crash_check=1\n"

    if configfs:
        expected = {
            b"on property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1",
            b"on property:sys.usb.ffs.ready=1 && property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1",
        }
        creation = b"    mkdir /config/usb_gadget/g1/functions/mtp.gs0 0770 root shell\n"
        if usb.count(creation) != 1:
            raise ValueError("unexpected configfs MTP function creation")
        usb = usb.replace(creation, b"")
        if (b"on property:sys.usb.ffs.ready=1 && property:sys.usb.config=adb && property:sys.usb.configfs=1\n" not in usb
                or b"symlink /config/usb_gadget/g1/functions/ffs.adb /config/usb_gadget/g1/configs/b.1/f1\n" not in usb):
            raise ValueError("missing published adb FunctionFS readiness path")
    else:
        expected = {b"on property:sys.usb.config=mtp", b"on property:sys.usb.config=mtp,adb"}
        initial = b"    setprop sys.usb.config ${persist.sys.usb.config}\n"
        if (usb.count(initial) != 1 or b"on property:sys.usb.config=adb\n" not in usb
                or b"write /sys/class/android_usb/android0/functions ${sys.usb.config}\n" not in usb):
            raise ValueError("unexpected legacy USB initialization")
        usb = usb.replace(initial, b"    setprop sys.usb.config adb\n")
    kept, removed = [], []
    for action in re.split(rb"(?m)(?=^on )", usb):
        header = action.split(b"\n", 1)[0]
        if b"property:sys.usb.config=mtp" in header:
            removed.append(header)
        else:
            dynamic = b"write /sys/class/android_usb/android0/functions ${sys.usb.config}"
            if not configfs and dynamic in action:
                modes = {b"on property:sys.usb.config=" + mode: mode
                         for mode in (b"adb", b"mass_storage", b"mass_storage,adb")}
                if header not in modes:
                    raise ValueError("unreviewed dynamic legacy USB function selection")
                # An already queued action must not expand a later MTP request.
                action = action.replace(dynamic, b"write /sys/class/android_usb/android0/functions " + modes[header])
            kept.append(action)
    if len(removed) != len(expected) or set(removed) != expected:
        raise ValueError("unexpected MTP init actions; refusing a partial USB patch")
    usb = b"".join(kept)
    if b"mtp" in usb.lower():
        raise ValueError("unhandled MTP action in published USB script")
    usb = usb.rstrip(b"\n") + b"\n\n" + ADB_ONLY_MARKER + b"\n" + redirects
    updates = {"prop.default": props, "init.recovery.usb.rc": usb}
    result = bytearray()
    for name, fields, content, encoded in entries:
        canonical = name.removeprefix("./")
        if canonical in updates:
            content = updates[canonical]
            fields = list(fields)
            fields[6] = len(content)
            if encoded[:6] == b"070702":
                fields[12] = sum(content) & 0xffffffff
            header = encoded[:6] + "".join("{:08x}".format(n) for n in fields).encode("ascii")
            header += name.encode("utf-8") + b"\0"
            encoded = header + b"\0" * (-len(header) % 4) + content
            encoded += b"\0" * (-len(encoded) % 4)
        result.extend(encoded)
    result.extend(b"\0" * (-len(result) % 512))
    return gzip.compress(bytes(result), mtime=0)


def report(data, verify=True):
    boot = BootImage(data)
    compressed, raw, dtbs = kernel_dtbs(boot.kernel)
    version = next((part[:240].decode("ascii", errors="replace").strip()
                    for part in raw.split(b"\0") if part.startswith(b"Linux version ")), None)
    info = verify_signature(boot.payload, boot.trailer) if verify else signature_info(boot.trailer)
    return {"bytes": len(data), "sha256": sha256(data), "page_size": boot.page,
            "kernel_version": version, "kernel_bytes": len(boot.kernel),
            "kernel_gzip_sha256": sha256(compressed), "ramdisk_sha256": sha256(boot.ramdisk),
            "boot_id_valid": boot.id_valid, "boot_id_style": boot.id_style, "cmdline": boot.cmdline,
            "signature_target": info["target"], "signature_verified": verify,
            "signature_bytes": info["trailer_bytes"],
            "dtbs": [{"bytes": len(blob), "sha256": sha256(blob), "free_tail_bytes": dtb.free_tail,
                      "msm_id_hex": dtb.root.props.get("qcom,msm-id", b"").hex(),
                      "board_id_hex": dtb.root.props.get("qcom,board-id", b"").hex()}
                     for blob, dtb in dtbs]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="verify signature and inspect an existing image")
    inspect.add_argument("image", type=Path)
    patch = sub.add_parser("patch", help="create a separate patched and signed image locally")
    patch.add_argument("image", type=Path)
    patch.add_argument("output", type=Path)
    patch.add_argument("--target", choices=("/boot", "/recovery"), required=True)
    patch.add_argument("--key", type=Path, required=True, help="private RSA PEM key outside this repo")
    patch.add_argument("--certificate", type=Path, required=True, help="matching PEM certificate")
    patch.add_argument("--att-dt", action="store_true", help="8 KiB DTB slack and 0x9ff00000 reservation")
    ramdisk_options = patch.add_mutually_exclusive_group()
    ramdisk_options.add_argument("--reader", action="store_true", help="TWRP 3.2.3 charger/USB init.rc patches")
    ramdisk_options.add_argument("--charger", action="store_true", help="start recovery in charger mode; use only with a recovery ramdisk")
    patch.add_argument("--adb-only", action="store_true", help="disable MTP startup in the known TWRP ramdisks and redirect MTP requests to adb")
    patch.add_argument("--append-cmdline", default="")
    args = parser.parse_args(argv)
    try:
        data = args.image.read_bytes()
        original = report(data)
        if args.command == "inspect":
            print(json.dumps(original, indent=2))
            return 0
        if args.output.exists() or args.output.with_suffix(args.output.suffix + ".json").exists():
            raise ValueError("output or manifest already exists; use a new filename")
        boot = BootImage(data)
        if not boot.id_valid:
            raise ValueError("source boot image SHA-1 ID does not match its sections")
        kernel, ramdisk = boot.kernel, boot.ramdisk
        if args.att_dt:
            compressed, _, dtbs = kernel_dtbs(kernel)
            patched = []
            for _, dtb in dtbs:
                msm_id = dtb.root.props.get("qcom,msm-id", b"")
                board_id = dtb.root.props.get("qcom,board-id", b"")
                if msm_id not in (bytes.fromhex("0000013100010001"), bytes.fromhex("000000f600030001")) or board_id[:4] != bytes.fromhex("00000066"):
                    raise ValueError("DTB IDs do not match the documented Fujisan images")
                dtb.add_att_reservation()
                patched.append(dtb.serialize(free=8192))
            kernel = compressed + b"".join(patched)
        if args.reader:
            if not (original["kernel_version"] or "").startswith("Linux version 3.18.71"):
                raise ValueError("--reader is for the known TWRP 3.2.3 kernel only")
            ramdisk = patch_reader(ramdisk)
        elif args.charger:
            ramdisk = patch_charger(ramdisk)
        if args.adb_only:
            ramdisk = patch_adb_only(ramdisk)
        cmdline = (boot.cmdline.rstrip() + " " + args.append_cmdline).strip() if args.append_cmdline else None
        payload = boot.rebuild(kernel=kernel, ramdisk=ramdisk, cmdline=cmdline)
        result = sign_image(payload, args.target, args.key, args.certificate)
        summary = report(result)
        summary.update({"source_sha256": sha256(data), "source_name": args.image.name,
                        "changes": {"att_dt": args.att_dt, "reader": args.reader,
                                    "charger": args.charger,
                                    "adb_only": args.adb_only,
                                    "append_cmdline": args.append_cmdline},
                        "hardware_tested": False})
        # Exclusive creation: an existing original, output, or backup is never overwritten.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(result)
        manifest = args.output.with_suffix(args.output.suffix + ".json")
        descriptor = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(summary, stream, indent=2)
            stream.write("\n")
        print(json.dumps(summary, indent=2))
    except (OSError, ValueError, UnicodeError, struct.error, zlib.error) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
