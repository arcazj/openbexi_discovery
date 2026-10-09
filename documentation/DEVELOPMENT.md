# Development and release 1.1

## Code map

- `index.html`: original evidence, guidance, and saved-brief workflows.
- `assets/discovery.js` and `.css`: Discovery UI; no CDN or Node runtime requirement.
- `backend/profiles.py`: schemas, taxonomy, revisions, workspace persistence.
- `backend/library.py`: activities/files, quizzes, safe ZIP processing.
- `backend/connections.py`: read-only SQLite; no free-form SQL endpoint.
- `backend/budget.py`: durable SQLite usage/reservations.
- `backend/prompting.py`, `prompts/runtime/`: versioned task instructions.
- `backend/discovery_api.py`: local Discovery routes.
- `templates/`: defaults and pricing; `schemas/`: generated schema references.

## Contracts

Run one server worker. JSON writes use atomic replacement; profile/workspace saves require matching revisions. Bundled defaults never overwrite edited profiles. Previous revisions support undo. Fields include schema version, ID/revision, themes, level, UI copy, tabs/panels/tools, and per-block provenance. Stable level values: `beginner`, `intermediate`, `advanced`, `expert`, `researcher`, `frontier`, `beyond_frontier`.

Taxonomy IDs come from linked files under `themes/world_research_taxonomy`. Historical profile snapshots retain context; active profiles validate against current taxonomy. A broad general profile can omit specific themes.

Activities retain profile snapshots, timestamps, requests/prompts, content, attachments, and provenance. Library indexes are derived from records. ZIP manifest `1.1` lists relative files, byte sizes, and SHA-256 checksums. Import stages files before a directory rename, remaps conflicting activity references, never executes embedded content, and never overwrites active profiles. Export excludes `exports/` itself and sensitive content without selection.

The independent usage ledger uses `BEGIN IMMEDIATE` reservations. Unknown final usage remains reserved. Profiles/AI/imports cannot reset budgets.

SQLite uses URI read-only mode, `query_only`, untrusted schema, real tables, named columns, parameterized equality filters, pagination, and a two-second deadline. Server paths are excluded from public connection metadata. Uploaded copies are limited to 8 MB.

## Extend

Add categories through the linked taxonomy. Change UI schemas and rendering together. Register tools as available only when implemented/tested. Add runtime tasks with a template manifest entry, structured output schema, and the same data-use and budget gates. Provider/account connectors need their own authorization workflow; none are claimed beyond SQLite in 1.1.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm test
npm run test:ui
npm run test:discovery
```

Discovery browser checks start an isolated backend and make no paid AI calls. Use synthetic fixtures for sensitive-data tests. See [Windows packaging](../WINDOWS_INSTALLATION.md) for installer/build checks.

The bundle includes frontend assets, templates, taxonomy, runtime prompts, schemas, documentation, and Python SQLite support. User profiles, libraries, private settings, keys, and Git files are excluded. Internal Windows executable/data-directory identifiers retain `REIResearchExplorer` for upgrade compatibility; the displayed product and installer are OpenBEXI Discovery.

Publish to `arcazj/openbexi_discovery`; retain `arcazj/openbexi_REI` as the legacy backup.


Profile and full-library ZIP exports include the current profile configuration and workspace, even for an empty profile. After importing, open a historical item and choose **Restore as a new profile** to create an inactive copy; a workspace backup also restores its saved briefs and preferences. Select the new copy in Profile settings. Live connections must be configured again. Sensitive workspace backups are excluded unless explicitly included.
