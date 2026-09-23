"""Decode BLE advertisements of Xiaomi weight scales, offline.

Two frame layouts are supported:

* ``0x181D``, 10 bytes - Mi Smart Scale (v1 family, e.g. XMTZC04HM)
* ``0x181B``, 13 bytes - Mi Body Composition Scale (v2 family, e.g. XMTZC05HM,
  advertised as ``MIBFS``)

Both carry the measurement inside the advertisement itself, so nothing has to be
paired or connected: a passive scan is enough. No vendor application is needed
and the payload never leaves the local machine.

Frame layout (v2, 13 bytes)::

    0       0x02 header
    1       flags: 0x02 impedance present, 0x20 weight stabilized, 0x80 load removed
    2-3     year, little endian (stays 1970 until a vendor app sets the RTC)
    4       month
    5       day
    6       hour
    7       minute
    8       second
    9-10    impedance, little endian (0xFFFD when not measured)
    11-12   weight, little endian; value / 200 = kilograms
"""

from __future__ import annotations

import argparse
import json
import sys

FLAG_IMPEDANCE = 0x02
FLAG_STABILIZED = 0x20
FLAG_LOAD_REMOVED = 0x80

V1_LENGTH = 10
V2_LENGTH = 13
WEIGHT_DIVISOR = 200.0


def _le16(data: bytes, index: int) -> int:
    return data[index] | (data[index + 1] << 8)


def _decode_v1(data: bytes) -> dict:
    control = data[0]
    return {
        "version": 1,
        "weight_kg": round(_le16(data, 1) / WEIGHT_DIVISOR, 3),
        "impedance": None,
        "stabilized": control in (0x22, 0xA2),
        "load_removed": control == 0xA2,
        "timestamp": (
            f"{_le16(data, 3):04d}-{data[5]:02d}-{data[6]:02d}"
            f"T{data[7]:02d}:{data[8]:02d}:{data[9]:02d}"
        ),
    }


def _decode_v2(data: bytes) -> dict:
    flags = data[1]
    return {
        "version": 2,
        "weight_kg": round(_le16(data, 11) / WEIGHT_DIVISOR, 3),
        "impedance": _le16(data, 9) if flags & FLAG_IMPEDANCE else None,
        "stabilized": bool(flags & FLAG_STABILIZED),
        "load_removed": bool(flags & FLAG_LOAD_REMOVED),
        "timestamp": (
            f"{_le16(data, 2):04d}-{data[4]:02d}-{data[5]:02d}"
            f"T{data[6]:02d}:{data[7]:02d}:{data[8]:02d}"
        ),
    }


def _frame_from_line(line: str) -> bytes | None:
    """Accept hex with spaces, colons, dashes or none; return bytes or None."""
    cleaned = line.strip().replace(" ", "").replace(":", "").replace("-", "")
    if not cleaned or not all(c in "0123456789abcdefABCDEF" for c in cleaned):
        return None
    if len(cleaned) % 2:
        return None
    return bytes.fromhex(cleaned)


def decode_frame(frame: bytes) -> dict:
    """Decode one advertisement payload."""
    if len(frame) == V2_LENGTH:
        return _decode_v2(frame)
    if len(frame) == V1_LENGTH:
        return _decode_v1(frame)
    raise ValueError(f"unknown frame length {len(frame)}; expected 10 (0x181D) or 13 (0x181B)")


def decode_stream(stream) -> int:
    """Decode hex frames line by line; comments and bad lines are reported, not fatal."""
    count = 0
    for number, line in enumerate(stream, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        frame = _frame_from_line(line)
        if frame is None:
            print(json.dumps({"line": number, "error": "not a hex frame"}), flush=True)
            continue
        try:
            record = decode_frame(frame)
        except ValueError as exc:
            print(json.dumps({"line": number, "error": str(exc)}), flush=True)
            continue
        record["line"] = number
        print(json.dumps(record, ensure_ascii=False), flush=True)
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="xiaomi_scale_decode",
        description="Decode Xiaomi scale advertisements (0x181D 10 bytes / 0x181B 13 bytes).",
    )
    parser.add_argument("frames", nargs="*", help="hex frame(s) to decode")
    parser.add_argument(
        "-f", "--file", help="read hex frames from a file, one per line (default: stdin)"
    )
    args = parser.parse_args(argv)

    if args.frames:
        exit_code = 0
        for raw in args.frames:
            frame = _frame_from_line(raw)
            if frame is None:
                print(json.dumps({"error": f"not a hex frame: {raw}"}), flush=True)
                exit_code = 2
                continue
            try:
                print(json.dumps(decode_frame(frame), ensure_ascii=False), flush=True)
            except ValueError as exc:
                print(json.dumps({"error": str(exc)}), flush=True)
                exit_code = 2
        return exit_code

    if args.file:
        with open(args.file, encoding="utf-8") as handle:
            decode_stream(handle)
    else:
        decode_stream(sys.stdin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
