# OpenBEXI Discovery · 1.1.1

**Make human knowledge accessible to everyone, from the first lesson to the frontiers of scientific discovery.**

A local learning and research workspace. Start with the familiar **REI profile at Advanced level**, including PubMed, Ensembl, GWAS evidence, research briefs, and AI guidance.

[Live demo · V1.1.1](https://arcazj.github.io/openbexi_discovery/) · [Release v1.1.1 and downloads](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.1.1) · [Release notes](CHANGELOG.md#111--compact-layout-and-profile-settings) · [User guide](documentation/USER_GUIDE.md)

The live demo displays **V1.1.1** beside AI settings. This release adds a compact header, golden-ratio desktop columns, and a **REI · Advanced** button that opens the same Profile settings as the gear in the local app.

## Downloads · v1.1.1

| Download | Contents |
| --- | --- |
| [Windows installer](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/OpenBEXIDiscovery-1.1.1-Windows-x64-Setup.exe) | Windows 10/11 x64 app with Python and SQLite included. |
| [Source ZIP](https://github.com/arcazj/openbexi_discovery/archive/refs/tags/v1.1.1.zip) | Tagged source code and documentation. |
| [Source tar.gz](https://github.com/arcazj/openbexi_discovery/archive/refs/tags/v1.1.1.tar.gz) | The same tagged source for Unix-style tools. |
| [Release notes](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/RELEASE-NOTES-v1.1.1.md) | Downloadable changes, compatibility, and validation notes. |
| [SHA-256 checksums](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/SHA256SUMS.txt) | Checksums for the installer and named release assets. |

The release also includes named source archives with checksums. Source archives require the setup below; they do not include the Windows runtime.

## Install on Windows

[Download the Windows installer](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.1/OpenBEXIDiscovery-1.1.1-Windows-x64-Setup.exe), run Setup, then open **OpenBEXI Discovery**. Windows 10/11, 64-bit. Python and SQLite are included; no database server or administrator access is needed.

The app opens in your browser. Use the tray menu to reopen or quit. Private data survives upgrades and uninstall. [Installation help](WINDOWS_INSTALLATION.md)

## What you can do

- **Research:** search evidence, inspect sources, save questions, and compare briefs.
- **Personalize:** create profiles, choose research themes and one of seven levels, and preview UI wording.
- **Work locally:** collect documents, browse datasets, write notes, take quizzes, and open or export ZIP libraries without AI.
- **Connect data:** browse a local SQLite database read-only and explicitly save selected rows for offline use.
- **Control AI:** supply your own API key, review usage and estimated cost, and set token or dollar limits. AI pauses when a limit blocks requests.

Green identifies source/user content whose upstream AI origin may be unknown. Orange identifies app-generated AI content, with its model recorded. Red signals errors or blocked AI usage.

## Run from source

Python 3.9+; no frontend build step. In PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. On macOS/Linux, use `python3` and `.venv/bin/python`. Run one server worker. Internet is needed for live evidence and AI; **Local-only mode** uses saved content without external requests.

**IntelliJ IDEA:** select **OpenBEXI Discovery** in Run configurations, using the project's `.venv` interpreter. Run or Debug, then open the HTTP URL printed in the Run console. Running `backend/app.py` or `serve_frontend.py` also starts the full app. [IDE setup](documentation/DEVELOPMENT.md#intellij-idea)

The [browser demo](https://arcazj.github.io/openbexi_discovery/) supports basic evidence browsing and manual briefs. Profiles, SQLite, archives, and AI require the local app.

## Learn more

- [Profiles, tabs, quizzes, and local library](documentation/USER_GUIDE.md)
- [AI usage, budgets, and data privacy](documentation/AI_AND_DATA.md)
- [Architecture, schemas, extensions, and tests](documentation/DEVELOPMENT.md)
- [Community Edition and commercial roadmap](documentation/LICENSING_ROADMAP.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

3D engines, full adaptive tutoring, knowledge graphs, autonomous agents, and account-provider integrations are planned extensions. Licensing remains pending owner review.
