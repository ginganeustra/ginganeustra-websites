#!/usr/bin/env python3
"""Deterministic routine publisher for Canada at War.

Usage:
    python3 scripts/publish_canada_story.py path/to/story.json

The manifest format is documented by Canada/templates/story-manifest.example.json.
This script refuses to improvise around unexpected page structures.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import html
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
CANADA = ROOT / "Canada"
TEMPLATES = CANADA / "templates"
HOME = CANADA / "index.html"
SITEMAP = CANADA / "sitemap.xml"
BASE_URL = "https://brazilginga.neocities.org/Canada/"

sys.path.insert(0, str(ROOT / "scripts"))
from validate_canada_publish import inspect_image

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEAD_BEGIN = "<!-- CANADA_LEAD_BEGIN -->"
LEAD_END = "<!-- CANADA_LEAD_END -->"
FEED_INSERT = "<!-- CANADA_STORY_FEED_INSERT -->"


def die(message: str) -> None:
    raise SystemExit(f"CANADA PUBLISHER REFUSED: {message}")


def required(m: dict, key: str):
    value = m.get(key)
    if value is None or value == "" or value == []:
        die(f"manifest is missing required field {key!r}")
    return value


def render(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace(f"@@{key}@@", value)
    leftovers = sorted(set(re.findall(r"@@([A-Z0-9_]+)@@", out)))
    if leftovers:
        die(f"template placeholders were not filled: {', '.join(leftovers)}")
    return out


def ensure_home_markers(text: str) -> str:
    if LEAD_BEGIN in text or LEAD_END in text or FEED_INSERT in text:
        if text.count(LEAD_BEGIN) != 1 or text.count(LEAD_END) != 1 or text.count(FEED_INSERT) != 1:
            die("homepage publishing markers are incomplete or duplicated")
        return text

    m = re.search(
        r"(<!-- PINNED_LEAD_LOCK -->\s*)(<section class=\"hero\">.*?</section>)(\s*<main class=\"wrap\">)",
        text,
        re.S,
    )
    if not m:
        die("cannot bootstrap lead markers from the current known-good homepage structure")
    marked = (
        m.group(1)
        + LEAD_BEGIN + "\n"
        + m.group(2) + "\n"
        + LEAD_END
        + m.group(3)
        + "\n" + FEED_INSERT
    )
    return text[:m.start()] + marked + text[m.end():]


def current_lead_block(text: str) -> str:
    m = re.search(re.escape(LEAD_BEGIN) + r"\s*(.*?)\s*" + re.escape(LEAD_END), text, re.S)
    if not m:
        die("homepage does not contain canonical lead markers")
    return m.group(1)


def demote_lead(block: str) -> str:
    kicker_m = re.search(r'<div class="k">(?:Lead · )?(.*?)</div>', block, re.S)
    headline_m = re.search(r"<h1>(.*?)</h1>", block, re.S)
    deck_m = re.search(r"<h1>.*?</h1>\s*<p>(.*?)</p>", block, re.S)
    link_m = re.search(r'<a class="read" href="([^"]+)">(.*?)</a>', block, re.S)
    meta_m = re.search(r'<p class="meta">(.*?)</p>', block, re.S)
    img_m = re.search(r'<img\b[^>]*src="([^"]+)"[^>]*alt="([^"]*)"[^>]*>', block, re.S)
    if not all((kicker_m, headline_m, deck_m, link_m, meta_m)):
        die("cannot demote current lead safely; its structure differs from the known-good pattern")

    inner = (
        '<div><div class="k" style="color:#b51f2a">' + kicker_m.group(1).strip() + "</div>"
        + "<h2>" + headline_m.group(1).strip() + "</h2>"
        + "<p>" + deck_m.group(1).strip() + "</p>"
        + f'<a class="read" href="{link_m.group(1)}">{link_m.group(2)}</a>'
        + '<p class="meta" style="color:#666">' + meta_m.group(1).strip() + "</p></div>"
    )
    if img_m:
        return (
            '<article class="story story-feature">' + inner
            + f'<img src="{img_m.group(1)}" alt="{html.escape(img_m.group(2), quote=True)}"></article>'
        )
    return '<article class="story">' + inner + "</article>"


def build_sources(items: list[dict]) -> str:
    if not items:
        return ""
    links = []
    for item in items:
        label = html.escape(str(required(item, "label")))
        url = html.escape(str(required(item, "url")), quote=True)
        if not url.startswith(("https://", "http://")):
            die(f"source URL must be absolute HTTP(S): {url}")
        links.append(f'<a href="{url}">{label}</a>')
    return '<div class="sources"><b>Sources</b>' + "<br>".join(links) + "</div>"


def update_sitemap(slug: str, lastmod: str) -> None:
    text = SITEMAP.read_text(encoding="utf-8")
    loc = BASE_URL + slug + ".html"
    home_loc = BASE_URL
    home_pat = re.compile(rf"<url><loc>{re.escape(home_loc)}</loc><lastmod>.*?</lastmod></url>")
    text, n = home_pat.subn(f"<url><loc>{home_loc}</loc><lastmod>{html.escape(lastmod)}</lastmod></url>", text, count=1)
    if n != 1:
        die("could not update Canada sitemap homepage lastmod")
    if loc not in text:
        entry = f"  <url><loc>{loc}</loc><lastmod>{html.escape(lastmod)}</lastmod></url>\n"
        text = text.replace("</urlset>", entry + "</urlset>", 1)
    SITEMAP.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    slug = str(required(manifest, "slug"))
    if not SLUG_RE.fullmatch(slug):
        die("slug must be lowercase letters/numbers separated by single hyphens")

    title = str(required(manifest, "title"))
    headline = str(required(manifest, "headline"))
    description = str(required(manifest, "description"))
    kicker = str(required(manifest, "kicker"))
    deck = str(required(manifest, "deck"))
    published_banner = str(required(manifest, "published_banner"))
    published_display = str(required(manifest, "published_display"))
    lastmod = str(required(manifest, "lastmod_utc"))
    read_label = str(manifest.get("read_label") or "Read the report")

    image_rel = str(manifest.get("image") or "")
    image_html = ""
    image_width = int(manifest.get("image_width_percent", 100))
    image_max = int(manifest.get("image_max_width", 900))
    if not (20 <= image_width <= 100):
        die("image_width_percent must be between 20 and 100")
    if not (200 <= image_max <= 1400):
        die("image_max_width must be between 200 and 1400")

    if image_rel:
        if not image_rel.startswith("assets/"):
            die("image must be a relative Canada/assets/... path")
        dest = CANADA / image_rel
        source = manifest.get("image_source")
        if source:
            source_path = Path(str(source)).expanduser()
            if not source_path.exists():
                die(f"image_source does not exist: {source_path}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, dest)
        inspect_image(dest)
        alt = html.escape(str(required(manifest, "image_alt")), quote=True)
        image_html = f'<img class="lead-art" src="{html.escape(image_rel, quote=True)}" alt="{alt}">'
    elif manifest.get("lead"):
        die("lead stories require direct JPG/PNG art in the canonical publisher")

    body = manifest.get("body_html")
    if isinstance(body, list):
        body_html = "\n".join(str(x) for x in body)
    elif isinstance(body, str):
        body_html = body
    else:
        die("body_html must be a string or list of HTML paragraph strings")
    if "data:image/" in body_html.lower():
        die("body_html may not contain embedded data-image URIs")

    sources_html = build_sources(list(manifest.get("sources") or []))
    article_template = (TEMPLATES / "article.html").read_text(encoding="utf-8")
    canonical = BASE_URL + slug + ".html"
    article_html = render(article_template, {
        "TITLE": html.escape(title),
        "DESCRIPTION": html.escape(description, quote=True),
        "CANONICAL_URL": html.escape(canonical, quote=True),
        "IMAGE_WIDTH_PERCENT": str(image_width),
        "IMAGE_MAX_WIDTH": str(image_max),
        "PUBLISHED_BANNER": html.escape(published_banner),
        "IMAGE_HTML": image_html,
        "KICKER": html.escape(kicker),
        "HEADLINE": html.escape(headline),
        "DECK": html.escape(deck),
        "PUBLISHED_DISPLAY": html.escape(published_display),
        "BODY_HTML": body_html,
        "SOURCES_HTML": sources_html,
    })

    article_path = CANADA / f"{slug}.html"
    if article_path.exists() and not manifest.get("allow_update"):
        die(f"article already exists; set allow_update only for an intentional correction: {article_path.name}")
    article_path.write_text(article_html, encoding="utf-8")

    if manifest.get("lead"):
        if manifest.get("replace_lead_authorized") is not True:
            die("lead replacement requires replace_lead_authorized: true")
        home = ensure_home_markers(HOME.read_text(encoding="utf-8"))
        old_lead = current_lead_block(home)
        old_href_m = re.search(r'<a class="read" href="([^"]+)"', old_lead)
        old_href = old_href_m.group(1) if old_href_m else ""

        lead_template = (TEMPLATES / "lead.html").read_text(encoding="utf-8").strip()
        lead_image = (
            f'<img src="{html.escape(image_rel, quote=True)}" alt="{html.escape(str(required(manifest, "image_alt")), quote=True)}" '
            f'style="display:block;width:{image_width}%;max-width:{image_max}px;height:auto;margin:18px auto 26px">'
        )
        new_lead = render(lead_template, {
            "KICKER": html.escape(kicker),
            "IMAGE_HTML": lead_image,
            "HEADLINE": html.escape(headline),
            "DECK": html.escape(deck),
            "ARTICLE_HREF": html.escape(slug + ".html", quote=True),
            "READ_LABEL": html.escape(read_label),
            "PUBLISHED_DISPLAY": html.escape(published_display),
        })

        if manifest.get("demote_previous_lead", True) and old_href and old_href != slug + ".html":
            card = demote_lead(old_lead)
            home = home.replace(FEED_INSERT, FEED_INSERT + "\n" + card, 1)

        home = re.sub(
            re.escape(LEAD_BEGIN) + r"\s*.*?\s*" + re.escape(LEAD_END),
            LEAD_BEGIN + "\n" + new_lead + "\n" + LEAD_END,
            home,
            count=1,
            flags=re.S,
        )
        updated_banner = manifest.get("updated_home_banner")
        if updated_banner:
            home, n = re.subn(r'<div class="top">UPDATED · .*?</div>', f'<div class="top">{html.escape(str(updated_banner))}</div>', home, count=1)
            if n != 1:
                die("could not update homepage timestamp banner")
        HOME.write_text(home, encoding="utf-8")

    update_sitemap(slug, lastmod)

    receipt_dir = CANADA / ".publish"
    receipt_dir.mkdir(exist_ok=True)
    receipt = {
        "protocol": 2,
        "slug": slug,
        "lead": bool(manifest.get("lead")),
        "headline": headline,
        "article": f"Canada/{slug}.html",
        "image": f"Canada/{image_rel}" if image_rel else None,
        "lastmod_utc": lastmod,
    }
    (receipt_dir / "last.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    from validate_canada_publish import main as preflight
    preflight()
    print(f"CANADA PUBLISHER READY TO COMMIT: {article_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
