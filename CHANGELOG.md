# Releases


## 1.1.1 — Compact layout and profile settings

- Makes the active profile button open the same Settings panel as the settings gear.
- Keeps the brand on the left and AI status, AI settings, Settings, and Help aligned on the right; shows the version in small text after the brand.
- Moves Saved research and Local library into Settings, with search as the default view.
- Places the compact introduction inline with a smaller description that wraps naturally.
- Removes the extra heading above the initial evidence welcome card, retaining search status and result headings.
- Refreshes the v1.1.1 live demo, documentation, Windows installer, source archives, release notes, and checksums with the latest UI.
- Reduces the heading and source bar height, keeping full profile details available on hover.
- Uses golden-ratio desktop columns, consistent spacing, and softer panel backgrounds, with responsive mobile layouts.
- Corrects the IntelliJ module and interpreter configuration.
- Consolidates repository links and Windows upgrade checks in OpenBEXI Discovery.
- Provides source ZIP and tar.gz downloads, standalone release notes, and checksums, with updated guides and a versioned live-demo link.
- Aligns profile templates, wording controls, previews, and AI draft guidance with the compact workspace; preserves custom wording and adapts the original REI introduction.
- Preserves existing profile schemas, saved work, and installed application data locations.

## 1.1.0 — OpenBEXI Discovery

- Preserves the REI evidence workflow at Advanced as the default profile.
- Adds editable JSON profiles, searchable research themes, seven learning levels, and profile-specific workspaces.
- Adds documents, datasets, notes, locally graded quizzes, read-only SQLite connections, and offline ZIP export/read/import.
- Adds versioned AI prompts, reviewed profile drafts, persistent token/cost budgets, and source/AI provenance colors.
- Bundles Python, SQLite, themes, prompts, schemas, and guides in the Windows installer; preserves legacy private data locations.
- Publishes as `openbexi_discovery` with the original REI Git history.

Optional tutors, 3D simulations, research agents, and account-provider connectors remain planned. Live public evidence sources remain PubMed, Ensembl, and GWAS Catalog. No paid AI requests are used in automated verification.

## V1.0.1 — 2026-10-04

- Search, More actions, and Suggest research directions share a compact row; the toolbar stays visible below sources while scrolling.
- Stronger silver gradients and graphite edges throughout the workspace. Sources have a distinct metallic frame, clearer selected colors, concise desktop descriptions, and a visible mobile heading.
- Tip text in a rounded card matching research guidance; a stronger silver-blue background separates Source evidence from its records.
- Consistent source palettes in selectors, coverage, evidence cards, and detail badges: green PubMed, blue Ensembl, and lavender GWAS Catalog.
- V1.0.1 after AI settings; application metadata, exports, and the bundled Windows installer use version 1.0.1. Existing saved research remains compatible.
- Explore presets sit on the right of Human / Auto-detect; presets and Auto-detect share grey metallic styling. Recent stays outside the search panel, with Recent: directly below Explore:. The taller query input has a thin green line that thickens on hover/focus without shifting the layout. Suggest research directions and verified AI status share an orange-grey palette with dark readable text.
- AI-generated guidance, tips, explanations, and proposed questions use a softer orange-grey surface, including AI-assisted brief editing, saved briefs, and comparisons. Saved AI-assisted briefs have an explicit label; the introduction explains that orange backgrounds indicate AI suggestions.
- The Windows workflow verifies fresh installation and upgrading the published V1.0 installer, including settings preservation and current UI/version checks.

## Windows installer for V1.0

- Self-contained x64 Windows 10/11 installer with bundled Python/runtime dependencies, per-user installation, Start menu/desktop shortcuts, and uninstall registration.
- Browser launch and native tray Open/Quit controls; singleton instance, remembered port, and loopback-only server.
- Credentials in a separate private user folder. Updates and uninstall preserve private settings, browser research, and added user files.
- Automated Windows build and actual install/runtime/update/uninstall checks; public packages omit local keys, workspace data, and IDE files.

## V1.0 — 2026-10-04

- Compact silver, sage, blue, and lavender UI; one AI status in the header and AI settings on the right.
- Verified connection reads “AI connected to GPT-6.1 Sol · key verified.” Mobile shows a short label with full details on tap.
- Selectable sources above search remain visible while scrolling. Search is the primary action before results; Suggest research directions follows a completed search. Draft and export are under More actions.
- Source-grounded GPT-6.1 Sol guidance after completed live searches: one next step and one tip, with supporting evidence available through Why this suggestion?
- Apply a refined query, review and save a proposed question, or add the next step to a brief. Saved AI material preserves evidence, model, prompt version, and date.
- Context-based session caching, manual refresh, automatic-guidance setting, cancellation, stale-response protection, and labeled fallbacks. Saved research survives AI failures.
- GitHub Pages browser demo and local Python application; key setup remains local. AI and GWAS Catalog require the Python version.

Original project-code licensing remains pending owner selection. Source data and third-party components retain their own terms; see the licensing documents.
