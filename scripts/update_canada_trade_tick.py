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

# These are ordinary politics even when a headline uses the trade war as scenery.
# They are excluded unless the title itself also contains a concrete trade-policy action.
POLITICAL_CONTEXT_TERMS = (
    "byelection", "by-election", "election", "poll", "polling", "vote", "voting",
    "campaign", "candidate", "riding", "approval rating", "seat projection",
)
CONCRETE_TRADE_ACTION_TERMS = (
    "tariff", "tariffs", "trade talks", "trade negotiation", "trade negotiations",
    "trade deal", "trade agreement", "usmca", "cusma", "counter-tariff", "counter tariff",
    "retaliatory tariff", "retaliatory tariffs", "customs duty", "import duty", "section 232",
    "section 301",
)


def is_trade_war_text(text: str) -> bool:
    t = f" {text.lower()} "
    if any(term in t for term in TRADE_WAR_TERMS):
        return True
    return any(term in t for term in TRADE_RESPONSE_TERMS) and any(term in t for term in US_CONFLICT_TERMS)


def is_incidental_politics(title: str) -> bool:
    t = f" {title.lower()} "
    if not any(term in t for term in POLITICAL_CONTEXT_TERMS):
        return False
    return not any(term in t for term in CONCRETE_TRADE_ACTION_TERMS)


_original_score = tick.score_item
_original_existing = tick.existing_unique_anchors


def trade_score_item(title: str, summary: str, source: str, lane: str) -> int:
    if is_incidental_politics(title):
        return -1
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
    # Never let the fallback preserve stale, incidental or non-trade-war headlines.
    kept = []
    for href, label in _original_existing(text):
        headline = label.split(" · ", 1)[-1].split(" — ", 1)[0]
        if is_trade_war_text(label) and not is_incidental_politics(headline):
            kept.append((href, label))
    return kept


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


def enforce_clean_public_tick_label() -> None:
    """Never publish a clock time in THE TICK label.

    The actual refresh time stays in workflow logs. The reader-facing masthead
    simply says THE TICK, avoiding a false impression of minute-by-minute news.
    """
    text = tick.PAGE.read_text(encoding="utf-8")
    text, count = re.subn(
        r'<span class="tick-label">THE TICK(?: · CHECKED [^<]+)?</span>',
        '<span class="tick-label">THE TICK</span>',
        text,
        count=1,
    )
    if count != 1:
        raise SystemExit("Could not enforce clean THE TICK public label")
    tick.PAGE.write_text(text, encoding="utf-8")


# The general federal-news lane hard-codes a FEDERAL label and guarantees slots,
# which is incompatible with a trade-war-only ticker. Global Affairs Canada is
# already in the curated domestic sources, so trade-specific official news can
# still qualify without opening the door to unrelated federal announcements.
tick.FEDERAL_FEEDS = ()
tick.FEDERAL_SLOTS = 0

tick.score_item = trade_score_item
tick.existing_unique_anchors = trade_existing
tick.topic_label = trade_topic_label

if __name__ == "__main__":
    result = tick.main()
    if result:
        raise SystemExit(result)
    enforce_clean_public_tick_label()
    raise SystemExit(0)
