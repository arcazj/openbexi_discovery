# Using OpenBEXI Discovery 1.1.1

[Live demo · V1.1.1](https://arcazj.github.io/openbexi_discovery/) · [Downloads and release notes](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.1.1)

## Start with REI

REI at Advanced is the default. Evidence search and saved research retain the original workflow. Both **REI · Advanced** beside Sources and the gear beside **AI settings** open the same **Profile settings** panel. Choose **Edit** or **Use profile** for an existing profile, or **Create profile** to select themes for a new one. **Local library** shows activities across profiles.

The compact profile button shows the active name and level; hover for its full theme and goal. Desktop evidence and guidance panels use a roughly 62/38 split, and stack on smaller screens. The public demo supports evidence browsing and manual briefs; profiles, local libraries, SQLite, and AI require the local application.

## Profiles and levels

Create a profile from the general template, search or browse taxonomy branches, and select themes/refinements. Choose a name, goal, and level. Preview before saving. Changed themes create a new profile; edits to wording, level, tabs, or goal update the current profile. Optional AI-assisted wording consumes the AI budget.

Levels: Foundation, Intermediate, Advanced, Expert, Researcher, Frontier, Beyond the Frontier. Advanced is preselected for new profiles. The saved level controls subsequent guidance and quiz requests. Experimental inquiry does not guarantee discovery or novelty.

Profiles have revision checks and undo. REI can be reset but not deleted. Deleting another profile retains historical materials. Save unsaved material before switching profiles or leaving the app.

## Workspace tabs

| Tab | Use |
| --- | --- |
| Evidence | Search sources, inspect coverage, and build briefs. |
| Documents | Import PDF, UTF-8 Markdown, text, or JSON; Markdown displays as safe text. |
| Datasets | Import CSV or a JSON array of row objects; filter and page through stored rows. |
| Connections | Connect a local SQLite file or upload a copy; select tables/fields to preview read-only. |
| Quizzes | Create editable quiz JSON or request an AI draft; review, save, and grade locally. |
| Notes | Save notes and revisions without overwriting earlier content. |

Live sources focus on biomedicine and genomics. Other subjects can use local materials; changing themes does not add a search provider.

## SQLite

Choose **Connections → Connect SQLite database**. Provide a database path on the server computer or upload a copy (8 MB maximum). Mark sensitive data and authorize retention before uploading. SQLite support is included in the Windows app.

Select table columns and an optional equality filter, then preview up to 50 rows. Queries are read-only and time-bounded. Explicitly save the displayed page as a dated offline snapshot. Disconnecting retains snapshots; delete those separately through Local library.

Database rows are not automatically sent to AI. Version 1.1.1 provides local browsing/snapshots; AI analysis of connected datasets and external-account providers are not implemented. Keep patient identifiers out of ordinary research prompts.

## Offline and ZIPs

**AI settings → Local-only mode** disables external requests while the local server runs. Read saved documents, search stored text/metadata, edit notes, create profiles from templates, and grade quizzes. Scanned PDF search/OCR is not included.

Export one activity, one profile, or the whole library. Sensitive snapshots are excluded unless explicitly selected. Credentials and live connection settings are never exported. **Open ZIP** previews the archive read-only in temporary server memory; reopen it after a restart. Import before editing. Identical items are skipped, conflicts become copies, and existing profiles are not overwritten. Imported profile snapshots preserve historical context and can be restored as separate profiles.

Limits: 8 MB per uploaded file; ZIPs up to 32 MB compressed, 64 MB expanded, and 1000 artifact entries. Export smaller selections as needed. ZIPs and local JSON are not encrypted: protect sensitive backups with appropriate storage access controls.

## Storage and migration

`user_profiles/` stores configurations, `discovery_library/` stores activities/files, and `.discovery/` stores private state and usage. Installed Windows data lives in its private user-data directory, outside the installation. Override with `DISCOVERY_DATA_DIR`; optionally set `DISCOVERY_LIBRARY_DIR` separately.

Legacy browser briefs migrate into REI when the backend first reads them. Browser storage is retained as backup. A different URL/port has different browser storage: export/import legacy briefs if changing addresses. Saved research still offers JSON and Markdown export.


Profile and full-library ZIP exports include the current profile configuration and workspace, even for an empty profile. After importing, open a historical item and choose **Restore as a new profile** to create an inactive copy; a workspace backup also restores its saved briefs and preferences. Select the new copy in Profile settings. Live connections must be configured again. Sensitive workspace backups are excluded unless explicitly included.
