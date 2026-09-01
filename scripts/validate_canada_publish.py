#!/usr/bin/env python3
"""Fail-closed preflight validation for Canada at War publishing.

This validator is intentionally conservative. A routine publication should not
need clever repair logic: if the current lead, article, or art cannot be proven
valid from the checked-out repository, deployment stops.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
CANADA = ROOT / "Canada"
HOME = CANADA / "index.html"
ALLOWED_RASTER = {".jpg", ".jpeg", ".png"}

REQUIRED_HOME_MARKERS = (
    "CANADA_AT_WAR_MASTHEAD_LOCK",
    "PINNED_LEAD_LOCK",
    "THE TICK",
    "HOURLY_TICK_AUTO_BEGIN",
    "HOURLY_TICK_AUTO_END",
    "tradingview-widget-container",
    "canada-at-war-goose-eagle-v3.jpg",
    "petition-paint-mix",
    "Must Read Library",
    "How Lying Works",
    'id="must-read-library"',
    "Must Reads from Other Sources",
    "ticker-speed-controller",
    "var pxPerSecond=125",
)


@dataclass(frozen=True)
class ImageInfo:
    kind: str
    width: int
    height: int


@dataclass(frozen=True)
class LeadInfo:
    block: str
    headline: str
    article_href: str
    image_src: str
    published: str


def die(message: str) -> None:
    raise SystemExit(f"CANADA PUBLISH PREFLIGHT FAILED: {message}")


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        die("JPEG is truncated or has an invalid SOI/EOI signature")
    i = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in {0xD8, 0xD9}:
            continue
        if marker == 0xDA:
            break
        if i + 2 > len(data):
            break
        seglen = struct.unpack(">H", data[i:i+2])[0]
        if seglen < 2 or i + seglen > len(data):
            die("JPEG contains an invalid segment length")
        if marker in sof:
            if seglen < 7:
                die("JPEG SOF segment is too short")
            height, width = struct.unpack(">HH", data[i+3:i+7])
            if width <= 0 or height <= 0:
                die("JPEG reports invalid dimensions")
            return width, height
        i += seglen
    die("JPEG dimensions could not be read")


def inspect_image(path: Path) -> ImageInfo:
    if not path.exists() or not path.is_file():
        die(f"missing image file: {path.relative_to(ROOT)}")
    ext = path.suffix.lower()
    if ext not in ALLOWED_RASTER:
        die(f"routine story art must be JPG/PNG, not {ext or 'extensionless'}: {path.relative_to(ROOT)}")
    data = path.read_bytes()
    if len(data) < 128:
        die(f"image is implausibly small: {path.relative_to(ROOT)}")
    if ext in {".jpg", ".jpeg"}:
        width, height = _jpeg_dimensions(data)
        return ImageInfo("jpeg", width, height)
    sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(sig) or len(data) < 24 or data[12:16] != b"IHDR":
        die(f"PNG signature/IHDR is invalid: {path.relative_to(ROOT)}")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        die(f"PNG reports invalid dimensions: {path.relative_to(ROOT)}")
    if not data.endswith(b"IEND\xaeB`\x82"):
        die(f"PNG is missing a complete IEND chunk: {path.relative_to(ROOT)}")
    return ImageInfo("png", width, height)


def extract_lead(home_text: str) -> LeadInfo:
    marked = re.search(r"<!-- CANADA_LEAD_BEGIN -->(.*?)<!-- CANADA_LEAD_END -->", home_text, re.S)
    if marked:
        block = marked.group(1).strip()
    else:
        legacy = re.search(
            r"<!-- PINNED_LEAD_LOCK -->\s*(<section class=\"hero\">.*?</section>)\s*<main class=\"wrap\">",
            home_text,
            re.S,
        )
        if not legacy:
            die("could not locate the protected homepage lead slot")
        block = legacy.group(1)

    headlines = re.findall(r"<h1>(.*?)</h1>", block, re.S)
    hrefs = re.findall(r"<a class=\"read\" href=\"([^\"]+)\"", block)
    images = re.findall(r"<img\b[^>]*\bsrc=\"([^\"]+)\"[^>]*>", block, re.S)
    metas = re.findall(r"<p class=\"meta\">(.*?)</p>", block, re.S)
    if len(headlines) != 1 or len(hrefs) != 1 or len(images) != 1 or len(metas) != 1:
        die("lead slot must contain exactly one headline, article link, image, and publication meta line")
    return LeadInfo(
        block=block,
        headline=re.sub(r"\s+", " ", headlines[0]).strip(),
        article_href=hrefs[0].strip(),
        image_src=images[0].strip(),
        published=re.sub(r"\s+", " ", metas[0]).strip(),
    )


def local_canada_path(relative: str, *, label: str) -> Path:
    if relative.startswith(("http://", "https://", "//", "data:")):
        die(f"{label} must be a direct local Canada asset/article path, got {relative}")
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts:
        die(f"unsafe {label} path: {relative}")
    resolved = (CANADA / p).resolve()
    try:
        resolved.relative_to(CANADA.resolve())
    except ValueError:
        die(f"{label} escapes Canada directory: {relative}")
    return resolved


def validate_article(lead: LeadInfo) -> tuple[Path, Path, ImageInfo]:
    article = local_canada_path(lead.article_href, label="lead article")
    if article.suffix.lower() != ".html" or not article.exists():
        die(f"lead article does not exist: {lead.article_href}")
    text = article.read_text(encoding="utf-8")
    if "data:image/" in text.lower():
        die(f"lead article contains an embedded data-image URI: {lead.article_href}")
    if lead.headline not in text:
        die("homepage lead headline does not match the linked article headline")
    if lead.image_src not in text:
        die("homepage and linked article do not reference the same lead image")
    if '<link rel="canonical" href="https://brazilginga.neocities.org/Canada/' not in text:
        die("lead article is missing the Canada at War canonical URL")
    if "Published " not in text and "Updated " not in text:
        die("lead article is missing publication/update metadata")

    if lead.image_src.lower().endswith(".svg"):
        die("homepage lead uses SVG; routine story art must be a direct JPG/PNG")
    if lead.image_src.lower().startswith("data:"):
        die("homepage lead uses a data URI; routine story art must be a direct JPG/PNG")
    if not lead.image_src.startswith("assets/"):
        die(f"homepage lead image must live in Canada/assets/: {lead.image_src}")

    image = local_canada_path(lead.image_src, label="lead image")
    info = inspect_image(image)

    ext = image.suffix.lower()
    if info.kind == "jpeg" and ext not in {".jpg", ".jpeg"}:
        die("lead image content is JPEG but filename extension is not JPG/JPEG")
    if info.kind == "png" and ext != ".png":
        die("lead image content is PNG but filename extension is not PNG")

    return article, image, info


def validate_shell(home_text: str) -> None:
    for marker in REQUIRED_HOME_MARKERS:
        if marker not in home_text:
            die(f"protected homepage shell marker missing: {marker}")
    if home_text.count("<!-- PINNED_LEAD_LOCK -->") != 1:
        die("PINNED_LEAD_LOCK must occur exactly once")
    if home_text.count("<section class=\"hero\">") != 1:
        die("homepage must contain exactly one hero/lead section")
    if home_text.count("<!-- HOURLY_TICK_AUTO_BEGIN -->") != 1 or home_text.count("<!-- HOURLY_TICK_AUTO_END -->") != 1:
        die("THE TICK protected block markers must occur exactly once")
    if "data:image/" in home_text.lower():
        die("homepage contains a data-image URI")


def main() -> int:
    if not HOME.exists():
        die("Canada/index.html is missing")
    home_text = HOME.read_text(encoding="utf-8")
    validate_shell(home_text)
    lead = extract_lead(home_text)
    article, image, info = validate_article(lead)
    print("CANADA PUBLISH PREFLIGHT PASSED")
    print(f"Lead: {lead.headline}")
    print(f"Article: {article.relative_to(ROOT)}")
    print(f"Image: {image.relative_to(ROOT)} ({info.kind}, {info.width}x{info.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
