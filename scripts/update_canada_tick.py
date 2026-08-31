#!/usr/bin/env python3
"""Refresh Canada at War's THE TICK.

The ticker combines a current Canadian-news lane, an official Government of
Canada announcements lane, and a narrow Europe lane. Official federal releases
come from the Canada News Centre National News feed, so the ticker is not
limited to Global Affairs Canada announcements.

Only THE TICK label and ticker-track region in Canada/index.html are edited.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import escape, unescape
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

PAGE = Path("Canada/index.html")
ET_ZONE = ZoneInfo("America/Toronto")
USER_AGENT = "Mozilla/5.0 (compatible; CanadaAtWar-HourlyTick/1.6; +https://brazilginga.neocities.org/Canada/)"
ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html, */*"
MAX_HEADLINES = 5
FEDERAL_SLOTS = 2
EUROPE_SLOTS = 1

# Main Canadian news sources.
DOMESTIC_FEEDS = (
    ("CBC Politics", "https://rss.cbc.ca/lineup/politics.xml"),
    ("CBC Business", "https://rss.cbc.ca/lineup/business.xml"),
    ("Global Canada", "https://globalnews.ca/canada/feed/"),
    ("Global Politics", "https://globalnews.ca/politics/feed/"),
    ("Global Money", "https://globalnews.ca/money/feed/"),
    (
        "Global Affairs Canada",
        "https://api.io.canada.ca/io-server/gc/news/en/v2?atomtitle=Global+Affairs+Canada+news&dept=departmentofforeignaffairstradeanddevelopment&format=atom&orderBy=desc&pick=1000&publishedDate%3E=2015-01-01&sort=publishedDate",
    ),
)

# Official Canada News Centre feed across the federal government. This is the
# source that restores announcements from departments beyond Global Affairs.
FEDERAL_FEEDS = (
    (
        "Government of Canada",
        "https://api.io.canada.ca/io-server/gc/news/en/v2?sort=publishedDate&orderBy=desc&pick=100&format=atom&atomtitle=National%20News",
    ),
)

CBC_PAGE_FALLBACKS = {
    "CBC Politics": "https://www.cbc.ca/news/politics",
    "CBC Business": "https://www.cbc.ca/news/business",
}

EUROPE_FEEDS = (
    ("European Commission Trade", "https://policy.trade.ec.europa.eu/node/2/rss_en"),
    ("EU Council Press", "https://www.consilium.europa.eu/en/rss/pressreleases.ashx"),
    ("POLITICO Europe", "https://www.politico.eu/feed/"),
)
EUROPE_PAGES = (
    ("EEAS Canada", "https://www.eeas.europa.eu/canada_en"),
)

CANADA_ANCHORS = (
    "canada", "canadian", "carney", "anand", "ontario", "ottawa", "quebec", "alberta",
    "british columbia", "b.c.", "usmca", "cusma", "ceta", "norad", "f-35", "gripen",
    "lake ontario", "lake america", "freeland", "joly", "champagne", "eu-canada",
    "eu–canada", "canada-eu", "canada–eu",
)
CORE_TERMS = (
    "trump", "tariff", "trade", "united states", "u.s.", "washington", "usmca", "cusma",
    "ceta", "sovereign", "sovereignty", "apple", "lake ontario", "lake america", "china",
    "beijing", "europe", "european union", " eu ", "mexico", "norad", "nato", "f-35",
    "gripen", "defence", "defense", "critical mineral", "critical raw material", "steel",
    "aluminum", "aluminium", "dairy", "sanction", "foreign affairs", "g20", "g7",
    "51st state", "digital sovereignty", "strategic partnership", "gymnich", "energy security",
)
ISSUE_TERMS = (
    "trump", "tariff", "trade", "united states", "u.s.", "washington", "apple", "toyota",
    "honda", "auto", "automaker", "china", "beijing", "europe", "european union", " eu ",
    "mexico", "sovereign", "defence", "defense", "norad", "nato", "f-35", "gripen",
    "critical mineral", "critical raw material", "steel", "aluminum", "aluminium", "dairy",
    "border", "sanction", "foreign affairs", "g20", "g7", "economy", "economic", "export",
    "import", "investment", "supply chain", "map", "lake ontario", "lake america", "51st state",
    "digital sovereignty", "ceta", "strategic partnership", "gymnich", "energy security",
)
STRONG_TERMS = (
    "trump", "tariff", "trade", "usmca", "cusma", "ceta", "sovereign", "norad", "f-35",
    "gripen", "apple", "lake ontario", "lake america", "toyota", "honda", "strategic partnership",
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
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(value))).strip()


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
        if child.tag.rsplit("}", 1)[-1].lower() in names and child.text:
            return child.text
    return ""


def item_link(node: ET.Element) -> str:
    alternate = ""
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = child.attrib.get("href", "").strip()
        rel = child.attrib.get("rel", "").strip().lower()
        if href.startswith(("https://", "http://")):
            if rel in ("", "alternate"):
                return href
            if not alternate:
                alternate = href
        text = (child.text or "").strip()
        if text.startswith(("https://", "http://")):
            return text
    return alternate


def suppress_title(title: str) -> bool:
    t = f" {title.lower()} "
    is_gm = re.search(r"\bgm\b", t) is not None or "general motors" in t
    return bool(is_gm and not any(x in t for x in ("tariff", "trade", "trump", "u.s.", "united states", "washington")))


def score_item(title: str, summary: str, source: str, lane: str) -> int:
    if suppress_title(title):
        return -1
    text = f" {title} {summary} ".lower()

    # Every current federal release is eligible. Its official-source status is
    # the Canada anchor; issue terms simply raise its rank within that lane.
    if lane == "federal" or source == "Government of Canada":
        hits = sum(1 for term in ISSUE_TERMS if term in text)
        strong = sum(1 for term in STRONG_TERMS if term in text)
        return 20 + hits * 3 + strong * 4

    # News and Europe lanes remain tightly tied to the Canada-at-War remit.
    if not any(anchor in text for anchor in CANADA_ANCHORS):
        return -1
    if not any(term in text for term in CORE_TERMS):
        return -1
    hits = sum(1 for term in ISSUE_TERMS if term in text)
    if not hits:
        return -1
    score = hits * 3 + sum(4 for term in STRONG_TERMS if term in text)
    if source == "Global Affairs Canada":
        score += 2
    if lane == "europe":
        score += 2
    if any(x in text for x in ("tariff", "trade", "sovereign", "norad", "f-35", "gripen", "ceta")):
        score += 3
    return score


def urllib_fetch(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def curl_fetch(url: str) -> bytes:
    cmd = [
        "curl", "--http1.1", "--fail", "--silent", "--show-error", "--location", "--compressed",
        "--retry", "1", "--retry-delay", "1", "--connect-timeout", "4", "--max-time", "10",
        "--user-agent", USER_AGENT, "--header", f"Accept: {ACCEPT}", url,
    ]
    completed = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
    if not completed.stdout:
        raise RuntimeError("empty response")
    return completed.stdout


def fetch_bytes(url: str) -> bytes:
    methods = (curl_fetch, urllib_fetch) if "cbc.ca" in url else (urllib_fetch, curl_fetch)
    errors: list[str] = []
    for method in methods:
        try:
            return method(url)
        except Exception as exc:
            errors.append(f"{method.__name__}: {exc}")
    raise RuntimeError(" | ".join(errors))


def fetch_feed(source: str, url: str, lane: str) -> list[Item]:
    root = ET.fromstring(fetch_bytes(url))
    nodes = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)
    items: list[Item] = []
    for node in nodes[:150]:
        title = clean_text(child_text(node, ("title",)))
        summary = clean_text(child_text(node, ("description", "summary", "content")))
        link = item_link(node)
        published = parse_date(child_text(node, ("pubdate", "published", "updated", "date")))
        if not title or not link or published < cutoff:
            continue
        score = score_item(title, summary, source, lane)
        if score >= 0:
            items.append(Item(title, link, summary, published, source, lane, score))
    return items


def html_meta(html: str, name: str) -> str:
    patterns = (
        rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\']{re.escape(name)}["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return clean_text(match.group(1))
    return ""


def article_date(html: str) -> datetime | None:
    patterns = (
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'<meta[^>]+(?:property|name)=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
        r'<time[^>]+datetime=["\']([^"\']+)',
    )
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return parse_date(unescape(match.group(1)))
    return None


def fetch_html_source(source: str, url: str, lane: str) -> list[Item]:
    landing = fetch_bytes(url).decode("utf-8", errors="replace")
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    host = urlparse(url).netloc.lower()

    for href, body in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', landing, re.I | re.S):
        title = clean_text(body)
        absolute = urljoin(url, unescape(href)).split("#", 1)[0]
        parsed = urlparse(absolute)
        if not title or len(title) < 18 or len(title) > 220 or absolute in seen:
            continue
        if source.startswith("CBC"):
            if "cbc.ca" not in parsed.netloc.lower() or "/news/" not in parsed.path:
                continue
        elif source == "EEAS Canada":
            if "eeas.europa.eu" not in parsed.netloc.lower():
                continue
        elif parsed.netloc.lower() != host:
            continue
        if score_item(title, "", source, lane) < 0:
            continue
        seen.add(absolute)
        links.append((absolute, title))
        if len(links) >= 10:
            break

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    items: list[Item] = []
    for absolute, title in links:
        try:
            article_html = urllib_fetch(absolute, timeout=7).decode("utf-8", errors="replace")
        except Exception:
            continue
        published = article_date(article_html)
        if published is None or published < cutoff:
            continue
        summary = html_meta(article_html, "description") or html_meta(article_html, "og:description")
        score = score_item(title, summary, source, lane)
        if score >= 0:
            items.append(Item(title, absolute, summary, published, source, lane, score))
    return items


def fetch_domestic(source: str, url: str) -> tuple[list[Item], str | None]:
    try:
        return fetch_feed(source, url, "domestic"), None
    except Exception as feed_exc:
        fallback = CBC_PAGE_FALLBACKS.get(source)
        if not fallback:
            raise
        try:
            return fetch_html_source(source, fallback, "domestic"), f"RSS failed; used {source} page fallback: {feed_exc}"
        except Exception as page_exc:
            raise RuntimeError(f"RSS: {feed_exc} | page fallback: {page_exc}") from page_exc


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
    match = re.search(r'<div class="ticker-track">(.*?)</div></div></div><div class="markets">', text, re.S)
    if not match:
        return []
    approved_sources = (
        "Government of Canada", "CBC Politics", "CBC Business", "Global Canada", "Global Politics", "Global Money",
        "Global Affairs Canada", "European Commission Trade", "EU Council Press", "POLITICO Europe", "EEAS Canada",
    )
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for href, label in re.findall(r'<a href="([^"]+)">(.*?)</a>', match.group(1), re.S):
        plain = clean_text(label)
        if suppress_title(plain) or not any(source in plain for source in approved_sources):
            continue
        key = (href, normalize_title(plain))
        if key not in seen:
            seen.add(key)
            out.append((href, plain))
    return out


def build_anchor(href: str, label: str) -> str:
    return f'<a href="{escape(href, quote=True)}">{escape(label)}</a>'


def main() -> int:
    text = PAGE.read_text(encoding="utf-8")
    candidates: list[Item] = []
    errors: list[str] = []
    notes: list[str] = []
    domestic_success = 0
    federal_success = 0
    europe_success = 0

    jobs: list[tuple[str, str, str, str]] = []
    for source, url in DOMESTIC_FEEDS:
        jobs.append((source, url, "domestic", "domestic"))
    for source, url in FEDERAL_FEEDS:
        jobs.append((source, url, "federal", "feed"))
    for source, url in EUROPE_FEEDS:
        jobs.append((source, url, "europe", "feed"))
    for source, url in EUROPE_PAGES:
        jobs.append((source, url, "europe", "page"))

    def run_job(source: str, url: str, lane: str, kind: str):
        if kind == "domestic":
            return fetch_domestic(source, url)
        if kind == "page":
            return (fetch_html_source(source, url, lane), None)
        return (fetch_feed(source, url, lane), None)

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {pool.submit(run_job, source, url, lane, kind): (source, lane) for source, url, lane, kind in jobs}
        for future in as_completed(futures):
            source, lane = futures[future]
            try:
                items, note = future.result()
                candidates.extend(items)
                if note:
                    notes.append(note)
                if lane == "domestic":
                    domestic_success += 1
                elif lane == "federal":
                    federal_success += 1
                else:
                    europe_success += 1
            except Exception as exc:
                errors.append(f"{source}: {exc}")

    if domestic_success < 3:
        for error in errors:
            print(f"Feed error: {error}", file=sys.stderr)
        raise SystemExit(f"Only {domestic_success}/{len(DOMESTIC_FEEDS)} core Canadian sources were reachable; refusing to rewrite THE TICK")

    dedup: dict[str, Item] = {}
    for item in candidates:
        key = normalize_title(item.title)
        old = dedup.get(key)
        if old is None or (item.score, item.published) > (old.score, old.published):
            dedup[key] = item

    ranked = sorted(dedup.values(), key=lambda x: (x.score, x.published), reverse=True)
    federal_ranked = sorted(
        (item for item in dedup.values() if item.lane == "federal"),
        key=lambda x: x.published,
        reverse=True,
    )
    europe_ranked = [item for item in ranked if item.lane == "europe"]

    selected: list[tuple[str, str]] = []
    seen_titles: set[str] = set()
    seen_hrefs: set[str] = set()

    def add_item(item: Item) -> None:
        key = normalize_title(item.title)
        if key in seen_titles or item.link in seen_hrefs or len(selected) >= MAX_HEADLINES:
            return
        label = "FEDERAL" if item.lane == "federal" else topic_label(item.title)
        selected.append((item.link, f"{label} · {item.title} — {item.source}"))
        seen_titles.add(key)
        seen_hrefs.add(item.link)

    # Federal announcements get a guaranteed place in every refresh. The newest
    # official releases are chosen first so they cannot be pushed out by news scoring.
    for item in federal_ranked[:FEDERAL_SLOTS]:
        add_item(item)

    for item in europe_ranked[:EUROPE_SLOTS]:
        add_item(item)

    for item in ranked:
        add_item(item)

    if len(selected) < MAX_HEADLINES:
        for href, label in existing_unique_anchors(text):
            if href in seen_hrefs:
                continue
            key = normalize_title(label.split(" · ", 1)[-1].split(" — ", 1)[0])
            if key in seen_titles:
                continue
            selected.append((href, label))
            seen_hrefs.add(href)
            seen_titles.add(key)
            if len(selected) >= MAX_HEADLINES:
                break

    if not selected:
        raise SystemExit("No ticker items and no approved existing fallback; refusing to rewrite THE TICK")

    one_pass = "".join(build_anchor(href, label) for href, label in selected)
    track = '<div class="ticker-track"><!-- HOURLY_TICK_AUTO_BEGIN -->' + one_pass + one_pass + '<!-- HOURLY_TICK_AUTO_END --></div></div></div><div class="markets">'
    text, track_count = re.subn(r'<div class="ticker-track">.*?</div></div></div><div class="markets">', track, text, count=1, flags=re.S)
    if track_count != 1:
        raise SystemExit("Could not locate the protected THE TICK track in Canada/index.html")

    # Keep the public label clean. Refresh time belongs in logs, not in the masthead.
    text, label_count = re.subn(
        r'<span class="tick-label">THE TICK(?: · CHECKED [^<]+)?</span>',
        '<span class="tick-label">THE TICK</span>',
        text,
        count=1,
    )
    if label_count != 1:
        raise SystemExit("Could not locate THE TICK label in Canada/index.html")

    required = (
        "CANADA_AT_WAR_MASTHEAD_LOCK", "PINNED_LEAD_LOCK", "tradingview-widget-container",
        "canada-at-war-goose-eagle-v3.jpg", "petition-paint-mix", "How Lying Works",
        "HOURLY_TICK_AUTO_BEGIN", "HOURLY_TICK_AUTO_END",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise SystemExit("Ticker safety guard failed; missing: " + ", ".join(missing))

    PAGE.write_text(text, encoding="utf-8")
    checked = datetime.now(ET_ZONE).strftime("%H:%M ET")
    federal_selected = sum(1 for _, label in selected if "— Government of Canada" in label)
    europe_selected = sum(1 for _, label in selected if any(source in label for source in ("European Commission", "EU Council", "POLITICO Europe", "EEAS Canada")))
    print(
        f"THE TICK checked {checked}; Canadian sources {domestic_success}/{len(DOMESTIC_FEEDS)}; "
        f"federal feed {federal_success}/{len(FEDERAL_FEEDS)}; Europe sources "
        f"{europe_success}/{len(EUROPE_FEEDS)+len(EUROPE_PAGES)}; {len(selected)} headlines "
        f"selected ({federal_selected} federal, {europe_selected} Europe-lane)."
    )
    for href, label in selected:
        print(f"- {label} -> {href}")
    for note in notes:
        print(f"Source note: {note}")
    for error in errors:
        print(f"Source warning: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
