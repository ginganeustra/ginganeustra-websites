#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import ssl
import urllib.parse
import urllib.request
from html.parser import HTMLParser

OUT = "Rustler/assets"
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (compatible; TheRustler/1.0; +https://therustler.neocities.org/)"
CTX = ssl.create_default_context()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read()


def save_direct(name: str, url: str) -> bool:
    try:
        data = fetch(url)
        if len(data) < 1500:
            raise RuntimeError(f"download too small: {len(data)} bytes")
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)
        print(f"saved {name} from {url} ({len(data)} bytes)")
        return True
    except Exception as e:
        print(f"WARN direct {name}: {e}")
        return False


class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.og = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag.lower() == "img":
            src = d.get("src") or d.get("data-src") or d.get("data-lazy-src")
            if src:
                self.images.append((src, d.get("alt", ""), d.get("class", "")))
        if tag.lower() == "meta" and d.get("property") == "og:image" and d.get("content"):
            self.og.append(d["content"])


def save_from_page(name: str, page: str, keywords: list[str], fallback: str | None = None) -> bool:
    try:
        html = fetch(page).decode("utf-8", "ignore")
        p = ImgParser(); p.feed(html)
        scored = []
        for src, alt, cls in p.images:
            hay = f"{src} {alt} {cls}".lower()
            score = sum(4 for k in keywords if k.lower() in hay)
            if any(x in hay for x in ["logo", "icon", "spinner", "avatar"]):
                score -= 2
            if score > 0:
                scored.append((score, src, alt))
        if scored:
            scored.sort(reverse=True)
            _, src, alt = scored[0]
            return save_direct(name, urllib.parse.urljoin(page, src))
        if p.og:
            return save_direct(name, urllib.parse.urljoin(page, p.og[0]))
        raise RuntimeError("no matching image")
    except Exception as e:
        print(f"WARN page {name}: {e}")
        if fallback and os.path.exists(os.path.join(OUT, fallback)):
            shutil.copy2(os.path.join(OUT, fallback), os.path.join(OUT, name))
            print(f"copied fallback {fallback} -> {name}")
            return True
        return False


# Strong official/courtesy photographs with stable URLs.
save_direct("rec-complex.jpg", "https://russell.ca/wp-content/uploads/2026/06/Rec-Complex.jpg")
save_direct("town-hall.jpg", "https://russell.ca/wp-content/uploads/2026/06/Town-Hall-at-Night_original.jpg")
save_direct("waste-collection.jpg", "https://russell.ca/wp-content/uploads/2026/07/Collection-1920x1080_july6-scaled.jpg")
save_direct("main-street.jpg", "https://www.therecordnews.ca/wp-content/uploads/2026/09/TT-Russell-funding-announcement-RGB.jpg")

# Pull the most relevant current image from official pages; use only official/courtesy fallbacks.
save_from_page(
    "notre-dame.jpg",
    "https://russell.ca/fr/construction-et-developpement/projets-en-cours/projet-de-rehabilitation-de-la-rue-notre-dame/",
    ["zone de construction", "construction", "fermeture", "closure"],
    "town-hall.jpg",
)
save_from_page(
    "water-tower.jpg",
    "https://russell.ca/news-and-notices/important-update-on-embrun-water-restrictions/",
    ["water", "tower", "eau", "chateau"],
    "town-hall.jpg",
)
save_from_page(
    "autumn-photo-expo.jpg",
    "https://russell.ca/culture-and-community/your-community/photography-club/photo-expo/",
    ["poster", "photo expo", "exposition", "recreational trail"],
    "town-hall.jpg",
)
save_from_page(
    "trail.jpg",
    "https://russell.ca/",
    ["russell weir", "trail", "sentier"],
    "town-hall.jpg",
)
save_from_page(
    "library-ai.jpg",
    "https://russellbiblio.com/2026/08/18/practical-ai-skills-for-everyday-life/",
    ["ai written", "computer", "laptop"],
    "town-hall.jpg",
)
save_from_page(
    "eorn.jpg",
    "https://eorn.ca/340593-2/",
    ["speakers", "cell gap", "august 20"],
    "town-hall.jpg",
)
save_from_page(
    "ucpr.jpg",
    "https://en.prescott-russell.on.ca/",
    ["prescott", "russell", "logo", "counties"],
    "town-hall.jpg",
)
save_from_page(
    "eohu.jpg",
    "https://www.eohu.ca/en/my-environment/west-nile-virus",
    ["west nile", "mosquito", "eohu", "logo"],
    "town-hall.jpg",
)

required = [
    "rec-complex.jpg", "town-hall.jpg", "waste-collection.jpg", "main-street.jpg",
    "notre-dame.jpg", "water-tower.jpg", "autumn-photo-expo.jpg", "trail.jpg",
    "library-ai.jpg", "eorn.jpg", "ucpr.jpg", "eohu.jpg"
]
missing = [x for x in required if not os.path.exists(os.path.join(OUT, x))]
if missing:
    raise SystemExit("Missing Rustler visual assets: " + ", ".join(missing))
