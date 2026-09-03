# Canada at War Publishing Protocol v2

**Status: mandatory. This file is the source of truth for routine Canada at War publishing.**

## Trigger

This protocol is triggered by any instruction to **post, publish, put live, add, update, replace, promote, demote, repair, or make a story the lead** on Canada at War. The trigger applies even if the user does not mention this file.

Before the first repository write in a triggered task, the publishing agent must:

1. Read this file from `main`.
2. Inspect the current `Canada/index.html` and the most recent successful comparable Canada at War article/lead.
3. Use `scripts/publish_canada_story.py` and the canonical templates for routine stories whenever a checked-out repository is available. If operating through a repository connector that cannot execute the script, reproduce the script's exact output and do not invent another structure.
4. Make the smallest possible change set.

**Routine publishing is not a design task. Do not invent a new publication method.**

## Canonical routine path

For a normal story publication the permitted path is:

`story + metadata + approved image -> canonical publisher/templates -> preflight -> commit main -> existing GitHub Actions deploy -> live verification -> completion`

A routine story should normally touch only:

- the new or intentionally updated `Canada/<slug>.html` article;
- its approved `Canada/assets/<image>.jpg` or `.png` asset;
- the lead/story-feed portion of `Canada/index.html` if the homepage is changing;
- `Canada/sitemap.xml` and relevant discovery files when required;
- the publisher receipt/manifest if the canonical publisher writes one.

Do not rewrite the masthead, navigation, THE TICK, market tape, petition feature, Must Read Library, footer, global CSS, deployment workflow, or unrelated stories during a routine publication.

## Last-known-good rule

The last successful comparable publication is the implementation template. When something differs unexpectedly, compare the failing publication with the last known-good one before changing technique.

If the known-good path fails:

1. identify the exact difference;
2. repair that difference with the smallest change possible;
3. run preflight again;
4. deploy again;
5. add a validator/test for a genuinely new failure mode.

Do not switch formats, wrappers, page architectures, deployment routes, or image techniques merely because an upload failed.

## Article template

New routine articles use `Canada/templates/article.html`.

Required fields:

- stable lowercase-hyphenated slug;
- title/headline;
- description/deck;
- kicker/section label;
- publication timestamp in Eastern Time;
- canonical URL;
- article body;
- source links;
- approved image and accurate alt text when art is used.

Do not rebuild article CSS from scratch for each story.

## Homepage lead

The homepage lead is a protected slot. Replacing it requires explicit editorial authorization. The canonical publisher requires `replace_lead_authorized: true`; absence of that flag means the existing lead stays where it is.

When a lead is replaced, the previous lead must be preserved in the story feed unless the editor explicitly says otherwise.

The rest of `Canada/index.html` is treated as protected state. A routine lead change must not reconstruct the homepage.

## Image rule

For normal Canada at War story art:

- use a direct `.jpg`, `.jpeg`, or `.png` file in `Canada/assets/`;
- reference that file directly from HTML;
- never wrap a JPEG/PNG inside SVG;
- never use `data:image/...` in story HTML;
- never change format simply to work around a publishing failure;
- sanitize owner-supplied images through the permanent metadata-stripping step before upload;
- verify the file signature and dimensions before deployment;
- verify the public image bytes after deployment.

SVG remains permitted for genuine vector artwork already designed as SVG, but a routine photographic/editorial raster image must not be converted into an SVG wrapper.

## Preflight gate

`scripts/validate_canada_publish.py` and `scripts/validate_canada_discovery.py` are mandatory preflight gates. The deployment runs both before files are uploaded.

At minimum it verifies:

- protected Canada at War shell markers still exist;
- exactly one lead story is detectable;
- the lead article file exists;
- the homepage headline and article headline agree;
- the homepage and article point at the same lead image;
- the lead image is a direct JPG/PNG, not an SVG or data URI;
- the image file exists and has a valid binary signature/dimensions;
- required ticker, market, petition, library and masthead elements remain present;
- the current lead article contains its canonical URL and publication metadata.

If preflight fails, deployment stops. Do not bypass or weaken the gate to get a story online.

## Archive and discovery integrity

A homepage story is not publishable until its archive and discovery records agree with the article.

