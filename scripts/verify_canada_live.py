#!/usr/bin/env python3
"""Dynamic live acceptance test for the current Canada at War lead."""
from __future__ import annotations

from pathlib import Path
import hashlib
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from validate_canada_publish import CANADA, ROOT, extract_lead, inspect_image

BASE = "https://brazilginga.neocities.org/Canada/"
USER_AGENT = "CanadaAtWar-PublishVerifier/2.0"


def die(message: str) -> None:
    raise SystemExit(f"CANADA LIVE VERIFICATION FAILED: {message}")


def fetch(url: str, *, binary: bool = False, attempts: int = 6) -> tuple[bytes, str]:
    last = ""
    for attempt in range(1, attempts + 1):
        sep = "&" if "?" in url else "?"
        bust = f"{sep}caw_verify={int(time.time())}-{attempt}"
        req = urllib.request.Request(url + bust, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
                ctype = r.headers.get("Content-Type", "")
                if getattr(r, "status", 200) == 200:
                    return data, ctype
                last = f"HTTP {getattr(r, 'status', 'unknown')}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(2)
    die(f"could not fetch {url}: {last}")


def assert_text_page(url: str, expected: tuple[str, ...]) -> None:
    data, ctype = fetch(url)
    try:
        text = data.decode("utf-8", "replace")
    except Exception as exc:
        die(f"could not decode {url}: {exc}")
    for marker in expected:
        if marker not in text:
            die(f"live page {url} is missing expected marker: {marker}")
    print(f"Verified live page: {url}")


def main() -> int:
    home_text = (CANADA / "index.html").read_text(encoding="utf-8")
    lead = extract_lead(home_text)
    article_path = CANADA / lead.article_href
    image_path = CANADA / lead.image_src
    local_info = inspect_image(image_path)

    article_url = urllib.parse.urljoin(BASE, lead.article_href)
    image_url = urllib.parse.urljoin(BASE, lead.image_src)

    assert_text_page(BASE, (lead.headline, lead.article_href, lead.image_src))
    assert_text_page(article_url, (lead.headline, lead.image_src))

    remote_bytes, ctype = fetch(image_url, binary=True)
    if not ctype.lower().startswith("image/"):
        die(f"live lead asset has non-image Content-Type {ctype!r}: {image_url}")

    temp = ROOT / (".canada-live-verify.tmp" + image_path.suffix)
    try:
        temp.write_bytes(remote_bytes)
        remote_info = inspect_image(temp)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass

    if (remote_info.kind, remote_info.width, remote_info.height) != (local_info.kind, local_info.width, local_info.height):
        die(
            f"live image dimensions/type differ from local upload candidate: "
            f"local={local_info.kind} {local_info.width}x{local_info.height}; "
            f"live={remote_info.kind} {remote_info.width}x{remote_info.height}"
        )

    local_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
    remote_hash = hashlib.sha256(remote_bytes).hexdigest()
    if local_hash != remote_hash:
        die(f"live lead image bytes do not match sanitized local asset: {image_url}")

    print(f"Verified live image: {image_url} ({remote_info.kind}, {remote_info.width}x{remote_info.height})")
    print("CANADA PUBLICATION VERIFIED: homepage + article + image")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
