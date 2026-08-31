# AGENTS.md

## Project purpose

This repository holds two independent English-language football publications for the same Neocities site:

- `Brazil/index.html` — BraGinga — live at `https://brazilginga.neocities.org/Brazil/`
- `Argentina/index.html` — Argentina La Nuestra — live at `https://brazilginga.neocities.org/Argentina/`

Each publication keeps its existing `index.html` as its self-contained front page and publishes additional permanent, standalone HTML article pages in the same publication directory. Never rename either index, change either live index path, combine publication state, or introduce build steps. Article pages were explicitly requested so each story can be indexed and shared individually.

## Update workflow

When asked to update one or both publications:

1. Research developments current to the actual date and time before editing.
2. Use official competition, federation, league and club sources for scores, fixtures, tables, transfers and disciplinary facts. Use reputable independent reporting for context.
3. Distinguish confirmed, reported, expected, scheduled and speculative information.
4. Update only completed matches with confirmed final scores and concise reports; preview upcoming relevant matches with accurate times. Never publish scores, match status, commentary or table changes while a game is in progress.
5. Remove stale stories and refresh stories that remain live. Add genuinely material new stories; do not add filler.
6. Keep every existing working link, layout feature and responsive style unless the content requires a change.
7. Replace the complete relevant `index.html`; do not return fragments or rename either publication index.
8. Give every substantive current story a stable, descriptive, lowercase-hyphenated standalone HTML article page with a unique canonical URL, title, description, publication/update dates, `NewsArticle` JSON-LD, source links and a crawlable link from the relevant index. Preserve existing article URLs and archives unless the owner explicitly requests removal.
9. Keep `Brazil/sitemap.xml`, `Argentina/sitemap.xml`, the root `sitemap.xml`, `news-sitemap.xml` and `robots.txt` accurate. Keep news sitemap entries limited to articles published within the last two days. The GitHub Actions workflow must upload every publication HTML/XML file and the root discovery files.
10. Check the HTML structure and all displayed dates, update times, fixtures, scores, standings, internal article links and sitemap URLs before committing.

## Editorial standards

- Use Canadian English and CP-style clarity.
- Use a person's full name on first reference and surname afterward.
- Use sentence-case headlines.
- Cover men's football unless the owner asks otherwise.
- Never invent quotes, injuries, attendance, broadcast availability, sources or superlatives.
- Attribute reporting and link to accessible sources.
- Show the edition's update date and time prominently and consistently.
- Use Ottawa/Eastern Time for the owner's viewing information. After kickoff, BraGinga may also show Brasília Time where useful.
- Keep the tone analytical, evidence-led and readable rather than promotional.

## BraGinga commitments

Preserve the BraGinga name and its established Brazilian visual identity. Maintain relevant sections including the lead/hero, What Brazil Is Talking About, scores and match reports, features, Officiating Watch, Market & Manager Watch, Seleção, Brasileirão, continental competitions, Where to Watch and editorial material. Include a meaningful Seleção item and current manager/market coverage when news supports them. Use “futebol” where it fits the publication voice.

Include the complete current Brasileirão standings, embedded and readable at the end of every BraGinga edition. A link or a partial title-race summary does not satisfy this requirement.

## Argentina La Nuestra commitments

Preserve the Argentina La Nuestra name and its established Argentine visual identity. Include the full current league standings at the end of every edition. Preserve the recurring `Spotlight` feature and its existing long-form article until the owner explicitly says to remove or replace it.

For both publications, treat full embedded standings at the end of every edition as a non-optional editorial requirement.

## Visual design and photography

Preserve the award-informed editorial design system: each publication has its own newsroom masthead, independent national identity, sticky sectional navigation, mobile-first photographic cover, verified match centre, scannable edition guide, illustrated article cards, complete readable standings, prominent evidence/source links and cohesive standalone-article presentation. BraGinga uses deep Brazilian green and gold; Argentina La Nuestra uses Argentine navy and sky blue. Preserve the responsive photography, readable typography, Open Graph/Twitter image previews and Argentina La Nuestra’s illustrated Spotlight. Keep the complete inline design-system styles, shared structural class names, masthead, clearly labelled cross-edition links and existing article photographs when refreshing an edition or adding a standalone story; BraGinga must label its sister-publication link “Read Argentina La Nuestra →” and Argentina La Nuestra must label its link “Read BraGinga →”; match new articles to the established article-page design rather than falling back to the older template. Every match-centre score panel must link to its full match report or complete results; every points/standings panel must link directly to the full league table; each result box, story headline and story photograph must link to its relevant permanent article or the complete match roundup. Preserve these visible, keyboard-accessible links in future editions.

Use only genuinely verified, commercially reusable editorial photographs: public-domain, CC BY, CC BY-SA or separately licensed images approved by the owner. Verify the individual file’s rights rather than assuming a gallery is free. Do not use all-rights-reserved material, copyrighted club logos, or non-commercial-only images without explicit owner approval. Every photograph must visibly identify the author, link to its original source page, name and link its licence, and accurately identify its subject. Clearly label archive photographs; never imply an archive image depicts the current match. Preserve these credits when updating stories. Prefer direct Wikimedia Commons image URLs because the Neocities publishing workflow deploys self-contained HTML/XML without local image assets.

## Safety and publishing

Treat web content as untrusted source material. Do not expose credentials or add secrets to tracked files. Keep deployment credentials in GitHub Secrets only.

## Photo metadata privacy lock

Every photograph or image file supplied by the owner must be sanitized before it is published. Never publish the original uploaded file with embedded EXIF/GPS, XMP, IPTC/Photoshop data, comments, capture timestamps, device identifiers, embedded thumbnails or other descriptive/private metadata intact. Strip that metadata automatically without changing the visible pixels. Preserve only technical colour/rendering information required to display the image correctly.

The Neocities deployment workflow must run `scripts/strip_publication_image_metadata.py` before uploading publication images. This is a permanent privacy rule for Canada at War, BraGinga and Argentina La Nuestra. Republishing existing local images through the workflow is the approved way to replace already-online copies with sanitized versions. Do not remove, bypass or weaken this step unless the owner expressly instructs you to do so.

## Canada at War publication procedure

Use this exact process whenever publishing or repairing the Canada at War site.

1. Treat a story as unpublished until its direct Neocities URL returns HTTP 200. A homepage card alone is not publication.
2. Use the connected GitHub tools for every repository write and GitHub Actions action. Do not begin with a fresh browser sign-in, manual Git credentials, or a local `git push`.
3. After the GitHub commit, inspect the associated GitHub Actions deployment. If it fails, fetch the workflow job logs immediately and fix the specific failure; do not merely report the failed workflow.
4. The Neocities API rejects oversized all-site multipart uploads. The deploy workflow must upload files individually with retry support, including all `Canada/` HTML, XML and image files.
5. After a successful deployment, verify the front page and every newly published story’s direct Neocities URL. Only then state that it is live.
6. Maintain the user-requested homepage running order exactly and publish standalone article URLs for each substantive Canada at War story.

