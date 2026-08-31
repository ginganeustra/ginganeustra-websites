#!/usr/bin/env python3
"""Strip privacy/descriptive metadata from publication image files without changing pixels.

The sanitizer removes EXIF/GPS, XMP, IPTC/Photoshop, comments, timestamps and other
non-rendering metadata from JPEG/PNG/WebP files. It preserves technical colour data
needed for reliable rendering (for example ICC profiles and Adobe colour transform
markers). It also sanitizes base64-embedded JPEG/PNG/WebP images inside SVG files.
"""
from __future__ import annotations

import base64
import binascii
import re
import struct
import sys
from pathlib import Path

ROOTS = (Path("Brazil"), Path("Argentina"), Path("Canada"))
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".svg"}


def clean_jpeg(data: bytes) -> bytes:
    if len(data) < 4 or not data.startswith(b"\xff\xd8"):
        return data

    out = bytearray(b"\xff\xd8")
    i = 2
    n = len(data)

    while i < n:
        if data[i] != 0xFF:
            return data

        start = i
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            return data
        marker = data[i]
        i += 1

        if marker == 0xD9:
            out.extend(data[start:i])
            out.extend(data[i:])
            break
        if marker == 0xDA:
            if i + 2 > n:
                return data
            seglen = struct.unpack(">H", data[i:i + 2])[0]
            end = i + seglen
            if seglen < 2 or end > n:
                return data
            out.extend(data[start:end])
            out.extend(data[end:])
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            out.extend(data[start:i])
            continue

        if i + 2 > n:
            return data
        seglen = struct.unpack(">H", data[i:i + 2])[0]
        end = i + seglen
        if seglen < 2 or end > n:
            return data
        payload = data[i + 2:end]

        keep = True
        if marker == 0xFE:
            keep = False
        elif 0xE0 <= marker <= 0xEF:
            if marker == 0xE0:
                keep = payload.startswith((b"JFIF\x00", b"JFXX\x00"))
            elif marker == 0xE2:
                keep = payload.startswith(b"ICC_PROFILE\x00")
            elif marker == 0xEE:
                keep = payload.startswith(b"Adobe")
            else:
                keep = False

        if keep:
            out.extend(data[start:end])
        i = end
    else:
        return data

    return bytes(out)


def clean_png(data: bytes) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(sig):
        return data
    out = bytearray(sig)
    i = len(sig)
    n = len(data)
    drop = {b"eXIf", b"tEXt", b"zTXt", b"iTXt", b"tIME", b"pHYs"}

    while i + 12 <= n:
        length = struct.unpack(">I", data[i:i + 4])[0]
        end = i + 12 + length
        if end > n:
            return data
        ctype = data[i + 4:i + 8]
        if ctype not in drop:
            out.extend(data[i:end])
        i = end
        if ctype == b"IEND":
            if i < n:
                out.extend(data[i:])
            break
    else:
        return data

    return bytes(out)


def clean_webp(data: bytes) -> bytes:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return data
    i = 12
    chunks: list[bytes] = []
    n = len(data)
    changed = False

    while i + 8 <= n:
        fourcc = data[i:i + 4]
        size = struct.unpack("<I", data[i + 4:i + 8])[0]
        d0 = i + 8
        d1 = d0 + size
        end = d1 + (size & 1)
        if end > n:
            return data
        payload = data[d0:d1]

        if fourcc in {b"EXIF", b"XMP "}:
            changed = True
        else:
            if fourcc == b"VP8X" and payload:
                flags = payload[0] & ~0x0C
                if flags != payload[0]:
                    payload = bytes([flags]) + payload[1:]
                    changed = True
            chunk = fourcc + struct.pack("<I", len(payload)) + payload
            if len(payload) & 1:
                chunk += b"\x00"
            chunks.append(chunk)
        i = end

    if i != n or not changed:
        return data

    body = b"WEBP" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def clean_raster(data: bytes, kind: str) -> bytes:
    kind = kind.lower()
    if kind in {"jpg", "jpeg"}:
        return clean_jpeg(data)
    if kind == "png":
        return clean_png(data)
    if kind == "webp":
        return clean_webp(data)
    return data


_DATA_URI = re.compile(
    rb"(data:image/(jpeg|jpg|png|webp);base64,)([^\"']+)",
    re.IGNORECASE,
)


def clean_svg(data: bytes) -> bytes:
    def repl(match: re.Match[bytes]) -> bytes:
        prefix, kind, encoded = match.groups()
        compact = re.sub(rb"\s+", b"", encoded)
        try:
            raw = base64.b64decode(compact, validate=True)
        except (binascii.Error, ValueError):
            return match.group(0)
        cleaned = clean_raster(raw, kind.decode("ascii"))
        if cleaned == raw:
            return match.group(0)
        return prefix + base64.b64encode(cleaned)

    return _DATA_URI.sub(repl, data)


def clean_file(path: Path) -> bool:
    original = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        cleaned = clean_jpeg(original)
    elif suffix == ".png":
        cleaned = clean_png(original)
    elif suffix == ".webp":
        cleaned = clean_webp(original)
    elif suffix == ".svg":
        cleaned = clean_svg(original)
    else:
        return False

    if cleaned != original:
        path.write_bytes(cleaned)
        return True
    return False


def main() -> int:
    seen = 0
    changed = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for path in sorted(
            p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
        ):
            seen += 1
            if clean_file(path):
                changed += 1
                print(f"Sanitized metadata: {path}")

    print(f"Metadata sanitizer checked {seen} publication image files; changed {changed}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
