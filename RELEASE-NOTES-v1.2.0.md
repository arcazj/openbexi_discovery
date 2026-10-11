# OpenBEXI Discovery v1.2.0

Version 1.2 adds reviewed AI profile updates, quizzes with scored history, API connections, dataset privacy review, and visible progress for every AI task. It includes the reviewed REI profile at Advanced level.

## Changes

- **Profiles:** request changes in a text area, preview and select fields, apply them explicitly, and roll back to the previous saved profile. Related searches offer an update shortcut. Repeated or equivalent requests can report no profile changes.
- **AI progress:** quizzes, profile preparation, guidance, explanations, comparisons, API recommendations, dataset questions, and connection checks show a task label, activity bar, elapsed time, and wait message. Concurrent requests and dialog transitions remain visible.
- **Quizzes:** generate eight questions for the active themes and level, grade locally, review scores and explanations, retake saved quizzes, and remove individual or all attempts for a profile.
- **AI connection:** one Connect AI/status button offers model and reasoning choices, defaulting to GPT-6 Astra / xHigh. By profile and model usage remains available, with notices for exhausted quota and previously saved local limits.
- **Connections and datasets:** connect public or authenticated HTTPS JSON APIs, request profile-based API recommendations, or browse SQLite read-only. Review privacy rules and create a separate working copy before statistics or AI analysis. Identifiers use consistent replacement labels; credentials are removed. Private mappings and optional originals are encrypted separately and excluded from AI requests and exports.
- **Workspace:** manage themes and source catalogues with removal and undo. Buttons and selectors have help captions. The orange/green provenance legend is restored; navigation, source, introduction, and search areas keep standard backgrounds.
- **REI profile:** the bundled template includes the reviewed embryology, assisted-reproduction, and infertility focus at Advanced level, preserving AI attribution for generated wording.

## Compatibility and privacy

Existing saved profiles, history, research, and connection settings are preserved on upgrade. Fresh installations use the bundled REI template; Reset is an explicit way to adopt it on an existing profile. The application version is `1.2.0`; profile and archive schemas remain `1.1`.

The installer and source downloads contain public code, templates, and documentation. They exclude OpenAI keys, `.env`, private profiles, connection credentials, datasets, and local research history. Supply your own key through Connect AI. The Windows package is unsigned.

Profile wording describes research requirements; it does not add video analysis, Excel workbook processing, or local AI. Enable Local-only mode explicitly to stop external requests. Privacy review produces pseudonymized working copies, not a guarantee of anonymity.

## Downloads

[Live demo](https://arcazj.github.io/openbexi_discovery/) · [All v1.2.0 downloads](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.2.0) · [User guide](https://github.com/arcazj/openbexi_discovery/blob/v1.2.0/documentation/USER_GUIDE.md)

- [Windows x64 installer](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.0/OpenBEXIDiscovery-1.2.0-Windows-x64-Setup.exe): Windows 10/11 app with Python, SQLite, and dependencies included; no administrator access required.
- [Source ZIP](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.0/OpenBEXIDiscovery-1.2.0-source.zip) and [source tar.gz](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.0/OpenBEXIDiscovery-1.2.0-source.tar.gz): source and documentation for the tagged release commit.
- [Release notes](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.0/RELEASE-NOTES-v1.2.0.md): these notes.
- [SHA256SUMS.txt](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.0/SHA256SUMS.txt): checksums for all named downloads.
- [SHA256SUMS-Windows.txt](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.0/SHA256SUMS-Windows.txt): installer checksum.

The hosted demo supports evidence browsing and manual briefs. Profiles, quizzes, local libraries, connections, privacy review, and AI require the local application. Source archives require the setup described in the README.

## Verification

Release checks cover backend behavior, frontend syntax, desktop/mobile browser workflows, AI progress and cancellation, profile rollback/repeated requests, dataset privacy boundaries, and hosted-demo packaging. The Windows workflow builds the tagged source commit and verifies installation, bundled execution without Python on PATH, REI template availability, private storage, upgrade from v1.1.1, and uninstall preserving user data. Automated verification uses synthetic data and makes no paid AI requests.
