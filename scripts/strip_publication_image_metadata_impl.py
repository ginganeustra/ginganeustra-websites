#!/usr/bin/env python3
"""Guard reader-facing publication copy, then strip image metadata without changing pixels.

The reader-copy gate prevents internal/editor-to-owner status language from being
published on the three homepages. For the two football magazines it also enforces
that reader content starts immediately after the public update timestamp.

The image sanitizer removes EXIF/GPS, XMP, IPTC/Photoshop, comments, timestamps and
other non-rendering metadata from JPEG/PNG/WebP files. It preserves technical colour
data needed for reliable rendering (for example ICC profiles and Adobe colour
transform markers). It also sanitizes base64-embedded JPEG/PNG/WebP images inside SVG.
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
HOME_PAGES = (Path("Brazil/index.html"), Path("Argentina/index.html"), Path("Canada/index.html"))
FOOTBALL_HOME_PAGES = (Path("Brazil/index.html"), Path("Argentina/index.html"))

# These phrases are workflow/editor language, not reader-facing journalism.
# The gate is intentionally narrow to avoid blocking legitimate article prose.
INTERNAL_COPY_PHRASES = (
    "as you asked",
    "as requested",
    "i’ve updated",
    "i've updated",
    "i have updated",
    "i’ve added",
    "i've added",
    "i have added",
    "i removed",
    "i fixed",
    "we did that",
    "remain listed only as",
    "remains listed only as",
    "have been confirmed final",
)


def guard_reader_copy() -> None:
    failures: list[str] = []

    for path in HOME_PAGES:
        if not path.exists():
            failures.append(f"missing publication homepage: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for phrase in INTERNAL_COPY_PHRASES:
            if phrase in lower:
                failures.append(f"{path}: internal/editor status phrase found: {phrase!r}")

    # The football magazines have a public update timestamp followed immediately by
    # journalism. A workflow/status card in this position is always an error.
    for path in FOOTBALL_HOME_PAGES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "READER_COPY_GATE" not in text:
            failures.append(f"{path}: missing READER_COPY_GATE marker")
            continue
        match = re.search(r'<p class="meta">.*?</p>', text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            failures.append(f"{path}: missing public update timestamp")
            continue
        tail = text[match.end():]
        # Permit whitespace and HTML comments used as non-rendering maintenance markers.
        tail = re.sub(r'^\s*(?:<!--.*?-->\s*)*', '', tail, flags=re.DOTALL)
        if not re.match(r'<h2(?:\s|>)', tail, flags=re.IGNORECASE):
            failures.append(
                f"{path}: reader content must start with an H2 immediately after the timestamp; "
                "possible editor/status note detected"
            )

    if failures:
        print("Reader-copy publication gate FAILED:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        raise SystemExit(1)

    print("Reader-copy publication gate passed for Brazil, Argentina and Canada homepages.")


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
    guard_reader_copy()

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
