# Windows installation · 1.2.0

[Live demo · V1.2.0](https://arcazj.github.io/openbexi_discovery/) · [All downloads and release notes](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.2.0)

Choose the `.exe` asset for installation. The release's ZIP and tar.gz files contain source code; follow [Run from source](README.md#run-from-source) to use them. `SHA256SUMS-Windows.txt` verifies the installer, and `SHA256SUMS.txt` covers all named release downloads.

## Install and launch

1. Download **[OpenBEXIDiscovery-1.2.0-Windows-x64-Setup.exe](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.0/OpenBEXIDiscovery-1.2.0-Windows-x64-Setup.exe)** from the project release.
2. Run Setup. It installs for the current Windows account, adds Start menu shortcuts, and offers a desktop shortcut.
3. Launch **OpenBEXI Discovery**. It opens your default browser and runs the local Python service in the background.
4. Browse evidence immediately. To enable AI, open **Connect AI**, choose a model and reasoning level (default **GPT-6 Astra / xHigh**), enter your own OpenAI key, and choose **Save & connect**. The same header status button reopens these choices later.

Supported package: **Windows 10/11, x64**, with a modern browser. Python, SQLite, templates, taxonomy, prompts, and dependencies are bundled; neither Python installation nor administrator access is required. Installation works offline after download; public sources and OpenAI require internet. Native ARM64 and 32-bit packages are not supplied or tested.

Use the Discovery icon in the Windows notification area to **Open research workspace** or **Quit OpenBEXI Discovery**. Closing the browser tab leaves the service running. Launching again opens the existing instance. There is no Windows service, firewall rule, or startup-at-login entry.

## Private data and updates

Default application folder: `%LOCALAPPDATA%\Programs\REIResearchExplorer`.

Private settings folder: `%LOCALAPPDATA%\REIResearchExplorer`. The API key is saved in its `.env`; `desktop.json` remembers the local port and instance identity. No key is included in the installer or copied into the browser.

Version 1.1 migrates the existing browser workspace into the default **REI / Advanced** profile, keeping the browser copy as a recovery backup. Profiles live in `user_profiles/`, materials and history in `discovery_library/`, and workspace revisions, usage accounting, and connection settings in `.discovery/`, all under the private settings folder. The legacy folder and executable names remain stable for upgrade compatibility.

Version 1.2 bundles the reviewed REI embryology and assisted-reproduction template for new installations. Upgrades preserve your current REI profile, its revisions, saved work, and AI connection settings. External API credentials, dataset replacement mappings, and optional retained originals stay under `.discovery/private/`; Windows protects them with the current account's DPAPI. The installer contains public templates, never your `.env`, private profiles, datasets, connection credentials, or API key.

Use **Local library → Export entire library** for portable ZIP backups. ZIPs contain permitted materials and profile snapshots, not API keys or live database connection configuration. For complete local recovery, also back up the private settings directory securely while the app is closed. See the [user guide](documentation/USER_GUIDE.md).

Rerun Setup to update. Uninstall through **Windows Settings → Apps → OpenBEXI Discovery**, or the Start menu Uninstall shortcut. Updates and uninstall preserve private settings and browser research. The uninstaller deletes only packaged files, retaining additional user files in the installation folder.

Confirm **V1.2.0** after the OpenBEXI Discovery name after updating. SQLite works immediately: connect a local file or upload a copy from Connections. No database server, Python, or Node.js installation is needed. Quizzes and all AI operations show a labeled progress bar while waiting.

## Troubleshooting

- **Windows warning:** this build is unsigned. Download only from the GitHub release; compare its SHA-256 with `SHA256SUMS-Windows.txt`. Windows may show an unknown-publisher/SmartScreen prompt. Managed PCs can require IT approval; do not disable security software.
- **Browser did not open:** use the tray icon's Open command, or relaunch from the Start menu. The app listens only on `127.0.0.1`.
- **Update cannot close the app:** choose Quit from the tray, then retry Setup.
- **AI unavailable:** use the AI connection/status button to check your key, model access, reasoning choice, and connection. A quota notice explains exhausted credits. Browsing/manual briefs remain available.
- **Briefs missing:** select the original REI profile. For a first legacy migration, use the original browser and port, or import the old Saved research JSON backup.

## Build and verify

Build on Windows x64 with Python 3.12 and [NSIS](https://nsis.sourceforge.io/Download). From the current source checkout:

```powershell
py -3.12 -m venv .build-venv
.\.build-venv\Scripts\python.exe -m pip install -r requirements.lock.txt -r installer/requirements-build.txt
.\.build-venv\Scripts\python.exe -m scripts.build_windows
.\.build-venv\Scripts\python.exe -m scripts.test_windows_install
```

Output: `dist/OpenBEXIDiscovery-1.2.0-Windows-x64-Setup.exe` and `dist/SHA256SUMS-Windows.txt`. The GitHub Windows installer workflow performs the same build and installation checks on Windows Server 2022. The smoke test uses isolated temporary folders and refuses to replace an existing registered installation.

The installer build records its source commit, Python, PyInstaller, and NSIS versions in `BUILD-INFO.json`. Packaging uses an explicit public-asset list and checks for private paths/keys. Python, PyInstaller, NSIS, and dependency license texts are included. Original-code licensing remains pending owner selection; review [commercial notes](COMMERCIAL_LICENSING.md) and [third-party notices](THIRD_PARTY_NOTICES.md) before redistribution.
