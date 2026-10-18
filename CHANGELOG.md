# Releases

## 1.2.2 ? Broad and specific search with compact reasoning controls

- Adds Overall Search with GPT-6 Astra web search, clickable citations, and no checkbox restrictions.
- Adds Specific Search with Astra-generated queries limited to selected sources; an empty selection runs an overall search.
- Places Request privacy directly beneath Specific Search, with two right-aligned green split buttons and independent Low / Medium / High reasoning settings, defaulting to Medium.
- Makes the prompt box prominent through restrained contrast and spacing, with responsive layouts, captions, cancellation and empty-result recovery.
- Preserves direct source browsing without AI, source error reporting, sensitive-request review, local-only mode, existing profiles and saved work. Meters web-search calls as well as tokens.
- Keeps automatic launch retrieval free of AI generation. Adds backend and desktop/mobile regression checks; application version is 1.2.2 and saved-data schemas stay at 1.1.

## 1.2.1 — Cleaner workspace, document editing, and reliable upgrades

- Simplifies the workspace with a larger centered plain-background title, golden-ratio proportions, solid Settings gear and bold circled Help icon, inline provenance legend, and a tall white results area, and no recent-query chips, profile shortcut, introductory description, constraints, or tips. Moves Sources after Evidence and renames the rightmost Notes tab to Private documents and Notes.
- Runs “Last Embryology research” once when the local REI workspace launches, respecting local-only/sensitive mode and user edits during startup. Shows the default as a placeholder, leaving the input empty and ready to type.
- Removes More actions and Suggest research directions from the search row; Search remains the primary action. Manual briefs stay available through Settings → Saved research → New brief.
- Replaces API catalogue “Use” buttons with Edit connection, Connect/Reconnect, Explore API, and confirmed Delete actions. Saved quizzes have Start and Delete quiz buttons; deletion preserves previous scores.
- Adds compact right-side detail panels and saved-item previews with right-aligned summary, AI analysis, open, edit, and confirmed deletion actions. Dataset analysis retains its privacy-review gate.
- Completes local document create/read/update/delete, with editable text and PDF notes, attachment replacement/download, conflict detection, and immediate library refresh. ZIP previews remain read-only.
- Refreshes the browser UI automatically after upgrades using a fresh launch URL, content fingerprints for scripts/styles, and cache headers. Browser research, cookies, and saved profiles are preserved.
- Prepares publisher signing for the app, uninstaller, and Setup, including timestamp verification and checksums after signing. A trusted certificate or Microsoft Artifact Signing identity must be configured before publishing signed installers; new downloads may still show reputation warnings.

## 1.2.0 — Reviewed profiles, quizzes, and private working copies

- Adds explicit AI profile updates with a text request, selectable preview, saved revisions, and rollback. Repeated or equivalent requests can report no changes; exact applicable repeats reuse the prior result locally.
- Shows a labeled progress bar, elapsed time, and polite wait message for every AI request, including quiz generation, concurrent tasks, connection checks, and work inside dialogs.
- Generates eight-question quizzes for the active profile and level, grades locally, and retains reviewable scores and history with individual or bulk removal.
- Consolidates AI setup into Connect AI with model and reasoning choices, defaulting to GPT-6 Astra / xHigh. Keeps By profile and model usage, removes the Usage & budget editor, and explains exhausted quota or previously saved limits.
- Adds profile-based API recommendations and public/authenticated HTTPS JSON connections before SQLite, with reviewed data retrieval, local statistics, and questions about approved working copies.
- Adds dataset privacy review with stable identifier labels, forced credential removal, configurable masking/removal, and separately encrypted mappings and optional originals. AI receives only reviewed statistics and a bounded working-copy sample.
- Adds theme/source catalogue management, removal and undo, plus mouse, keyboard, and touch help captions for controls.
- Restores the orange/green provenance legend and keeps standard backgrounds on the workspace introduction, source bar, profile badge, and search controls.
- Bundles the reviewed REI/Advanced embryology and assisted-reproduction profile, retaining generated-content attribution. Existing saved profiles and private data survive upgrades.
- Updates documentation, dependency notices, Windows packaging, source archives, and release checks. The Windows installer includes Python, SQLite, encryption dependencies, and all new UI assets.

Profile wording does not implement video/Excel processing or local AI. Data/profile/archive schemas remain compatible at `1.1`; application version is `1.2.0`.


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
