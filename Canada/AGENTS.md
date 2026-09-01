# Canada at War agent instructions

Any request to **post, publish, put live, add, update, replace, promote, demote, repair, or make a story the lead** on Canada at War automatically triggers `PUBLISHING_PROTOCOL.md`.

Before the first repository write, read `Canada/PUBLISHING_PROTOCOL.md` from the current `main` branch and inspect the current homepage plus the last successful comparable story.

For routine stories, use `scripts/publish_canada_story.py` with `Canada/templates/`. If the connected repository interface cannot execute the script, reproduce the canonical publisher's structure exactly; do not invent an alternative page or image method.

Non-negotiable rules:

- Routine story art is a direct JPG/JPEG/PNG in `Canada/assets/`; no raster-in-SVG wrappers and no `data:image` story art.
- Replacing the homepage lead requires explicit editorial authorization.
- Do not reconstruct or redesign the homepage during a routine publication.
- Do not touch THE TICK, market tape, masthead, petition feature, Must Read Library, global shell or unrelated stories unless the editor specifically requests that change.
- Let the normal `main` -> GitHub Actions -> Neocities route deploy the story.
- A commit or green upload is not completion. Do not say live/published/fixed/done until the production workflow reaches `CANADA PUBLICATION VERIFIED: homepage + article + image` or equivalent live acceptance checks have independently passed.
- On failure, compare against the last known-good publication first. Add a deterministic validator for new failure modes rather than inventing a new routine.
