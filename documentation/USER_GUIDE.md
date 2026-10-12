# Using OpenBEXI Discovery 1.2.1

[Live demo · V1.2.1](https://arcazj.github.io/openbexi_discovery/) · [Downloads and release notes](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.2.1)

Version 1.2 adds reviewed profile updates and rollback, quizzes with scores and history, API connections, dataset privacy review, control captions, and progress bars for every AI task. These features require the local application; the public demo remains an evidence-browsing preview.

## Start with REI

REI at Advanced is the default. Evidence search and saved research retain the original workflow. The Settings gear opens **Settings**. Open **Saved research** there to review, compare, or export briefs; **Back to research** or the OpenBEXI Discovery name returns to search. Search is the default view on launch. Choose **Edit** or **Use profile** for an existing profile, or **Create profile** to select themes for a new one. **Settings > Local library** shows activities across profiles. The right side of the header contains one AI connection/status button, the Settings gear, and **Help (?)**.

The bundled [REI template](../templates/rei.json) now includes the reviewed embryology, assisted-reproduction, and infertility research focus. It keeps Advanced level, the six saved tab choices plus the Sources tab, the three evidence sources, and the original AI attribution for generated wording. Fresh installations use this template. Upgrades keep existing profiles and history; **Reset** explicitly restores the bundled REI configuration, with the previous revision available through rollback.

Profile wording describes research requirements, not additional processing capabilities. Video analysis, Excel workbook processing, and local AI are not implemented. To prevent external requests, explicitly enable **Local-only mode** in the AI connection dialog; mentioning local-only handling in a profile does not enable the switch. Public evidence searches and configured OpenAI requests require external connections.

The large workspace title is centered between equally sized side sections; the title column uses a 1.618 proportion and keeps a plain background. A solid gear opens Settings. The local REI workspace automatically searches **Last Embryology research** once on launch, using the selected sources. This text appears as a placeholder in the empty search field and disappears when you type. Local-only mode, sensitive mode, or editing the query during startup prevents the automatic search. Other profiles and the public demo keep manual search. The workspace omits recent-query chips, the profile description, and the welcome card. The search row keeps only **Search** and, while searching, **Cancel**. To draft a question, open **Settings → Saved research → New brief**. Results use the full workspace width and a tall white area, including when there are no records; detail panels stay compact and fit smaller screens. The public demo supports evidence browsing and manual briefs; profiles, local libraries, SQLite, and AI require the local application.

Buttons, tabs, and selectors have short help captions. Hover over a control or focus it with the keyboard to read its purpose; on touch screens, press and hold without activating it. Press Escape to dismiss a caption. Captions are also available to screen readers. Search automatically recognizes a topic, gene, or genomic region. Gene and region searches use the human genome (GRCh38); literature can include other organisms.

**Connect AI** offers Model and Reasoning choices, defaulting to **GPT-6 Astra / xHigh**. Enter a key once and choose **Save & connect**; the same header button lets you change these choices later. **By profile and model** shows local usage. A visible notice explains exhausted API credits/quota. The orange/green color key directly below the header identifies AI-generated text and source/user text whose upstream AI origin is unverified.

## Profiles and levels

Create a profile from the general template, search or browse taxonomy branches, and select themes/refinements. Choose a name, goal, and level. Preview before saving. Theme, wording, level, tab, and goal changes update the current profile with a new revision. Optional AI-assisted wording uses metered API tokens.

**Sources → Source settings → Manage themes** opens the current selections. Choose **Add theme** to search or browse the catalogue, remove a selected theme with its **×**, then **Save themes**. The active profile keeps its saved research, datasets, and quiz history. An **Undo** button in Source settings restores the preceding profile revision; older activities keep their original theme snapshots.

**+ Add source** opens the evidence catalogue, public API presets, custom API setup, and SQLite setup. **Manage sources → Remove from workspace** hides an evidence source or connected source for this profile. Its saved connection and datasets remain available. Restore it through **+ Add source → Add to workspace**, or use **Undo** immediately after the change. Evidence checkboxes still control participation in each search; a removed source is excluded even if it was checked previously. **Reset** restores the three recommended evidence sources. Sources appears immediately after Evidence. Each row includes a short description and right-aligned **Read/Open**, **Edit** where supported, and **Delete** actions. Deleting a built-in source removes it from this workspace; deleting a connection removes the saved connection and credentials after confirmation, while preserving datasets.

Levels: Foundation, Intermediate, Advanced, Expert, Researcher, Frontier, Beyond the Frontier. Advanced is preselected for new profiles. The saved level controls subsequent guidance and quiz requests. Experimental inquiry does not guarantee discovery or novelty.

Profiles have revision checks and undo. REI can be reset but not deleted. Deleting another profile retains historical materials. Save unsaved material before switching profiles or leaving the app.

**Settings → Update profile with AI** provides a text area for your requested changes. Select **Generate preview**, compare the current and proposed values, then choose **Apply selected changes**. You can deselect individual changes or discard the preview. Editing your instructions invalidates the previous preview. AI-generated preview content retains orange provenance and its model attribution. The workspace heading and search controls keep their normal backgrounds while retaining attribution.

While preparing the preview, an animated progress bar, elapsed time, and a polite wait message show that AI is working. The bar shows ongoing activity rather than a completion percentage. Detailed requests and higher reasoning can take a few minutes. **Cancel preparation** stops waiting and discards the pending preview; your saved profile stays unchanged. Usage already incurred may still be recorded. Reduced-motion preferences are respected.

The same progress indicator covers **every AI request**: quizzes, profile drafts, guidance, evidence explanations, research questions, comparisons, API recommendations, dataset analysis, and connection checks. It stays visible below an open dialog's heading or in the corner of the workspace. Each concurrent task has its own labeled bar and elapsed time. Completed, failed, timed-out, and canceled requests are removed independently. Existing Cancel controls remain available for tasks that support cancellation.

If an update is already fully reflected in your saved profile, asking again reports **No profile changes needed**. Exact repeats and simple presentation/politeness variations are checked locally without another AI call. The AI checks other similar phrasings against relevant prior requests and can report the same result without rewriting equivalent wording. New requirements, partial applications, changed level/layout permissions, and rollback are evaluated against the current profile. Repeated checks do not create another profile revision. Sensitive request bodies are excluded from this reuse.

Profile updates are available in Settings. Searching does not update your profile or automatically request AI guidance.

Learning level and layout stay unchanged by default. Enable their separate options when requesting a change; proposed level and layout changes also start unchecked in the review. Search difficulty alone does not establish expertise.

After applying an AI update, **Roll back profile** appears in **Sources → Source settings**. **Settings → Profiles → Roll back profile** is also available whenever an earlier saved revision exists, including after restarting. It restores the previous goal, themes, level, wording, and interface settings as a new revision. Saved research, datasets, and quiz history remain available. Rollback restores profile configuration; it does not undo external requests or API charges.

## Workspace tabs

| Tab | Use |
| --- | --- |
| Evidence | Search sources, inspect coverage, and build briefs. The local REI workspace runs its default search on launch. |
| Sources | Choose evidence sources, add API/SQLite connections, and manage themes and sources. |
| Documents | Create, import, read, edit, and delete documents. Import PDF, UTF-8 Markdown, text, or JSON; Markdown displays as safe text. |
| Datasets | Import CSV/JSON, review privacy rules, and save a separate sanitized working copy. Calculate local statistics or ask AI about that copy. |
| Connections | Connect a public or authenticated HTTPS JSON API, ask AI to recommend sources for your profile, or browse SQLite read-only. |
| Quizzes | Start an AI quiz with 8 questions for your level; view scores, review attempts, and remove history. Saved quizzes can be retaken offline. |
| Private documents and Notes | The renamed Notes tab is last, aligned to the right. Save notes and revisions without overwriting earlier content; use Documents for document files. |

Saved-material rows show a short preview and right-aligned **Summarize**, **Analyze with AI**, **Open**, **Edit** where applicable, and **Delete** actions. AI summaries and analyses require an explicit request and consent to send the displayed text. Text is bounded to 12,000 characters; PDF analysis uses saved notes, not PDF pages. Dataset AI continues to require an approved privacy-reviewed working copy. Deletion asks for confirmation.

Live sources focus on biomedicine and genomics. Other subjects can use local materials; changing themes does not add a search provider.

## Documents

Choose **Documents → New document** to write text, or **Import file** to load a PDF, Markdown, text, or JSON file (up to 8 MB). Enter a title and choose **Save locally**. **Open** reads a saved document; **Download document file** retrieves its complete attachment.

In an open document, **Edit document → Save changes** updates that same library entry. You can change its title and text, or select a replacement file. Text edits also update the downloadable attachment. For PDFs, edit the title and accompanying notes, or upload a replacement to change the pages. Files longer than 250,000 characters show a partial preview: download the complete file and upload a replacement to edit it. Leaving the file picker empty preserves the attachment. **Cancel** discards unsaved edits. If another window has saved changes, reopen the document before editing again.

**Delete local activity** asks for confirmation and removes the document and its attachment from this computer; existing ZIP backups remain. These actions also work from **Settings → Local library**, including for documents from other profiles. ZIP previews stay read-only until imported. Sensitive documents require explicit permission when saving, and retain their sensitive designation.

## Quizzes and history

Choose **Quizzes → Start a quiz**. AI creates eight multiple-choice questions for the active profile's themes, goal, and level, then opens the saved quiz. Select one answer for every question and click **Grade & save attempt**. The result shows your score out of eight, percentage, correct answers, and explanations. Each saved quiz has **Start**, which opens a fresh attempt without an AI call, and **Delete quiz**, which asks for confirmation and preserves previous attempts and scores. **Take quiz again** starts another attempt; **Create quiz** still supports manually authored quizzes.

During generation, the **AI is working** panel shows **Creating an 8-question quiz**, an animated bar, elapsed time, and a wait message. **Cancel** discards the pending quiz. Higher reasoning may take several minutes; the activity bar does not estimate a completion percentage.

**Quiz history** keeps each completed attempt, its date, level, and score. **Review attempt** reopens the answers and explanations, including after a restart. **Remove attempt** removes one result; **Clear history** removes all attempts for the current profile. These actions preserve saved quizzes and other profiles' history. ZIP backups keep any previously exported copies.

## API connections

**Connections → Connect to an API** appears before SQLite. Choose a public preset or enter a JSON endpoint. **Recommend APIs with AI** uses your active profile's subjects, goal, and level to select from the documented catalog; it does not receive connection credentials or datasets. The catalog includes [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [ClinicalTrials.gov](https://clinicaltrials.gov/data-api/api), and [Open Library](https://openlibrary.org/dev/docs/api/search).

Public APIs need no credentials. Private services can use a bearer token, an API key in a header/query parameter, or a username and password. Use **API query options** for the search parameter, records path, and fixed parameters such as page size. **Test & save connection** verifies a bounded JSON response. API rows place **Edit connection**, **Connect/Reconnect**, **Explore API**, and **Delete** on the right. **Connect** tests and saves a public preset; **Reconnect** checks saved settings. **Explore API** opens its data explorer, connecting a public preset first when necessary. **Delete** removes the saved connection and credentials after confirmation, preserving reviewed datasets. An unconnected suggestion can also be removed from this profile; **Restore API suggestions** makes it available again. Credentials remain blank in edit forms; leaving them blank preserves credentials for the same endpoint and authentication method. Changing the endpoint requires entering credentials again.

**Explore API → Retrieve data** fetches one response and opens a local privacy review. Once you approve a working copy, its question field and **Calculate statistics** become available. Statistics cover the saved copy, not all upstream records. **Ask AI about this copy** sends only that reviewed copy's statistics, up to 100 sampled rows, and your question; identifiers known to the replacement mapping are replaced in the question too. Green styling identifies working-copy data; orange identifies AI interpretation. Results identify the source and sample scope.

The connector supports Internet HTTPS endpoints on port 443 returning JSON through GET. It does not execute arbitrary SQL/code, perform write operations, sign in through OAuth, follow redirects, or access private-network/loopback endpoints. Responses are limited to 2 MB; select a smaller API page if necessary. API failures and authentication errors remain visible without exposing provider response bodies or credentials.

## Dataset privacy review

Choose **Datasets → Import file → Review privacy** for a CSV or JSON array. Original files remain unchanged. Imports support up to 8 MB, 5,000 rows, and 100 columns; nested JSON objects become named columns. API responses and existing SQLite snapshots can use the same review.

Review each column: **Keep**, **Replace with labels**, **Remove**, **Mask**, **Year only**, or **Numeric bands of 10**. Patient names can become `Patient 1`, `Patient 2`, and so on, with repeated values retaining their label. Passwords, tokens, and credential fields are always removed. Free text is removed by default; if you retain it, known identifiers and detectable contact/credential patterns are scrubbed. Enter additional names or sensitive phrases under **Additional sensitive values**. Local rules cannot detect every identity or sensitive combination.

Choose **Preview working copy**, inspect the transformed rows, and confirm the review before **Save reviewed working copy**. Changes to protection rules require another preview. You can name the copy; known sensitive terms are removed from that name as well. Working copies are labeled pseudonymized, not guaranteed anonymous, and remain marked sensitive in export review.

Optionally retain an encrypted private original to revise protection rules later. Replacement mappings and retained originals stay outside the portable library, are excluded from ZIP exports and AI requests, and are deleted when their working copy is deleted. Without a retained original, reimport your original to undo removals. **Revise privacy rules** creates a new reviewed copy instead of overwriting earlier work. Legacy datasets and imported ZIP copies require a new local review before AI is enabled. Locally computed statistics include numeric count, missing values, mean, median, minimum, maximum, and categorical counts.

## SQLite

Choose **Connections → Connect SQLite database**. Provide a database path on the server computer or upload a copy (8 MB maximum). Mark sensitive data and authorize retention before uploading. SQLite support is included in the Windows app.

Select table columns and an optional equality filter, then preview up to 50 rows. Queries are read-only and time-bounded. Explicitly save the displayed page as a dated offline snapshot. Deleting a database connection retains the original database and saved snapshots; delete snapshots separately through Local library.

Database rows are not automatically sent to AI. Save a snapshot, open it in **Datasets**, and use **Review privacy and create working copy** before analysis. Keep patient identifiers out of ordinary research prompts.

## Offline and ZIPs

Open the **AI connection/status button → Local-only mode** to disable external requests while the local server runs. Read saved documents, search stored text/metadata, edit notes, create profiles from templates, and grade saved quizzes. Scanned PDF search/OCR is not included.

Export one activity, one profile, or the whole library. Sensitive snapshots are excluded unless explicitly selected. Credentials and live connection settings are never exported. **Open ZIP** previews the archive read-only in temporary server memory; reopen it after a restart. Import before editing. Identical items are skipped, conflicts become copies, and existing profiles are not overwritten. Imported profile snapshots preserve historical context and can be restored as separate profiles.

Limits: 8 MB per uploaded file; ZIPs up to 32 MB compressed, 64 MB expanded, and 1000 artifact entries. Export smaller selections as needed. ZIPs and local JSON are not encrypted: protect sensitive backups with appropriate storage access controls.

## Storage and migration

`user_profiles/` stores configurations, `discovery_library/` stores activities/files, and `.discovery/` stores private state and usage. Installed Windows data lives in its private user-data directory, outside the installation. Override with `DISCOVERY_DATA_DIR`; optionally set `DISCOVERY_LIBRARY_DIR` separately.

Legacy browser briefs migrate into REI when the backend first reads them. Browser storage is retained as backup. A different URL/port has different browser storage: export/import legacy briefs if changing addresses. Saved research still offers JSON and Markdown export.


Profile and full-library ZIP exports include the current profile configuration and workspace, even for an empty profile. After importing, open a historical item and choose **Restore as a new profile** to create an inactive copy; a workspace backup also restores its saved briefs and preferences. Select the new copy in Settings. Live connections must be configured again. Sensitive workspace backups are excluded unless explicitly included.

### Profile wording and preview

In **Settings > Profiles > Edit > Edit page wording**, **Workspace heading** sets the large header title. Existing descriptions and welcome wording remain in saved profile data; the main workspace hides them to keep the evidence view focused on search results. The editor preview retains the description for reviewing existing profiles. Saving records the reviewed wording, and switching profiles restores the matching title. The version label beside the brand is shared by every profile.
