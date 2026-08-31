#!/usr/bin/env python3
"""Refresh Canada at War's THE TICK from a tightly curated source set.

Editorial rule: reliability problems must not be solved by broadening the beat.
The domestic lane keeps the original Canada at War sources.  A separate Europe
lane may contribute only items that independently pass the same Canada + issue
relevance test.

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
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

PAGE = Path("Canada/index.html")
ET_ZONE = ZoneInfo("America/Toronto")
USER_AGENT = (
    "Mozilla/5.0 (compatible; CanadaAtWar-HourlyTick/1.1; "
    "+https://brazilginga.neocities.org/Canada/)"
)

# The original, editorially tight Canada at War source set.
DOMESTIC_FEEDS = (
    ("CBC Politics", "https://www.cbc.ca/webfeed/rss/rss-politics"),
    ("CBC Business", "https://www.cbc.ca/webfeed/rss/rss-business"),
    ("Global Politics", "https://globalnews.ca/politics/feed/"),
    ("Global Money", "https://globalnews.ca/money/feed/"),
    (
        "Global Affairs Canada",
        "https://api.io.canada.ca/io-server/gc/news/en/v2?atomtitle=Global+Affairs+Canada+news&dept=departmentofforeignaffairstradeanddevelopment&format=atom&orderBy=desc&pick=1000&publishedDate%3E=2015-01-01&sort=publishedDate",
    ),
)

# Europe is a separate lane, not a broadening of the domestic feed.  Items from
# these sources still must pass the Canada anchor + Canada-at-War issue filter.
EUROPE_FEEDS = (
    (
        "European Parliament Delegations",
        "https://www.europarl.europa.eu/rss/doc/last-news-delegations/en.xml",
    ),
    (
        "European Parliament Press",
        "https://www.europarl.europa.eu/rss/doc/press-releases/en.xml",
    ),
    (
        "EU Council Press",
        "https://www.consilium.europa.eu/en/rss/pressreleases.ashx",
    ),
    ("POLITICO Europe", "https://www.politico.eu/feed/"),
)

CANADA_ANCHORS = (
    "canada", "canadian", "carney", "anand", "ontario", "ottawa", "quebec",
    "alberta", "british columbia", "b.c.", "usmca", "cusma", "ceta", "norad",
    "f-35", "gripen", "lake ontario", "lake america", "freeland", "joly",
    "champagne", "eu-canada", "eu–canada", "canada-eu", "canada–eu",
)

CORE_TERMS = (
    "trump", "tariff", "trade", "united states", "u.s.", "washington", "usmca",
    "cusma", "ceta", "sovereign", "sovereignty", "apple", "lake ontario",
    "lake america", "china", "beijing", "europe", "european union", " eu ",
    "mexico", "norad", "nato", "f-35", "gripen", "defence", "defense",
    "critical mineral", "critical raw material", "steel", "aluminum", "aluminium",
    "dairy", "sanction", "foreign affairs", "g20", "g7", "51st state",
    "digital sovereignty", "strategic partnership", "gymnich", "energy security",
)

ISSUE_TERMS = (
    "trump", "tariff", "trade", "united states", "u.s.", "washington", "apple",
    "toyota", "honda", "auto", "automaker", "china", "beijing", "europe",
    "european union", " eu ", "mexico", "sovereign", "defence", "defense",
    "norad", "nato", "f-35", "gripen", "critical mineral", "critical raw material",
    "steel", "aluminum", "aluminium", "dairy", "border", "sanction",
    "foreign affairs", "g20", "g7", "economy", "economic", "export", "import",
    "investment", "supply chain", "map", "lake ontario", "lake america",
    "51st state", "digital sovereignty", "ceta", "strategic partnership",
    "gymnich", "energy security",
)

STRONG_TERMS = (
    "trump", "tariff", "trade", "usmca", "cusma", "ceta", "sovereign", "norad",
    "f-35", "gripen", "apple", "lake ontario", "lake america", "toyota", "honda",
    "strategic partnership",
)


@dataclass(frozen=True)
class Item:
    title: str
    link: str
    summary: str
    published: datetime
    source: str
    lane: str
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
    """Suppress routine stories already outside the Canada at War editorial beat."""
    t = f" {title.lower()} "
    is_gm = re.search(r"\bgm\b", t) is not None or "general motors" in t
    if is_gm and not any(
        x in t for x in ("tariff", "trade", "trump", "u.s.", "united states", "washington")
    ):
        return True
    return False


def score_item(title: str, summary: str, source: str, lane: str) -> int:
    if suppress_title(title):
        return -1
    text = f" {title} {summary} ".lower()

    # This is the key anti-dilution rule.  Even a European source must be about
    # Canada AND one of the publication's defined conflict/sovereignty themes.
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
    if lane == "europe":
        # A small tie-break only after the item has independently passed the
        # Canada-at-War relevance gate.  This creates a European window without
        # allowing generic European news into the ticker.
        score += 2
    if any(
        x in text
        for x in ("tariff", "trade", "sovereign", "norad", "f-35", "gripen", "ceta")
    ):
        score += 3
    return score


def fetch_bytes(url: str) -> bytes:
    """Fetch a feed with retries and two transports before declaring it dead.

    CBC's feeds proved relevant but occasionally stalled from GitHub runners.
    We therefore retry the same source and then fall back from urllib to curl;
    we do not substitute a broader news source simply because a fetch timed out.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        "Accept-Encoding": "gzip, deflate",
    }
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=14) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)

    cmd = [
        "curl", "--fail", "--silent", "--show-error", "--location", "--compressed",
        "--retry", "2", "--retry-delay", "1", "--connect-timeout", "6",
        "--max-time", "20", "--user-agent", USER_AGENT,
        "--header", headers["Accept"], url,
    ]
    try:
        completed = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if completed.stdout:
            return completed.stdout
    except Exception as exc:
        last_error = exc

    raise RuntimeError(str(last_error) if last_error else "feed fetch failed")


