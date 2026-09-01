#!/usr/bin/env python3
"""Compatibility wrapper for publication image sanitation.

Before the normal metadata sanitizer runs, replace HTML references to raster images
wrapped inside SVG data URIs with the same-stem direct JPEG when that JPEG exists.
This avoids Safari/WebKit failures when an SVG is loaded through an <img> element and
the SVG itself embeds a raster data URI.
"""
from pathlib import Path

ROOTS = (Path("Brazil"), Path("Argentina"), Path("Canada"))


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


prefer_direct_raster_assets()

from strip_publication_image_metadata_impl import main

if __name__ == "__main__":
    raise SystemExit(main())
