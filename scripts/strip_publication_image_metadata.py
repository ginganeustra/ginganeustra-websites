#!/usr/bin/env python3
"""Compatibility wrapper for publication image sanitation.

Before the normal metadata sanitizer runs, switch the CBC lead elephant artwork to
a verified direct JPEG and make it 60% of its previous displayed size. Other raster
images wrapped inside SVG data URIs are also rewritten to direct JPEG assets.
"""
from __future__ import annotations

from pathlib import Path

ROOTS = (Path("Brazil"), Path("Argentina"), Path("Canada"))
ELEPHANT_STEM = "republican-elephant-tinfoil-sept-1-2026"


def validate_jpeg(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing CBC lead image: {path}")
    data = path.read_bytes()
    if len(data) < 5000 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise SystemExit(f"CBC lead image is not a complete JPEG: {path}")


def prepare_elephant_art() -> None:
    root = Path("Canada")
    image = root / "assets" / f"{ELEPHANT_STEM}.jpg"
    validate_jpeg(image)

    homepage = root / "index.html"
    article = root / "republicans-revoke-cbc-radio-canada-accreditation-september-1-2026.html"
    for path in (homepage, article):
        text = path.read_text(encoding="utf-8")
        text = text.replace(f"assets/{ELEPHANT_STEM}.svg", f"assets/{ELEPHANT_STEM}.jpg")
        text = text.replace(f"assets/{ELEPHANT_STEM}.png", f"assets/{ELEPHANT_STEM}.jpg")
        path.write_text(text, encoding="utf-8")

    htext = homepage.read_text(encoding="utf-8")
    old_home_style = 'style="display:block;width:100%;max-width:900px;height:auto;margin:18px 0 26px"'
    new_home_style = 'style="display:block;width:60%;max-width:540px;height:auto;margin:18px auto 26px"'
    if old_home_style in htext:
        htext = htext.replace(old_home_style, new_home_style, 1)
    elif new_home_style not in htext:
        raise SystemExit("CBC homepage lead image style changed; refusing to guess at 60% resize")
    homepage.write_text(htext, encoding="utf-8")

    atext = article.read_text(encoding="utf-8")
    old_article_css = '.lead-art{display:block;width:100%;height:auto;margin:0 0 28px}'
    new_article_css = '.lead-art{display:block;width:60%;max-width:540px;height:auto;margin:0 auto 28px}'
    if old_article_css in atext:
        atext = atext.replace(old_article_css, new_article_css, 1)
    elif new_article_css not in atext:
        raise SystemExit("CBC article lead image CSS changed; refusing to guess at 60% resize")
    article.write_text(atext, encoding="utf-8")

    for path in (homepage, article):
        text = path.read_text(encoding="utf-8")
        if f"assets/{ELEPHANT_STEM}.jpg" not in text:
            raise SystemExit(f"CBC lead JPEG reference missing after repair: {path}")
    if 'width:60%;max-width:540px' not in homepage.read_text(encoding="utf-8"):
        raise SystemExit("CBC homepage image did not resize to 60%")
    if '.lead-art{display:block;width:60%;max-width:540px' not in article.read_text(encoding="utf-8"):
        raise SystemExit("CBC article image did not resize to 60%")

    print(f"CBC lead art validated as complete JPEG: {image}")
    print("CBC lead art display size reduced to 60% on homepage and article page.")


def prefer_direct_raster_assets() -> None:
    rewrites = 0
    for root in ROOTS:
        if not root.exists():
            continue
        wrappers = []
        for svg in root.rglob("*.svg"):
            jpg = svg.with_suffix(".jpg")
            if not jpg.exists():
                continue
            try:
                data = svg.read_bytes()
            except OSError:
                continue
            if b"data:image/jpeg;base64," not in data.lower():
                continue
            wrappers.append((svg, jpg))

        for html in root.rglob("*.html"):
            text = html.read_text(encoding="utf-8")
            original = text
            for svg, jpg in wrappers:
                svg_rel = svg.relative_to(root).as_posix()
                jpg_rel = jpg.relative_to(root).as_posix()
                text = text.replace(svg_rel, jpg_rel)
                svg_abs = f"https://brazilginga.neocities.org/{root.name}/{svg_rel}"
                jpg_abs = f"https://brazilginga.neocities.org/{root.name}/{jpg_rel}"
                text = text.replace(svg_abs, jpg_abs)
            if text != original:
                html.write_text(text, encoding="utf-8")
                rewrites += 1
                print(f"Safari-safe direct raster rewrite: {html}")

    print(f"Safari-safe direct raster compatibility rewrote {rewrites} HTML file(s).")


prepare_elephant_art()
prefer_direct_raster_assets()

from strip_publication_image_metadata_impl import main

if __name__ == "__main__":
    raise SystemExit(main())
