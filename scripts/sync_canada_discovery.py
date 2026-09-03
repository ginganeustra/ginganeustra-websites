#!/usr/bin/env python3
"""Synchronize Canada at War's archive and discovery records.

Run this after a Canada article has been written and before deployment:

    python3 scripts/sync_canada_discovery.py Canada/example-story.html

The script deliberately updates only the specified article records (or the
current homepage article set with --from-homepage). It preserves historical
archive cards while replacing a card when the current article's headline has
changed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import html
from pathlib import Path
import re
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CANADA = ROOT / "Canada"
HOME = CANADA / "index.html"
ARCHIVE = CANADA / "archive.html"
SECTION_SITEMAP = CANADA / "sitemap.xml"
ROOT_SITEMAP = ROOT / "sitemap.xml"
NEWS_SITEMAP = ROOT / "news-sitemap.xml"
BASE_URL = "https://brazilginga.neocities.org/Canada/"
TORONTO = ZoneInfo("America/Toronto")
IGNORED_HOME_PAGES = {
    "archive.html",
    "about.html",
    "must-reads-from-other-sources.html",
    "how-lying-works-library.html",
}


def die(message: str) -> None:
    raise SystemExit(f"CANADA DISCOVERY SYNC FAILED: {message}")


def plain(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "").replace("\xa0", " "))


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", plain(value)).strip()


def xml(value: str) -> str:
    return html.escape(value, quote=True).replace("&#x27;", "&apos;")


def match_one(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    if not match:
        die(f"could not find {label}")
    return match.group(1)


@dataclass(frozen=True)
class Article:
    href: str
    path: Path
    headline: str
    title: str
    description: str
    published: datetime | None
    search_text: str


def parse_published(text: str) -> datetime | None:
    content = compact(text)
    match = re.search(
        r"(?:Published|Updated)\s+([A-Za-z]+)\.?\s+(\d{1,2}),\s*(\d{4})"
        r"(?:\s*[·•]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?)?",
        content,
        re.I,
    )
    if not match:
        return None
    month = match.group(1).lower().rstrip(".")
    aliases = {"sept": "sep"}
    month = aliases.get(month, month)
    try:
        month_no = datetime.strptime(month[:3], "%b").month
    except ValueError:
        return None
    hour = int(match.group(4) or 12)
    minute = int(match.group(5) or 0)
    half = (match.group(6) or "p").lower()
    if half == "p" and hour != 12:
        hour += 12
    if half == "a" and hour == 12:
        hour = 0
    return datetime(int(match.group(3)), month_no, int(match.group(2)), hour, minute, tzinfo=TORONTO)


def read_article(href: str) -> Article:
    if href.startswith(("http://", "https://", "//", "data:")):
        die(f"article href must be a local Canada path: {href}")
    rel = Path(href)
    if rel.is_absolute() or ".." in rel.parts or rel.suffix.lower() != ".html":
        die(f"unsafe or non-HTML article href: {href}")
    path = (CANADA / rel).resolve()
    try:
        path.relative_to(CANADA.resolve())
    except ValueError:
        die(f"article path escapes Canada: {href}")
    if not path.exists():
        die(f"missing article file: Canada/{href}")

    text = path.read_text(encoding="utf-8")
    canonical = BASE_URL + href
    if canonical not in text:
        die(f"article canonical URL does not match its file name: Canada/{href}")
    headline = compact(match_one(r"<h1[^>]*>(.*?)</h1>", text, f"H1 in Canada/{href}"))
    title = compact(match_one(r"<title>(.*?)</title>", text, f"title in Canada/{href}"))
    title = re.sub(r"\s+[—–-]\s+Canada at War$", "", title, flags=re.I).strip()
    description_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', text, re.I)
    if description_match:
        description = compact(description_match.group(1))
    else:
        description = compact(match_one(r'<p\s+class=["\']dek["\']>(.*?)</p>', text, f"deck in Canada/{href}"))
    meta_match = re.search(r'<p\s+class=["\']meta["\']>(.*?)</p>', text, re.I | re.S)
    published = parse_published(meta_match.group(1) if meta_match else text)
    return Article(href, path, headline, title or headline, description, published, compact(text))


def homepage_articles() -> list[str]:
    text = HOME.read_text(encoding="utf-8")
    hrefs = re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+\.html)["\']', text, re.I)
    result: list[str] = []
    for href in hrefs:
        if href in IGNORED_HOME_PAGES or href.startswith(("http://", "https://", "//")):
            continue
        if href not in result:
            result.append(href)
    return result


def archive_card(article: Article) -> str:
    when = article.published or datetime.now(TORONTO)
    date_label = f"{when.strftime('%B')} {when.day}, {when.year}"
    return (
        '<article class="archive-card"><div class="archive-meta">Current page · '
        + xml(date_label)
        + '</div><h2><a href="'
        + xml(article.href)
        + '">'
        + xml(article.headline)
        + "</a></h2><p>"
        + xml(article.description)
        + '</p><span class="search-text" hidden>'
        + xml(article.search_text)
        + "</span></article>"
    )


def archive_card_range(text: str, href: str) -> tuple[int, int] | None:
    anchor = text.find(f'href="{href}"')
    if anchor < 0:
        return None
    start = text.rfind('<article class="archive-card">', 0, anchor)
    end = text.find("</article>", anchor)
    if start < 0 or end < 0:
        die(f"could not isolate archive card for {href}")
    return start, end + len("</article>")


def archive_headline(text: str, href: str) -> str | None:
    card_range = archive_card_range(text, href)
    if not card_range:
        return None
    card = text[card_range[0]:card_range[1]]
    match = re.search(r"<h2>.*?<a\b[^>]*>(.*?)</a>.*?</h2>", card, re.I | re.S)
    return compact(match.group(1)) if match else None


def sync_archive(articles: list[Article]) -> None:
    text = ARCHIVE.read_text(encoding="utf-8")
    refresh = [article for article in articles if archive_headline(text, article.href) != article.headline]
    for article in refresh:
        card_range = archive_card_range(text, article.href)
        if card_range:
            text = text[:card_range[0]] + text[card_range[1]:]
    if not refresh:
        return
    marker = '<section id="archive-results">'
    if marker not in text:
        die("archive results marker is missing")
    text = text.replace(marker, marker + "".join(archive_card(article) for article in refresh), 1)
    total = text.count('<article class="archive-card">')
    text, count = re.subn(
        r'<div id="result-count">\d+ archive entries</div>',
        f'<div id="result-count">{total} archive entries</div>',
        text,
        count=1,
    )
    if count != 1:
        die("archive count marker is missing")
    newest = max((article.published for article in articles if article.published), default=datetime.now(TORONTO))
    updated = f"SEARCHABLE ARCHIVE · UPDATED {newest.strftime('%B').upper()} {newest.day}, {newest.year} · {newest.strftime('%-I:%M %p')} ET"
    text, count = re.subn(r'<div class="top">SEARCHABLE ARCHIVE · UPDATED .*?</div>', f'<div class="top">{updated}</div>', text, count=1, flags=re.S)
    if count != 1:
        die("archive update banner is missing")
    ARCHIVE.write_text(text, encoding="utf-8")


def lastmod(article: Article) -> str:
    when = article.published or datetime.now(TORONTO)
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def insert_url_entry(path: Path, article: Article) -> None:
    text = path.read_text(encoding="utf-8")
    url = BASE_URL + article.href
    if url in text:
        return
    entry = f"  <url><loc>{xml(url)}</loc><lastmod>{lastmod(article)}</lastmod></url>\n"
    if "</urlset>" not in text:
        die(f"{path.relative_to(ROOT)} has no urlset close marker")
    path.write_text(text.replace("</urlset>", entry + "</urlset>", 1), encoding="utf-8")


def replace_lastmod(path: Path, url: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = rf"(<url><loc>{re.escape(url)}</loc><lastmod>)[^<]+(</lastmod></url>)"
    updated, count = re.subn(pattern, rf"\g<1>{value}\g<2>", text, count=1)
    if count:
        path.write_text(updated, encoding="utf-8")


def in_news_window(article: Article, reference: datetime) -> bool:
    return article.published is not None and article.published.date() >= (reference.date() - timedelta(days=2))


def news_entry(article: Article) -> str:
    assert article.published is not None
    stamp = article.published.isoformat(timespec="seconds")
    return (
        "  <url><loc>"
        + xml(BASE_URL + article.href)
        + "</loc><news:news><news:publication><news:name>Canada at War</news:name><news:language>en</news:language></news:publication><news:publication_date>"
        + stamp
        + "</news:publication_date><news:title>"
        + xml(article.title)
        + "</news:title></news:news></url>\n"
    )


def sync_news(articles: list[Article], reference: datetime) -> None:
    text = NEWS_SITEMAP.read_text(encoding="utf-8")
    additions = [article for article in articles if in_news_window(article, reference) and BASE_URL + article.href not in text]
    if not additions:
        return
    for article in additions:
        text = text.replace("</urlset>", news_entry(article) + "</urlset>", 1)
    NEWS_SITEMAP.write_text(text, encoding="utf-8")


def update_home_title(reference: datetime) -> None:
    text = HOME.read_text(encoding="utf-8")
    expected = f"Canada at War — {reference.strftime('%B')} {reference.day}, {reference.year}"
    updated, count = re.subn(r"<title>Canada at War\s+[—–-]\s*[^<]+</title>", f"<title>{expected}</title>", text, count=1)
    if count != 1:
        die("homepage Canada at War title is missing")
    HOME.write_text(updated, encoding="utf-8")


def sync(articles: list[Article]) -> None:
    if not articles:
        die("no article records were supplied")
    reference = max((article.published for article in articles if article.published), default=datetime.now(TORONTO))
    sync_archive(articles)
    for article in articles:
        insert_url_entry(SECTION_SITEMAP, article)
        insert_url_entry(ROOT_SITEMAP, article)
    replace_lastmod(SECTION_SITEMAP, BASE_URL, lastmod(Article("", HOME, "", "", "", reference, "")))
    replace_lastmod(ROOT_SITEMAP, BASE_URL, lastmod(Article("", HOME, "", "", "", reference, "")))
    replace_lastmod(SECTION_SITEMAP, BASE_URL + "archive.html", lastmod(Article("", ARCHIVE, "", "", "", reference, "")))
    replace_lastmod(ROOT_SITEMAP, BASE_URL + "archive.html", lastmod(Article("", ARCHIVE, "", "", "", reference, "")))
    sync_news(articles, reference)
    update_home_title(reference)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("articles", nargs="*", help="Canada-relative article paths, such as story.html")
    parser.add_argument("--from-homepage", action="store_true", help="synchronize all current homepage articles")
    args = parser.parse_args()
    if args.from_homepage and args.articles:
        die("use article paths or --from-homepage, not both")
    hrefs = homepage_articles() if args.from_homepage else args.articles
    if not hrefs:
        die("supply at least one article path or use --from-homepage")
    sync([read_article(href.removeprefix("Canada/")) for href in hrefs])
    print("CANADA DISCOVERY SYNC PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
