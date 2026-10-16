#!/usr/bin/env python3
"""List the ARM64 debug kernel's level 6/7 initcalls without touching a device.

System.map records the pointer order, but not the pointers' contents. Function
names below are inferred from the kernel's __define_initcall symbol format;
confirm them against vmlinux or initcall_debug output before blacklisting.
"""

import argparse
import json
import re
import sys
from pathlib import Path


SYMBOL = re.compile(r"^([0-9a-fA-F]+)\s+([A-Za-z?])\s+(\S+)$")
INITCALL = re.compile(
    r"^__initcall_(?P<body>.+?)(?P<level>[67])(?P<sync>s?)"
    r"(?:\.llvm\.[0-9]+)?$"
)
BOUNDARIES = ("__initcall6_start", "__initcall7_start", "__initcall_end")


def read_order(contents):
    """Return validated pointer entries from a complete ARM64 System.map."""
    symbols = []
    for line_number, line in enumerate(contents.splitlines(), 1):
        if not line.strip():
            continue
        match = SYMBOL.fullmatch(line.strip())
        if not match:
            raise ValueError("malformed System.map line {}".format(line_number))
        address, kind, name = match.groups()
        symbols.append((int(address, 16), kind, name))

    boundaries = {}
    for address, _, name in symbols:
        if name in BOUNDARIES:
            if name in boundaries:
                raise ValueError("duplicate boundary: " + name)
            boundaries[name] = address
    missing = [name for name in BOUNDARIES if name not in boundaries]
    if missing:
        raise ValueError("missing boundaries: " + ", ".join(missing))
    start, middle, end = (boundaries[name] for name in BOUNDARIES)
    if not start <= middle <= end or any(n % 8 for n in (start, middle, end)):
        raise ValueError("invalid boundaries for 8-byte ARM64 initcall pointers")

    entries = {}
    for address, _, name in symbols:
        if not start <= address < end or name in BOUNDARIES:
            continue
        match = INITCALL.fullmatch(name)
        if not match:
            continue
        if address % 8:
            raise ValueError("unaligned initcall pointer: " + name)
        level = 6 if address < middle else 7
        if int(match["level"]) != level:
            raise ValueError("initcall level disagrees with boundaries: " + name)
        if address in entries:
            raise ValueError("ambiguous initcall pointer at {:#x}".format(address))
        # CONFIG_LTO_CLANG adds __COUNTER__ and __LINE__ before the function.
        function = re.sub(r"^\d+_\d+_", "", match["body"])
        entries[address] = {
            "level": level,
            "sync": bool(match["sync"]),
            "pointer_address": "0x{:016x}".format(address),
            "pointer_symbol": name,
            "function_inferred": function,
        }

    # Reject truncated/stripped maps instead of silently giving a partial list.
    expected_count = (end - start) // 8
    if len(entries) != expected_count:
        raise ValueError(
            "incomplete initcall table: found {} of {} pointer entries; "
            "use the complete System.map or inspect vmlinux".format(
                len(entries), expected_count
            )
        )
    return [entries[address] for address in sorted(entries)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system_map", type=Path, help="System.map from the exact kernel being tested")
    parser.add_argument("--level", type=int, choices=(6, 7), help="show only one initcall level")
    parser.add_argument("--json", action="store_true", help="print machine-readable entries")
    args = parser.parse_args(argv)
    try:
        entries = read_order(args.system_map.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.level is not None:
        entries = [entry for entry in entries if entry["level"] == args.level]
    print(
        "Read-only: function names are inferred from pointer symbols. "
        "Confirm against vmlinux or initcall_debug before blacklisting.",
        file=sys.stderr,
    )
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        print("order\tlevel\tpointer_address\tfunction_inferred\tpointer_symbol")
        for order, entry in enumerate(entries, 1):
            level = str(entry["level"]) + ("s" if entry["sync"] else "")
            print("\t".join((str(order), level, entry["pointer_address"],
                             entry["function_inferred"], entry["pointer_symbol"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
