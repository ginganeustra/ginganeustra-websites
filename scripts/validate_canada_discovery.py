#!/usr/bin/env python3
"""Fail closed when current Canada at War stories are not discoverable."""
from __future__ import annotations

from datetime import datetime
import re

from sync_canada_discovery import (
    ARCHIVE,
    BASE_URL,
    HOME,
    NEWS_SITEMAP,
    ROOT_SITEMAP,
    SECTION_SITEMAP,
    TORONTO,
    archive_headline,
    compact,
    homepage_articles,
    in_news_window,
    read_article,
)


def die(message: str) -> None:
    raise SystemExit(f"CANADA DISCOVERY PREFLIGHT FAILED: {message}")


def homepage_updated_date(home: str) -> datetime:
    marker = re.search(
        r"UPDATED\s*[·•]\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})",
        compact(home),
        re.I,
    )
    if not marker:
        die("homepage updated-date banner is missing")
    month = marker.group(1).lower().rstrip(".")
    if month == "sept":
        month = "sep"
    try:
        month_no = datetime.strptime(month[:3], "%b").month
    except ValueError:
        die(f"could not parse homepage update month: {marker.group(1)}")
    return datetime(int(marker.group(3)), month_no, int(marker.group(2)), tzinfo=TORONTO)


def main() -> int:
    home = HOME.read_text(encoding="utf-8")
    reference = homepage_updated_date(home)
    expected_title = f"Canada at War — {reference.strftime('%B')} {reference.day}, {reference.year}"
    if f"<title>{expected_title}</title>" not in home:
        die(f"homepage title must be {expected_title!r}")

    archive = ARCHIVE.read_text(encoding="utf-8")
    section = SECTION_SITEMAP.read_text(encoding="utf-8")
    root = ROOT_SITEMAP.read_text(encoding="utf-8")
    news = NEWS_SITEMAP.read_text(encoding="utf-8")
    articles = [read_article(href) for href in homepage_articles()]
    if not articles:
        die("no current homepage article links were detected")

    failures: list[str] = []
    for article in articles:
        if f'href="{article.href}"' not in archive:
            failures.append(f"archive missing {article.href}")
        elif archive_headline(archive, article.href) != article.headline:
            failures.append(f"archive headline stale for {article.href}")
        url = BASE_URL + article.href
        if url not in section:
            failures.append(f"Canada sitemap missing {article.href}")
        if url not in root:
            failures.append(f"root sitemap missing {article.href}")
        if in_news_window(article, reference) and url not in news:
            failures.append(f"news sitemap missing recent {article.href}")
    if failures:
        die("; ".join(failures))
    print(f"CANADA DISCOVERY PREFLIGHT PASSED: {len(articles)} current homepage articles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
