#!/usr/bin/env python3
from pathlib import Path

page = Path("Canada/index.html")
text = page.read_text(encoding="utf-8")

old_top = '<div class="top">UPDATED · AUGUST 31, 2026 · 2:00 P.M. ET</div>'
new_top = '<div class="top">UPDATED · AUGUST 31, 2026 · 4:28 P.M. ET</div>'
old_hero = '''<section class="hero"><div class="hero-in"><div class="k">U.S. lead · Canada–U.S. trade · First contact since collapse</div><h1>THE DOOR REOPENS</h1><p>Scott Bessent says he will meet François-Philippe Champagne in Asheville — the first publicly announced cabinet-level Canada–U.S. contact since the trade talks collapsed Aug. 22. Bessent paired the opening with a new attack on Mark Carney, saying the United States is “not at war with Canada” and accusing the prime minister of turning the dispute into a political shouting match.</p><a class="read" href="bessent-champagne-first-contact-trade-collapse-august-31-2026.html">Read the U.S. lead →</a><p class="meta">Published Aug. 31, 2026 · 2:00 p.m. ET</p></div></section>'''
new_hero = '''<section class="hero"><div class="hero-in"><div class="k">Lead · Canada–U.S. trade · G20 Asheville · Developing</div><h1>BESSENT ESCALATES — THEN SITS DOWN WITH CANADA</h1><p>Hours before an expected face-to-face meeting with François-Philippe Champagne, U.S. Treasury Secretary Scott Bessent mocked Canada’s ability to retaliate, blamed Mark Carney for a “political shouting match” and claimed Ottawa walked away from “the best trade deal of any country on the globe.” The G20 now becomes the first test of whether the rhetoric is theatre — or the beginning of a harder American line.</p><a class="read" href="bessent-champagne-first-contact-trade-collapse-august-31-2026.html">Read the developing lead →</a><p class="meta">Updated Aug. 31, 2026 · 3:53 p.m. ET</p></div></section>'''

if old_top not in text:
    raise SystemExit("Expected stale 2:00 p.m. homepage timestamp was not found; refusing broad rewrite")
if old_hero not in text:
    raise SystemExit("Expected stale THE DOOR REOPENS hero was not found; refusing broad rewrite")

text = text.replace(old_top, new_top, 1)
text = text.replace(old_hero, new_hero, 1)
page.write_text(text, encoding="utf-8")
print("Patched only the Canada homepage timestamp and stale lead block.")
