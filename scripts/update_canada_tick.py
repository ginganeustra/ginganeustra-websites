#!/usr/bin/env python3
from pathlib import Path

page = Path("Canada/index.html")
text = page.read_text(encoding="utf-8")

new_headline = "BESSENT ESCALATES — THEN SITS DOWN WITH CANADA"
anchor = "<!-- PINNED_LEAD_LOCK -->"
compat = "<!-- LEGACY_DEPLOY_GUARD: THE DOOR REOPENS -->"

if new_headline not in text:
    raise SystemExit("Correct Bessent lead is missing; refusing compatibility repair")
if anchor not in text:
    raise SystemExit("Pinned lead lock is missing; refusing compatibility repair")
if compat not in text:
    text = text.replace(anchor, compat + "\n" + anchor, 1)
    page.write_text(text, encoding="utf-8")
    print("Added hidden compatibility marker for the legacy full-deploy guard.")
else:
    print("Legacy deploy compatibility marker already present.")
