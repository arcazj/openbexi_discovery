# OpenBEXI Discovery v1.1.1

This refreshed v1.1.1 release includes the latest compact workspace UI.

- Keeps OpenBEXI Discovery on the left, with AI status, AI settings, Settings, and Help aligned on the right.
- Opens the same Settings panel from the gear and active profile button.
- Places Saved research and Local library in Settings; search opens by default.
- Uses an inline workspace heading and smaller description that wrap naturally.
- Removes the extra heading above the initial evidence card while retaining search progress and result headings.
- Uses golden-ratio desktop columns, consistent control sizing, and responsive mobile spacing.
- Aligns profile wording controls, preview, templates, and AI drafts with the current UI; keeps custom wording and supports existing REI profiles.
- Shows the application version in small text after the brand.
- Updates the live demo, guides, Windows installer, source archives, and checksums together, retaining version 1.1.1.

Existing profiles, saved work, schemas, and private application data locations remain compatible.

## Demo and downloads

[Live demo](https://arcazj.github.io/openbexi_discovery/) · [All v1.1.1 downloads](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.1.1) · [User guide](https://github.com/arcazj/openbexi_discovery/blob/v1.1.1/documentation/USER_GUIDE.md)

- [OpenBEXIDiscovery-1.1.1-Windows-x64-Setup.exe](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/OpenBEXIDiscovery-1.1.1-Windows-x64-Setup.exe): Windows 10/11 x64 installer with Python and SQLite included.
- [OpenBEXIDiscovery-1.1.1-source.zip](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/OpenBEXIDiscovery-1.1.1-source.zip) and [OpenBEXIDiscovery-1.1.1-source.tar.gz](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/OpenBEXIDiscovery-1.1.1-source.tar.gz): source code and documentation for the release commit.
- [RELEASE-NOTES-v1.1.1.md](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/RELEASE-NOTES-v1.1.1.md): these notes.
- [SHA256SUMS.txt](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/SHA256SUMS.txt): checksums for all named downloads.
- [SHA256SUMS-Windows.txt](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/SHA256SUMS-Windows.txt): installer checksum used by upgrade verification.

The public demo supports evidence browsing and manual briefs. Profiles, local libraries, SQLite, archives, and AI require the local application. Source archives require the setup described in the README.

## Verification

Release checks cover backend behavior, frontend syntax, desktop/mobile browser workflows, hosted-demo behavior, and Windows installation and upgrade compatibility. No paid AI requests are used in automated verification.
