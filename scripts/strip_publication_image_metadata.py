#!/usr/bin/env python3
"""Publication-image sanitation plus Canada at War preflight enforcement.

The CBC elephant repair remains as a migration shim for the September 1, 2026
legacy commit. New routine publications must already use direct JPG/PNG assets;
`validate_canada_publish.py` enforces that before upload.
"""
from __future__ import annotations

from pathlib import Path
import re

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

    # The CBC story was the lead when this migration shim was introduced. It can
    # later rotate into the ordinary story feed. Only resize the CBC image itself;
    # never resize whichever unrelated image subsequently occupies the lead slot.
    htext = homepage.read_text(encoding="utf-8")
    elephant_tag = re.search(
        rf'<img\b[^>]*src="assets/{re.escape(ELEPHANT_STEM)}\.jpg"[^>]*>',
        htext,
        flags=re.IGNORECASE,
    )
    if not elephant_tag:
        raise SystemExit("CBC homepage JPEG reference missing after repair")
    tag = elephant_tag.group(0)
    old_home_style = 'style="display:block;width:100%;max-width:900px;height:auto;margin:18px 0 26px"'
    new_home_style = 'style="display:block;width:60%;max-width:540px;height:auto;margin:18px auto 26px"'
    if old_home_style in tag:
        tag = tag.replace(old_home_style, new_home_style, 1)
        htext = htext[:elephant_tag.start()] + tag + htext[elephant_tag.end():]
        homepage.write_text(htext, encoding="utf-8")
    elif new_home_style in tag:
        pass
    else:
        # Once the story is in the standard story-feature feed, sizing is provided
        # by the protected homepage CSS and no inline lead sizing is expected.
        if 'class="story story-feature"' not in htext:
            raise SystemExit("CBC homepage image style changed outside the standard story feed")

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
    if '.lead-art{display:block;width:60%;max-width:540px' not in article.read_text(encoding="utf-8"):
        raise SystemExit("CBC article image did not resize to 60%")

    print(f"CBC legacy lead art normalized to direct JPEG: {image}")


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

        for page in root.rglob("*.html"):
            text = page.read_text(encoding="utf-8")
            original = text
            for svg, jpg in wrappers:
                svg_rel = svg.relative_to(root).as_posix()
                jpg_rel = jpg.relative_to(root).as_posix()
                text = text.replace(svg_rel, jpg_rel)
                svg_abs = f"https://brazilginga.neocities.org/{root.name}/{svg_rel}"
                jpg_abs = f"https://brazilginga.neocities.org/{root.name}/{jpg_rel}"
                text = text.replace(svg_abs, jpg_abs)
            if text != original:
                page.write_text(text, encoding="utf-8")
                rewrites += 1
                print(f"Legacy raster-wrapper migration: {page}")

    print(f"Legacy raster-wrapper migration rewrote {rewrites} HTML file(s).")


def main() -> int:
    prepare_elephant_art()
    prefer_direct_raster_assets()

    from strip_publication_image_metadata_impl import main as sanitize
    result = sanitize()
    if result:
        return int(result)

    from validate_canada_publish import main as validate_canada
    validate_canada()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
