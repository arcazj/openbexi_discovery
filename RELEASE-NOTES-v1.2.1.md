# OpenBEXI Discovery v1.2.1

Version 1.2.1 simplifies the research workspace, completes document editing, and refreshes cached browser assets after upgrades.

## Changes

- **Workspace:** a larger, centered Embryology research workspace title, golden-ratio header proportions, bold Settings and Help icons, and an orange/green provenance legend. Sources follows Evidence; Private documents and Notes is the rightmost tab. Results keep a tall white area, including with zero records. Right-side panels stay compact.
- **Search:** the local REI workspace searches **Last Embryology research** once at launch. The input stays empty and displays that phrase as a placeholder, which disappears when typing. Local-only mode, sensitive mode, and edits during startup prevent the automatic search. Other profiles and the public demo keep manual search. No AI guidance is generated automatically.
- **Simpler controls:** removes More actions, Suggest research directions, recent-query chips, the profile-update shortcut, introductory copy, research-constraint panels, and tips. Manual briefs remain available through Settings → Saved research → New brief. Evidence explanations and saved-item AI actions remain available.
- **Documents:** create, import, read, edit, and delete local documents; replace or download attachments, edit text and PDF notes, and detect conflicting revisions. Attachment replacement preserves the existing document ID and rolls back on failure. Library views refresh after changes; ZIP previews remain read-only.
- **Saved material:** short previews and right-aligned summary, AI analysis, open, edit, and confirmed delete actions where supported. AI analysis requires review and explicit consent; datasets retain their privacy-review workflow.
- **Connections:** Edit connection, Connect/Reconnect, Explore API, and Delete replace catalogue Use buttons. Removed API suggestions can be restored. Deleting a connection preserves saved datasets.
- **Quizzes:** saved quizzes have Start and Delete quiz controls. Starting a saved quiz works without generating new questions or calling AI; deleting it preserves previous scores and attempts.
- **Windows updates:** fresh launch URLs, content fingerprints, and cache headers load the installed page, scripts, and styles without clearing saved browser research, profiles, or cookies.
- **Publisher signing:** build support signs and verifies the app, uninstaller, and Setup before generating checksums when a trusted signing identity is configured. Unsigned downloads can still show browser/Windows reputation prompts.

## Compatibility and privacy

The application version is `1.2.1`; profile, data, and archive schemas remain `1.1`. Existing profiles, saved work, history, credentials, and installation locations are preserved. Bundled templates do not overwrite edited profiles.

Release inputs exclude `.env`, OpenAI keys, private profiles, local libraries, connection credentials, and private datasets. AI requires your own configured key. Local-only mode must be enabled explicitly to prevent external requests.

## Release artifacts and verification

The release packages are `OpenBEXIDiscovery-1.2.1-Windows-x64-Setup.exe`, named source ZIP/tar.gz archives, these notes, and SHA-256 checksums. The Windows build records the exact source commit in `BUILD-INFO.json`. Publishing the installer and hosted demo is separate from preparing the release commit.

Backend and browser checks cover document CRUD and attachment failures, reviewed AI context, default launch search and typing, responsive layouts, connection actions, saved quizzes, profile isolation, cache upgrades, and public packaging. Automated tests use temporary data and synthetic API responses without paid AI calls. The Windows workflow verifies installation and upgrade from v1.2.0.

[Release v1.2.1](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.2.1) · [User guide](documentation/USER_GUIDE.md) · [Windows installation](WINDOWS_INSTALLATION.md)
