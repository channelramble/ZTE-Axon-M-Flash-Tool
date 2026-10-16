#!/usr/bin/env python3
"""Validate a saved eMMC primary GPT and optional boot/recovery/misc backups.

Reads local files only. GPT/partition GUIDs and misc contents are not printed.
Successful checks establish file consistency, not that a phone will boot.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


SECTOR = 512
REQUIRED = ("boot", "recovery", "misc")


def crc32(data):
    return zlib.crc32(data) & 0xffffffff


def read_header(data):
    if len(data) < 2 * SECTOR or data[SECTOR:SECTOR + 8] != b"EFI PART":
        raise ValueError("expected a primary GPT dump starting at disk LBA 0 (512-byte sectors)")
    fields = struct.unpack_from("<8sIIIIQQQQ16sQIII", data, SECTOR)
    _, revision, header_size, header_crc, reserved, current, backup, first, last, _, entries_lba, count, width, entries_crc = fields
    if revision != 0x10000 or not 92 <= header_size <= SECTOR or reserved:
        raise ValueError("unsupported or malformed GPT header")
    header = bytearray(data[SECTOR:SECTOR + header_size])
    header[16:20] = b"\0" * 4
    if crc32(header) != header_crc:
        raise ValueError("GPT header CRC mismatch")
    if current != 1 or not 2 <= entries_lba < first <= last < backup:
        raise ValueError("invalid primary GPT disk bounds")
    if not 1 <= count <= 4096 or width < 128 or width > 4096 or width & (width - 1):
        raise ValueError("unsupported GPT partition entry dimensions")
    start = entries_lba * SECTOR
    end = start + count * width
    if end > first * SECTOR:
        raise ValueError("overlapping GPT partition array")
    return {"sector_bytes": SECTOR, "disk_bytes": (backup + 1) * SECTOR,
            "header_crc_valid": True, "primary_dump_sectors": (end + SECTOR - 1) // SECTOR,
            "backup_header_sector": backup, "first_usable_sector": first,
            "last_usable_sector": last, "entry_count": count, "entry_bytes": width,
            "array_start_bytes": start, "array_end_bytes": end, "array_crc": entries_crc}


def read_gpt(data):
    header = read_header(data)
    start, end = header["array_start_bytes"], header["array_end_bytes"]
    first, last = header["first_usable_sector"], header["last_usable_sector"]
    count, width = header["entry_count"], header["entry_bytes"]
    if end > len(data):
        raise ValueError("truncated or overlapping GPT partition array")
    array = data[start:end]
    if crc32(array) != header["array_crc"]:
        raise ValueError("GPT partition array CRC mismatch")
    parts, guids = {}, set()
    for index in range(count):
        entry = array[index * width:(index + 1) * width]
        if not any(entry[:16]):
            continue
        unique = entry[16:32]
        if not any(unique) or unique in guids:
            raise ValueError("missing or duplicate partition GUID")
        guids.add(unique)
        low, high = struct.unpack_from("<QQ", entry, 32)
        name = entry[56:128].decode("utf-16-le").split("\0", 1)[0]
        if not name or name in parts or any(ord(c) < 32 for c in name):
            raise ValueError("empty, duplicate, or invalid partition name")
        if not first <= low <= high <= last:
            raise ValueError("partition outside GPT usable range: " + name)
        sectors = high - low + 1
        parts[name] = {"start_sector": low, "end_sector": high,
                       "sectors": sectors, "bytes": sectors * SECTOR}
    ordered = sorted(parts.items(), key=lambda item: item[1]["start_sector"])
    for (name_a, a), (name_b, b) in zip(ordered, ordered[1:]):
        if a["end_sector"] >= b["start_sector"]:
            raise ValueError("overlapping partitions: " + name_a + ", " + name_b)
    for name in REQUIRED:
        if name not in parts:
            raise ValueError("missing required partition: " + name)
    for name in ("boot", "recovery"):
        if parts[name]["bytes"] != 64 * 1024 * 1024:
            raise ValueError(name + " size differs from the documented 64 MiB; investigate before writes")
    if parts["misc"]["bytes"] < 2048:
        raise ValueError("misc too small for the bootloader control block")
    return {"sector_bytes": SECTOR, "disk_bytes": header["disk_bytes"],
            "header_crc_valid": True, "partition_array_crc_valid": True,
            "partition_count": len(parts), "partitions": parts}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_files(gpt, directory):
    result = {}
    for name in REQUIRED:
        path = directory / (name + ".bin")
        size = path.stat().st_size
        if size != gpt["partitions"][name]["bytes"]:
            raise ValueError(name + ".bin is missing partition data or has the wrong size")
        result[name] = {"bytes": size, "sha256": file_hash(path)}
        if name == "misc":
            with path.open("rb") as stream:
                command = stream.read(32).split(b"\0", 1)[0]
            result[name]["boot_recovery_flag"] = command == b"boot-recovery"
            result[name]["bcb_command_present"] = bool(command)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gpt", type=Path, help="gpt_main0.bin saved by EDL (includes LBA 0)")
    parser.add_argument("--directory", type=Path, help="also require complete boot.bin/recovery.bin/misc.bin")
    parser.add_argument("--header-only", action="store_true", help="validate an initial 2-sector read and calculate the full GPT read length")
    args = parser.parse_args(argv)
    try:
        data = args.gpt.read_bytes()
        if args.header_only:
            if args.directory:
                raise ValueError("--header-only cannot validate partition backups")
            header = read_header(data)
            print(json.dumps({"header_crc_valid": True, "partition_array_checked": False,
                              "primary_dump_start_sector": 0,
                              "primary_dump_sectors": header["primary_dump_sectors"],
                              "backup_header_sector": header["backup_header_sector"]}, indent=2))
            return 0
        gpt = read_gpt(data)
        summary = {key: value for key, value in gpt.items() if key != "partitions"}
        summary["gpt_sha256"] = file_hash(args.gpt)
        summary["partitions"] = {name: gpt["partitions"][name] for name in REQUIRED}
        if args.directory:
            summary["backups"] = check_files(gpt, args.directory)
        print(json.dumps(summary, indent=2))
    except (OSError, ValueError, UnicodeError, struct.error) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
