#!/usr/bin/env python3
from __future__ import annotations

import os
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


def copy_fallback(name: str, fallback: str) -> bool:
    src = os.path.join(OUT, fallback)
    dst = os.path.join(OUT, name)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"copied fallback {fallback} -> {name}")
        return True
    return False


class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.images=[]; self.og=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag.lower()=="img":
            src=d.get("src") or d.get("data-src") or d.get("data-lazy-src")
            if src: self.images.append((src,d.get("alt",""),d.get("class","")))
        if tag.lower()=="meta" and d.get("property")=="og:image" and d.get("content"):
            self.og.append(d["content"])


def save_from_page(name: str, page: str, keywords: list[str], fallback: str) -> bool:
    try:
        html=fetch(page).decode("utf-8","ignore")
        p=ImgParser(); p.feed(html)
        scored=[]
        for src,alt,cls in p.images:
            hay=f"{src} {alt} {cls}".lower()
            score=sum(4 for k in keywords if k.lower() in hay)
            if any(x in hay for x in ["icon","spinner","avatar","living wage"]): score-=8
            if score>0: scored.append((score,src,alt))
        scored.sort(reverse=True)
        for _,src,alt in scored:
            if save_direct(name,urllib.parse.urljoin(page,src)):
                print(f"matched alt for {name}: {alt}")
                return True
        for src in p.og:
            if save_direct(name,urllib.parse.urljoin(page,src)): return True
        raise RuntimeError("no usable matching image")
    except Exception as e:
        print(f"WARN page {name}: {e}")
        return copy_fallback(name,fallback)


# Stable official photographs. These are the preferred base set.
if not save_direct("rec-complex.jpg","https://russell.ca/wp-content/uploads/2026/06/Rec-Complex.jpg"):
    raise SystemExit("Could not fetch official Recreation Complex photo")
if not save_direct("town-hall.jpg","https://russell.ca/wp-content/uploads/2026/06/Town-Hall-at-Night_original.jpg"):
    copy_fallback("town-hall.jpg","rec-complex.jpg")
if not save_direct("waste-collection.jpg","https://russell.ca/wp-content/uploads/2026/07/Collection-1920x1080_july6-scaled.jpg"):
    copy_fallback("waste-collection.jpg","town-hall.jpg")
if not save_direct("main-street.jpg","https://www.therecordnews.ca/wp-content/uploads/2026/09/TT-Russell-funding-announcement-RGB.jpg"):
    copy_fallback("main-street.jpg","town-hall.jpg")

# Current official/civic pages. If a page has no usable photo, a real official Township photo is used rather than fake local photography.
save_from_page("notre-dame.jpg","https://russell.ca/fr/construction-et-developpement/projets-en-cours/projet-de-rehabilitation-de-la-rue-notre-dame/",["zone de construction","construction","fermeture","closure"],"town-hall.jpg")
save_from_page("water-tower.jpg","https://russell.ca/news-and-notices/important-update-on-embrun-water-restrictions/",["water tower","chateau d'eau","water restrictions","restrictions"],"town-hall.jpg")
save_from_page("autumn-photo-expo.jpg","https://russell.ca/culture-and-community/your-community/photography-club/photo-expo/",["poster","photo expo","exposition","recreational trail"],"town-hall.jpg")
save_from_page("trail.jpg","https://russell.ca/",["russell weir","trail","sentier"],"town-hall.jpg")
save_from_page("library-ai.jpg","https://russellbiblio.com/2026/08/18/practical-ai-skills-for-everyday-life/",["ai written","computer","laptop"],"town-hall.jpg")
# Use a public EORN page that exposes its own branded logo image, rather than the event page that blocks automated requests.
save_from_page("eorn.jpg","https://eorn.ca/resources-for-residents/",["eorn_logo-subtext","eastern ontario regional network"],"town-hall.jpg")
save_from_page("ucpr.jpg","https://en.prescott-russell.on.ca/",["prescott","russell","counties","logo"],"town-hall.jpg")
# EOHU's general West Nile page contains unrelated partner logos. Use a page whose header explicitly exposes the health-unit identity.
save_from_page("eohu.jpg","https://eohu.ca/en/breastfeeding/more-formula-and-bottle-feeding-resources",["eastern ontario health unit","bureau de santé de l'est de l'ontario","bureau de sante de l'est de l'ontario"],"town-hall.jpg")

required=["rec-complex.jpg","town-hall.jpg","waste-collection.jpg","main-street.jpg","notre-dame.jpg","water-tower.jpg","autumn-photo-expo.jpg","trail.jpg","library-ai.jpg","eorn.jpg","ucpr.jpg","eohu.jpg"]
missing=[x for x in required if not os.path.exists(os.path.join(OUT,x)) or os.path.getsize(os.path.join(OUT,x))<1500]
if missing: raise SystemExit("Missing Rustler visual assets: "+", ".join(missing))