For every story on the current Canada homepage, the following must be true before deployment:

- `Canada/archive.html` contains one searchable card with the current headline and dek;
- `Canada/sitemap.xml` contains the article URL;
- root `sitemap.xml` contains the article URL;
- root `news-sitemap.xml` contains the article URL when the article is within the two-day Google News window;
- the homepage `<title>` date matches its visible `UPDATED` date.

The canonical publisher calls `scripts/sync_canada_discovery.py` for each story it writes. For a repair or backfill, synchronize every current homepage story with:

```bash
python3 scripts/sync_canada_discovery.py --from-homepage
```

Run `python3 scripts/validate_canada_discovery.py` before any deployment. The workflow runs this validator as a fail-closed gate, so uploading a story with stale archive or sitemap data is a deployment failure, not a post-publication cleanup task.

## Deployment gate

The production route remains:

1. write/commit through the connected GitHub repository;
2. push/update `main`;
3. let `Publish to Neocities` upload the files individually with retry support;
4. inspect the workflow run;
5. if it fails, read the failing job logs and repair the specific cause.

Do not substitute manual Neocities editing, a different repository, a different branch, a fresh browser login, or a separate ad-hoc upload path for routine publication.

## Deployment race gate

A one-shot workflow that directly uploads and verifies files can still be followed by an older `Publish to Neocities` run that checked out the pre-final source state. If that older run finishes later, it can overwrite the newly verified public pages with stale content.

Therefore:

- inspect all `Publish to Neocities` runs triggered by the staging/workflow commit and the final source commit;
- do not treat a one-shot live check as final while an older deployment based on pre-final source is queued or running;
- after the last competing deployment has settled, redeploy the current final `main` state if necessary;
- perform a fresh cache-busted public verification after that final deployment;
- only the post-race verification counts as acceptance.

This failure was observed on September 2, 2026: the AI-copyright/tariff-grants one-shot verified the correct public files, but a concurrently triggered normal deploy from the preceding workflow-file commit completed afterward and restored the older public state.

## Live acceptance gate

A GitHub Actions green check is not sufficient by itself.

`scripts/verify_canada_live.py` dynamically reads the current lead and checks the live site. It verifies:

- the Canada at War homepage returns HTTP 200 and contains the expected current headline and image reference;
- the direct article URL returns HTTP 200 and contains the same headline and image reference;
- the public image URL returns HTTP 200 with an image content type;
- the public image is a valid JPG/PNG;
- its dimensions match the local upload candidate;
- its SHA-256 bytes match the sanitized local file.

Only after the workflow and this live acceptance gate succeed may the publishing agent say **live**, **published**, **fixed**, or **done**.

## Completion language

Never report success based on any of these alone:

- a GitHub commit existing;
- the article HTML existing in the repository;
- the GitHub Actions workflow starting;
- the upload API returning success for some files;
- the homepage returning HTTP 200;
- visual assumptions based only on source HTML.

Completion requires successful deployment plus the live acceptance checks above.

## Failure learning

When a genuinely new production failure is solved, update this protocol and/or validator so the same failure is automatically detected next time. Prefer adding a deterministic check over adding another paragraph asking a future agent to remember something.

Archive/sitemap drift is covered by `scripts/validate_canada_discovery.py`; do not waive it. Repair the source records, rerun the synchronizer, then deploy.

## Current known lesson: CBC elephant art

The September 1, 2026 CBC/RNC publication exposed the failure mode this protocol is intended to prevent: a routine raster image was wrapped in SVG, the workflow could succeed while the public browser still showed broken art, and success was reported too early. The permanent rule is direct raster assets plus binary/live validation. Do not repeat the SVG-wrapper approach for routine story art.

## Definition of done

A Canada at War story is done only when all of the following are true:

- editorial copy is complete;
- canonical article URL exists;
- homepage placement matches the editor's instruction;
- archive card, Canada sitemap, root sitemap and eligible news-sitemap records are current;
- homepage title date matches the visible update date;
- image is valid and correctly referenced;
- both publishing and discovery preflight checks pass;
- GitHub commit is on `main`;
- Neocities deployment completes successfully;
- homepage, article and image pass live verification.