def fetch_feed(source: str, url: str, lane: str) -> list[Item]:
    data = fetch_bytes(url)
    root = ET.fromstring(data)
    nodes = [
        n for n in root.iter()
        if n.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}
    ]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=36)
    items: list[Item] = []
    for node in nodes[:100]:
        title = clean_text(child_text(node, ("title",)))
        summary = clean_text(child_text(node, ("description", "summary", "content")))
        link = item_link(node)
        published = parse_date(child_text(node, ("pubdate", "published", "updated", "date")))
        if not title or not link or published < cutoff:
            continue
        score = score_item(title, summary, source, lane)
        if score < 0:
            continue
        items.append(Item(title, link, summary, published, source, lane, score))
    return items


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def topic_label(title: str) -> str:
    t = f" {title.lower()} "
    if any(x in t for x in ("norad", "f-35", "gripen", "defence", "defense", "nato")):
        return "DEFENCE"
    if any(x in t for x in ("toyota", "honda", "automaker", " auto ", "vehicle")):
        return "AUTO WAR"
    if any(x in t for x in ("apple", "lake ontario", "lake america", " map ")):
        return "SOVEREIGNTY"
    if any(x in t for x in ("ceta", "europe", "european union", " eu ", "anand", "gymnich")):
        return "EUROPE"
    if any(x in t for x in ("china", "beijing")):
        return "CHINA"
    if any(x in t for x in ("tariff", "trade", "usmca", "cusma", "export", "import")):
        return "TRADE WAR"
    if any(x in t for x in ("trump", "washington", "united states", "u.s.")):
        return "WASHINGTON"
    return "CANADA"


def existing_unique_anchors(text: str) -> list[tuple[str, str]]:
    match = re.search(
        r'<div class="ticker-track">(.*?)</div></div></div><div class="markets">',
        text,
        re.S,
    )
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
    candidates: list[Item] = []
    errors: list[str] = []
    domestic_success = 0
    europe_success = 0

    for source, url in DOMESTIC_FEEDS:
        try:
            candidates.extend(fetch_feed(source, url, "domestic"))
            domestic_success += 1
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    # Refuse to rewrite the ticker if the core source set is substantially down.
    if domestic_success < 3:
        for error in errors:
            print(f"Feed error: {error}", file=sys.stderr)
        raise SystemExit(
            f"Only {domestic_success}/{len(DOMESTIC_FEEDS)} core ticker feeds were reachable; "
            "refusing to rewrite THE TICK"
        )

    for source, url in EUROPE_FEEDS:
        try:
            candidates.extend(fetch_feed(source, url, "europe"))
            europe_success += 1
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    dedup: dict[str, Item] = {}
    for item in candidates:
        key = normalize_title(item.title)
        old = dedup.get(key)
        if old is None or (item.score, item.published) > (old.score, old.published):
            dedup[key] = item

    ranked = sorted(
        dedup.values(),
        key=lambda x: (x.score, x.published),
        reverse=True,
    )
    europe_ranked = [item for item in ranked if item.lane == "europe"]

    selected: list[tuple[str, str]] = []
    seen_titles: set[str] = set()
    seen_hrefs: set[str] = set()

    def add_item(item: Item) -> bool:
        key = normalize_title(item.title)
        if key in seen_titles or item.link in seen_hrefs:
            return False
        label = f"{topic_label(item.title)} · {item.title} — {item.source}"
        selected.append((item.link, label))
        seen_titles.add(key)
        seen_hrefs.add(item.link)
        return True

    # If Europe has genuinely relevant Canada-at-War material, reserve up to two
    # of six slots for it.  Never manufacture a European slot with generic news.
    for item in europe_ranked[:2]:
        add_item(item)

    for item in ranked:
        add_item(item)
        if len(selected) >= 6:
            break

    # If today's filtered feeds yield fewer than five items, retain recent existing
    # ticker items rather than filling space with off-beat material.
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
        raise SystemExit(
            "No relevant ticker items and no existing ticker fallback; refusing to rewrite THE TICK"
        )

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
    text, label_count = re.subn(
        r'<span class="tick-label">THE TICK(?: · CHECKED [^<]+)?</span>',
        label,
        text,
        count=1,
    )
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
    europe_selected = sum(1 for _, label in selected if "European Parliament" in label or "EU Council" in label or "POLITICO Europe" in label)
    print(
        f"THE TICK checked {checked}; core feeds {domestic_success}/{len(DOMESTIC_FEEDS)}; "
        f"Europe feeds {europe_success}/{len(EUROPE_FEEDS)}; "
        f"{len(selected)} headlines selected ({europe_selected} from Europe lane)."
    )
    for href, label in selected:
        print(f"- {label} -> {href}")
    for error in errors:
        print(f"Feed warning: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
