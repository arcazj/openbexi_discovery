# OpenBEXI Discovery · 1.1

**Make human knowledge accessible to everyone, from the first lesson to the frontiers of scientific discovery.**

A local learning and research workspace. Start with the familiar **REI profile at Advanced level**, including PubMed, Ensembl, GWAS evidence, research briefs, and AI guidance.

[Download release 1.1](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.1.0) · [Release notes](CHANGELOG.md) · [User guide](documentation/USER_GUIDE.md)

## Install on Windows

[Download the Windows installer](https://github.com/arcazj/openbexi_discovery/releases/download/v1.1.0/OpenBEXIDiscovery-1.1.0-Windows-x64-Setup.exe), run Setup, then open **OpenBEXI Discovery**. Windows 10/11, 64-bit. Python and SQLite are included; no database server or administrator access is needed.

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

The [browser demo](https://arcazj.github.io/openbexi_discovery/) supports basic evidence browsing and manual briefs. Profiles, SQLite, archives, and AI require the local app.

## Learn more

- [Profiles, tabs, quizzes, and local library](documentation/USER_GUIDE.md)
- [AI usage, budgets, and data privacy](documentation/AI_AND_DATA.md)
- [Architecture, schemas, extensions, and tests](documentation/DEVELOPMENT.md)
- [Community Edition and commercial roadmap](documentation/LICENSING_ROADMAP.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

3D engines, full adaptive tutoring, knowledge graphs, autonomous agents, and account-provider integrations are planned extensions. Licensing remains pending owner review. The [legacy REI repository](https://github.com/arcazj/openbexi_REI) is retained as a backup.
