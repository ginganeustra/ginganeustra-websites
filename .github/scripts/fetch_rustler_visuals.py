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


def save_from_page(name: str, page: str, keywords: list[str], fallback: str, allow_og: bool = True) -> bool:
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
        if allow_og:
            for src in p.og:
                if save_direct(name,urllib.parse.urljoin(page,src)): return True
        raise RuntimeError("no usable matching image")
    except Exception as e:
        print(f"WARN page {name}: {e}")
        return copy_fallback(name,fallback)


# Stable official photographs.
if not save_direct("rec-complex.jpg","https://russell.ca/wp-content/uploads/2026/06/Rec-Complex.jpg"):
    raise SystemExit("Could not fetch official Recreation Complex photo")
if not save_direct("town-hall.jpg","https://russell.ca/wp-content/uploads/2026/06/Town-Hall-at-Night_original.jpg"):
    copy_fallback("town-hall.jpg","rec-complex.jpg")
if not save_direct("waste-collection.jpg","https://russell.ca/wp-content/uploads/2026/07/Collection-1920x1080_july6-scaled.jpg"):
    copy_fallback("waste-collection.jpg","town-hall.jpg")
if not save_direct("main-street.jpg","https://www.therecordnews.ca/wp-content/uploads/2026/09/TT-Russell-funding-announcement-RGB.jpg"):
    copy_fallback("main-street.jpg","town-hall.jpg")

# Official people photography and Township branding.
save_from_page("mayor-council.jpg","https://russell.ca/",["mayor and council"],"town-hall.jpg",allow_og=False)
# Use the verified Mayor-and-Council photograph for the election card rather than a stale portrait URL that was returning a broken image.
copy_fallback("mayor-tarnowski-v2.jpg","mayor-council.jpg")
save_from_page("rec-groundbreaking.jpg","https://russell.ca/news-and-notices/groundbreaking-ceremony-at-the-recreation-complex/",["group in front of construction site","construction site","groundbreaking"],"rec-complex.jpg",allow_og=False)
# Official Russell Township logo, used when the source story has no usable photograph.
if not save_direct("township-logo-v2.png","https://www.russell.ca/en/your-township/resources/Council/Township-Logo-Blue.png"):
    copy_fallback("township-logo-v2.png","town-hall.jpg")

# Current official/civic pages.
save_from_page("notre-dame.jpg","https://russell.ca/fr/construction-et-developpement/projets-en-cours/projet-de-rehabilitation-de-la-rue-notre-dame/",["zone de construction","construction","fermeture","closure"],"town-hall.jpg",allow_og=False)
# Verified editorial visuals for the current Rustler edition.
if not save_direct("autumn-maple-leaf-water.jpg","https://images.pexels.com/photos/29237867/pexels-photo-29237867.jpeg?cs=srgb&dl=pexels-aj4xo-29237867.jpg&fm=jpg"):
    raise SystemExit("Could not fetch Pexels maple-leaf photograph")
if not save_direct("terry-fox.jpg","https://upload.wikimedia.org/wikipedia/commons/2/2c/TerryFoxToronto19800712.JPG"):
    raise SystemExit("Could not fetch public-domain Terry Fox photograph")
save_from_page("trail.jpg","https://russell.ca/",["russell weir","trail","sentier"],"town-hall.jpg",allow_og=False)
save_from_page("library-ai.jpg","https://russellbiblio.com/2026/08/18/practical-ai-skills-for-everyday-life/",["ai written","computer","laptop"],"town-hall.jpg",allow_og=False)
# The official EORN logo is a vetted, checked-in asset. EORN’s CMS blocks this action runner’s direct requests.
if not os.path.exists(os.path.join(OUT, "eorn-logo.png")):
    raise SystemExit("Bundled official EORN logo is missing")
save_from_page("ucpr.jpg","https://en.prescott-russell.on.ca/",["prescott","russell","counties","logo"],"town-hall.jpg",allow_og=False)
save_from_page("eohu.jpg","https://eohu.ca/en/breastfeeding/more-formula-and-bottle-feeding-resources",["eastern ontario health unit","bureau de santé de l'est de l'ontario","bureau de sante de l'est de l'ontario"],"town-hall.jpg",allow_og=False)

required=["rec-complex.jpg","town-hall.jpg","waste-collection.jpg","main-street.jpg","mayor-council.jpg","mayor-tarnowski-v2.jpg","rec-groundbreaking.jpg","township-logo-v2.png","notre-dame.jpg","autumn-maple-leaf-water.jpg","terry-fox.jpg","trail.jpg","library-ai.jpg","eorn-logo.png","ucpr.jpg","eohu.jpg"]
missing=[x for x in required if not os.path.exists(os.path.join(OUT,x)) or os.path.getsize(os.path.join(OUT,x))<1500]
if missing: raise SystemExit("Missing Rustler visual assets: "+", ".join(missing))
