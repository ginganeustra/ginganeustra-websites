#!/usr/bin/env python3
"""Run Canada at War's hourly ticker with a trade-war-only editorial gate.

This wrapper deliberately reuses the existing curated source/fetch machinery.
It does not broaden the source list. It only narrows what may be published.
"""
from __future__ import annotations

import re
import update_canada_tick as tick

TRADE_WAR_TERMS = (
    "tariff", "tariffs", "trade war", "trade talks", "trade negotiation",
    "trade negotiations", "trade deal", "trade agreement", "usmca", "cusma",
    "counter-tariff", "counter tariff", "retaliatory tariff", "retaliatory tariffs",
    "retaliation", "retaliatory", "customs duty", "customs duties", "import duty",
    "import duties", "export duty", "export duties", "section 232", "section 301",
    "trade rupture", "trade dispute", "trade conflict", "trade pressure",
)

# These can qualify only when the text also makes the U.S./Trump trade confrontation explicit.
TRADE_RESPONSE_TERMS = (
    "ceta", "market diversification", "diversify", "diversification", "supply chain",
    "export market", "exports", "investment shift", "reshoring", "friendshoring",
    "steel", "aluminum", "aluminium", "auto", "automaker", "vehicle", "dairy",
    "critical mineral", "critical minerals", "critical raw material", "critical raw materials",
)
US_CONFLICT_TERMS = (
    "trump", "united states", "u.s.", "washington", "american tariff", "u.s. tariff",
    "u.s. tariffs", "us tariff", "us tariffs", "51st state",
)


def is_trade_war_text(text: str) -> bool:
    t = f" {text.lower()} "
    if any(term in t for term in TRADE_WAR_TERMS):
        return True
    return any(term in t for term in TRADE_RESPONSE_TERMS) and any(term in t for term in US_CONFLICT_TERMS)


_original_score = tick.score_item
_original_existing = tick.existing_unique_anchors


def trade_score_item(title: str, summary: str, source: str, lane: str) -> int:
    combined = f"{title} {summary}"
    if not is_trade_war_text(combined):
        return -1
    score = _original_score(title, summary, source, lane)
    if score < 0:
        return -1
    # Reward direct tariff/trade-war language over adjacent economic responses.
    direct = sum(1 for term in TRADE_WAR_TERMS if term in combined.lower())
    return score + direct * 6


def trade_existing(text: str):
    # Never let the fallback mechanism preserve a stale non-trade-war headline.
    return [(href, label) for href, label in _original_existing(text) if is_trade_war_text(label)]


def trade_topic_label(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ("toyota", "honda", "automaker", "auto ", "vehicle")):
        return "AUTO TARIFF"
    if any(x in t for x in ("europe", "european union", "ceta", "eu ")):
        return "EUROPE TRADE"
    if any(x in t for x in ("china", "beijing")):
        return "CHINA TRADE"
    if any(x in t for x in ("steel", "aluminum", "aluminium")):
        return "METALS TARIFF"
    return "TRADE WAR"


tick.score_item = trade_score_item
tick.existing_unique_anchors = trade_existing
tick.topic_label = trade_topic_label

if __name__ == "__main__":
    raise SystemExit(tick.main())
