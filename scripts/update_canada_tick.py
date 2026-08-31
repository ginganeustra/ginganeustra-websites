#!/usr/bin/env python3
"""Refresh Canada at War's THE TICK from current public RSS/Atom feeds.

This script edits only the ticker label and ticker-track region in Canada/index.html.
It does not touch story ordering, the masthead, market ticker, petition, or article copy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

PAGE = Path("Canada/index.html")
ET_ZONE = ZoneInfo("America/Toronto")
USER_AGENT = "CanadaAtWar-HourlyTick/1.0 (+https://brazilginga.neocities.org/Canada/)"

FEEDS = (
    ("Global Politics", "https://globalnews.ca/politics/feed/"),
    ("Global Money", "https://globalnews.ca/money/feed/"),
    ("Global Canada", "https://globalnews.ca/canada/feed/"),
    ("Global U.S.", "https://globalnews.ca/us-news/feed/"),
    ("Global World", "https://globalnews.ca/world/feed/"),
    (
        "Global Affairs Canada",
        "https://api.io.canada.ca/io-server/gc/news/en/v2?atomtitle=Global+Affairs+Canada+news&dept=departmentofforeignaffairstradeanddevelopment&format=atom&orderBy=desc&pick=1000&publishedDate%3E=2015-01-01&sort=publishedDate",
    ),
)

CANADA_ANCHORS = (
    "canada", "canadian", "carney", "anand", "ontario", "ottawa", "quebec",
    "alberta", "british columbia", "b.c.", "usmca", "cusma", "norad", "f-35",
    "gripen", "lake ontario", "lake america", "freeland", "joly", "champagne",
)

CORE_TERMS = (
    "trump", "tariff", "trade", "united states", "u.s.", "washington", "usmca",
    "cusma", "sovereign", "sovereignty", "apple", "lake ontario", "lake america",
    "china", "beijing", "europe", "european union", " eu ", "mexico", "norad",
    "f-35", "gripen", "defence", "defense", "critical mineral", "steel",
    "aluminum", "aluminium", "dairy", "sanction", "foreign affairs", "g20", "g7",
    "51st state", "digital sovereignty",
)

ISSUE_TERMS = (
    "trump", "tariff", "trade", "united states", "u.s.", "washington", "apple",
    "toyota", "honda", "auto", "automaker", "china", "beijing", "europe",
    "european union", " eu ", "mexico", "sovereign", "defence", "defense",
    "norad", "f-35", "gripen", "critical mineral", "steel", "aluminum",
    "aluminium", "dairy", "border", "sanction", "foreign affairs", "g20", "g7",
    "economy", "economic", "export", "import", "investment", "supply chain",
    "map", "lake ontario", "lake america", "51st state", "digital sovereignty",
)

STRONG_TERMS = (
    "trump", "tariff", "trade", "usmca", "cusma", "sovereign", "norad", "f-35",
    "gripen", "apple", "lake ontario", "lake america", "toyota", "honda",
)


@dataclass(frozen=True)
class Item:
    title: str
    link: str
    summary: str
    published: datetime
    source: str
    score: int


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names and child.text:
            return child.text
    return ""


def item_link(node: ET.Element) -> str:
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = child.attrib.get("href", "").strip()
        if href.startswith(("https://", "http://")):
            return href
        text = (child.text or "").strip()
        if text.startswith(("https://", "http://")):
            return text
    return ""


def suppress_title(title: str) -> bool:
    t = f" {title.lower()} "
    is_gm = re.search(r"\bgm\b", t) is not None or "general motors" in t
    if is_gm and not any(x in t for x in ("tariff", "trade", "trump", "u.s.", "united states", "washington")):
        return True
    return False


def score_item(title: str, summary: str, source: str) -> int:
    if suppress_title(title):
        return -1
    text = f" {title} {summary} ".lower()
    if not any(anchor in text for anchor in CANADA_ANCHORS):
        return -1
    if not any(term in text for term in CORE_TERMS):
        return -1
    hits = sum(1 for term in ISSUE_TERMS if term in text)
    if hits == 0:
        return -1
    score = hits * 3
    score += sum(4 for term in STRONG_TERMS if term in text)
    if source == "Global Affairs Canada":
        score += 2
    if any(x in text for x in ("tariff", "trade", "sovereign", "norad", "f-35", "gripen")):
        score += 3
    return score


def fetch_feed(source: str, url: str) -> list[Item]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=12) as response:
        data = response.read()
    root = ET.fromstring(data)
    nodes = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=36)
    items: list[Item] = []
    for node in nodes[:80]:
        title = clean_text(child_text(node, ("title",)))
        summary = clean_text(child_text(node, ("description", "summary", "content")))
        link = item_link(node)
        published = parse_date(child_text(node, ("pubdate", "published", "updated", "date")))
        if not title or not link or published < cutoff:
            continue
        score = score_item(title, summary, source)
        if score < 0:
            continue
        items.append(Item(title, link, summary, published, source, score))
    return items


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def topic_label(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ("norad", "f-35", "gripen", "defence", "defense")):
        return "DEFENCE"
    if any(x in t for x in ("toyota", "honda", "automaker", "auto ", "vehicle")):
        return "AUTO WAR"
    if any(x in t for x in ("apple", "lake ontario", "lake america", "map")):
        return "SOVEREIGNTY"
    if any(x in t for x in ("europe", "european union", " eu ", "anand")):
        return "EUROPE"
    if any(x in t for x in ("china", "beijing")):
        return "CHINA"
    if any(x in t for x in ("tariff", "trade", "usmca", "cusma", "export", "import")):
        return "TRADE WAR"
    if any(x in t for x in ("trump", "washington", "united states", "u.s.")):
        return "WASHINGTON"
    return "CANADA"


def existing_unique_anchors(text: str) -> list[tuple[str, str]]:
    match = re.search(r'<div class="ticker-track">(.*?)</div></div></div><div class="markets">', text, re.S)
    if not match:
        return []
    anchors = re.findall(r'<a href="([^"]+)">(.*?)</a>', match.group(1), re.S)
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for href, label in anchors:
        label_plain = clean_text(label)
        if suppress_title(label_plain):
            continue
        key = (href, normalize_title(label_plain))
        if key in seen:
            continue
        seen.add(key)
        out.append((href, label_plain))
    return out


def build_anchor(href: str, label: str) -> str:
    return f'<a href="{escape(href, quote=True)}">{escape(label)}</a>'


def main() -> int:
    text = PAGE.read_text(encoding="utf-8")
    successful = 0
    candidates: list[Item] = []
    errors: list[str] = []

    for source, url in FEEDS:
        try:
            candidates.extend(fetch_feed(source, url))
            successful += 1
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    if successful < 3:
        for error in errors:
            print(f"Feed error: {error}", file=sys.stderr)
        raise SystemExit(f"Only {successful} ticker feeds were reachable; refusing to rewrite THE TICK")

    dedup: dict[str, Item] = {}
    for item in candidates:
        key = normalize_title(item.title)
        old = dedup.get(key)
        if old is None or (item.score, item.published) > (old.score, old.published):
            dedup[key] = item
    ranked = sorted(dedup.values(), key=lambda x: (x.score, x.published), reverse=True)

    selected: list[tuple[str, str]] = []
    seen_titles: set[str] = set()
    seen_hrefs: set[str] = set()
    for item in ranked:
        label = f"{topic_label(item.title)} · {item.title} — {item.source}"
        key = normalize_title(item.title)
        if key in seen_titles or item.link in seen_hrefs:
            continue
        seen_titles.add(key)
        seen_hrefs.add(item.link)
        selected.append((item.link, label))
        if len(selected) >= 6:
            break

    if len(selected) < 5:
        for href, label in existing_unique_anchors(text):
            if href in seen_hrefs:
                continue
            key = normalize_title(label.split(" · ", 1)[-1].split(" — ", 1)[0])
            if key in seen_titles:
                continue
            selected.append((href, label))
            seen_hrefs.add(href)
            seen_titles.add(key)
            if len(selected) >= 6:
                break

    if not selected:
        raise SystemExit("No relevant ticker items and no existing ticker fallback; refusing to rewrite THE TICK")

    one_pass = "".join(build_anchor(href, label) for href, label in selected)
    track = (
        '<div class="ticker-track"><!-- HOURLY_TICK_AUTO_BEGIN -->'
        + one_pass + one_pass
        + '<!-- HOURLY_TICK_AUTO_END --></div></div></div><div class="markets">'
    )
    text, track_count = re.subn(
        r'<div class="ticker-track">.*?</div></div></div><div class="markets">',
        track,
        text,
        count=1,
        flags=re.S,
    )
    if track_count != 1:
        raise SystemExit("Could not locate the protected THE TICK track in Canada/index.html")

    checked = datetime.now(ET_ZONE).strftime("%H:%M ET")
    label = f'<span class="tick-label">THE TICK · CHECKED {checked}</span>'
    text, label_count = re.subn(r'<span class="tick-label">THE TICK(?: · CHECKED [^<]+)?</span>', label, text, count=1)
    if label_count != 1:
        raise SystemExit("Could not locate THE TICK label in Canada/index.html")

    required = (
        "CANADA_AT_WAR_MASTHEAD_LOCK",
        "PINNED_LEAD_LOCK",
        "tradingview-widget-container",
        "canada-at-war-goose-eagle-v3.jpg",
        "petition-paint-mix",
        "How Lying Works",
        "HOURLY_TICK_AUTO_BEGIN",
        "HOURLY_TICK_AUTO_END",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise SystemExit("Ticker safety guard failed; missing: " + ", ".join(missing))

    PAGE.write_text(text, encoding="utf-8")
    print(f"THE TICK checked {checked}; {successful}/{len(FEEDS)} feeds reachable; {len(selected)} headlines selected.")
    for href, label in selected:
        print(f"- {label} -> {href}")
    for error in errors:
        print(f"Feed warning: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
