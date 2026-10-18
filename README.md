# OpenBEXI Discovery · 1.2.2

**Make human knowledge accessible to everyone, from the first lesson to the frontiers of scientific discovery.**

A local learning and research workspace. Start with the **REI profile at Advanced level**, including PubMed, Ensembl, GWAS evidence, research briefs, and optional AI analysis. Version 1.2 includes the reviewed REI embryology and assisted-reproduction profile as its default template; upgrades preserve your saved profile.

[Live demo · V1.2.2](https://arcazj.github.io/openbexi_discovery/) · [Release v1.2.2 and downloads](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.2.2) · [Release notes](RELEASE-NOTES-v1.2.2.md) · [User guide](documentation/USER_GUIDE.md)

**Verify every result before use.** AI output, retrieved sources, citations, and calculations may be incorrect, incomplete, or outdated. Users are responsible for independent verification and their decisions. This is a learning and research tool, not professional advice. Warranty and liability exclusions apply to the extent permitted by law. Read the [disclaimer](DISCLAIMER.md) and [commercial licensing terms](COMMERCIAL_LICENSING.md).

The workspace uses a compact header and golden-ratio desktop columns. The header keeps one AI connection/status button, the **Settings** gear, and **Help (?)** on the right. **Connect AI** offers OpenAI (default, GPT-6 Astra / xHigh), Anthropic, Gemini, DeepSeek, OpenRouter, and custom OpenAI-compatible providers, with separate saved keys and model settings. Token usage includes its date (UTC). Open **Settings** to select REI, Cosmologie, or another profile, or create a complete AI-generated profile by describing a field or area of interest. **Saved research** and **Local library** remain available in the workspace footer. The application version appears in small text after the brand.

Version 1.2.2 adds **Overall Search** across the web and **Specific Search** within checked sources or profile topics. OpenAI searches use **GPT-6 Astra**; other providers support scientific-source query planning with their selected model. Web search currently requires OpenAI. Each compact green search button includes supported reasoning choices up to **Ultra**, defaulting to Medium where available. Request privacy sits directly beneath Specific Search; the search box remains prominent and lightweight. Without AI, Specific Search can still retrieve checked sources directly.

Version 1.2 adds reviewed AI profile updates with rollback, eight-question quizzes with scores and history, API connections, dataset privacy review, help captions, and visible progress for every AI task. Each progress bar names the task and shows elapsed time, including inside dialogs and when multiple requests are running.

## Downloads · v1.2.2

| Download | Contents |
| --- | --- |
| [Windows installer](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.2/OpenBEXIDiscovery-1.2.2-Windows-x64-Setup.exe) | Windows 10/11 x64 app with Python and SQLite included. |
| [Source ZIP](https://github.com/arcazj/openbexi_discovery/archive/refs/tags/v1.2.2.zip) | Tagged source code and documentation. |
| [Source tar.gz](https://github.com/arcazj/openbexi_discovery/archive/refs/tags/v1.2.2.tar.gz) | The same tagged source for Unix-style tools. |
| [Release notes](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.2/RELEASE-NOTES-v1.2.2.md) | Downloadable changes, compatibility, and validation notes. |
| [SHA-256 checksums](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.2/SHA256SUMS.txt) | Checksums for the installer and named release assets. |

The release also includes named source archives with checksums. Source archives require the setup below; they do not include the Windows runtime.

## Install on Windows

[Download the Windows installer](https://github.com/arcazj/openbexi_discovery/releases/download/v1.2.2/OpenBEXIDiscovery-1.2.2-Windows-x64-Setup.exe), run Setup, then open **OpenBEXI Discovery**. Windows 10/11, 64-bit. Python and SQLite are included; no database server or administrator access is needed.

The app opens in your browser. Use the tray menu to reopen or quit. Private data survives upgrades and uninstall. [Installation help](WINDOWS_INSTALLATION.md)

## What you can do

- **Research:** search evidence, inspect sources, save questions, and compare briefs.
- **Personalize:** describe an area of interest to create an AI-named profile with topics, goals, and an overview. Switch profiles from compact Settings, edit manually, or review AI updates. Delete profiles with confirmation while keeping archived research.
- **Learn and practice:** generate an eight-question quiz for your profile and level, save scores, review answers, and remove attempts from history. Retake saved quizzes offline.
- **Work locally:** create, import, read, edit, and delete documents; browse datasets, write notes, author quizzes, and open or export ZIP libraries without AI.
- **Keep the workspace simple:** automatically search “Last Embryology research” when the local REI workspace launches, manage sources in the tab after Evidence, and use compact item actions and detail panels.
- **Connect data:** connect public or authenticated HTTPS JSON APIs, ask AI to recommend sources for your profile, or browse SQLite read-only.
- **Review before analysis:** import datasets, replace identifiers with consistent labels, and approve a separate working copy for local statistics and AI questions. Original data and private mappings stay outside AI requests and library exports.
- **Control AI:** supply your own API key, choose model/reasoning, and review **By profile and model** usage. Quota notices explain unavailable credits; previously saved local limits remain enforced and can be removed explicitly.

Green identifies source/user content whose upstream AI origin may be unknown. Orange identifies app-generated AI content, with its model recorded. Red signals errors or blocked AI usage.

The centered workspace heading uses golden-ratio header proportions, with a solid gear for Settings. The heading keeps its standard background; the prompt uses restrained contrast to stand out. The orange/green legend sits below the header on one line when space allows. AI answers and previews retain orange highlighting. The REI profile records research goals; it does not add video or Excel processing, local AI, or automatically enforce local-only mode. See [the REI profile guide](documentation/USER_GUIDE.md#start-with-rei).

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
- [AI connection, usage, quizzes, and data privacy](documentation/AI_AND_DATA.md)
- [Architecture, schemas, extensions, and tests](documentation/DEVELOPMENT.md)
- [Community Edition and commercial roadmap](documentation/LICENSING_ROADMAP.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

3D engines, full adaptive tutoring, knowledge graphs, autonomous agents, and account-provider integrations are planned extensions. The [proprietary license](LICENSE) permits personal noncommercial learning, research, and evaluation; commercial use and redistribution require separate written permission. Third-party rights remain separate.
