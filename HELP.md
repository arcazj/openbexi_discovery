# OpenBEXI Discovery 1.2.1 Help


For Discovery 1.2.1 profiles, themes, quizzes, offline archives, SQLite connections, and AI usage, read the [Discovery user guide](documentation/USER_GUIDE.md). The REI workflow below remains available in the default Advanced profile. The settings gear opens **Settings**. Use its **Saved research** section for briefs and **Local library** section for local activities and archives. The header keeps one AI connection/status button, the Settings gear, and **Help (?)** on the right.

[Live demo · V1.2.1](https://arcazj.github.io/openbexi_discovery/) · [Downloads and release notes](https://github.com/arcazj/openbexi_discovery/releases/tag/v1.2.1)

Version 1.2 adds reviewed AI profile updates with rollback, eight-question quizzes with score history, API connections, dataset privacy review, and progress bars for every AI task. The bundled REI/Advanced template includes the reviewed embryology research focus; existing profiles are preserved on upgrade.

## Quick start

Search a topic such as **ovarian aging** or **PCOS**, a human gene such as **BRCA1**, or a chromosome region such as `17:43044295-43170245`. The search type is detected automatically. Open a finding to inspect its source, then start a research brief with the references you want to keep.

## Sources and coverage

The **Sources** tab follows Evidence. Use its source checkboxes, **+ Add source**, and row actions. Open **Source settings** for the per-source limit, **Reset**, and theme/source management. Changing sources requires a new search; the existing coverage report describes the completed search.

- **PubMed:** publications and available abstracts.
- **Ensembl:** human genes, transcripts, and regions, using GRCh38.
- **GWAS Catalog:** reported trait and genetic associations.

Coverage reports the source query, match count when available, retrieved count, and failures or limits. A small result set is not proof that no research exists. Sources can use different search vocabularies; inspect their queries and original records.

## Reading evidence

Open source links to check findings. Study design, population, sample size, and human/animal context are shown when available; missing information remains unknown. Retractions, corrections, and expressions of concern are displayed when the source provides them. A reported association does not establish causation. Genome coordinates are displayed with their assembly and convention.

## Research briefs

Record a question, population, exposure/intervention, outcome, study design, required data, notes, and feasibility uncertainties. Optionally record your deadline, available datasets, and mentor expertise. Review access, sample size, methods, and time with your mentor; the application cannot establish these from publications alone.

Open **Settings > Saved research** to review your briefs. Choose **Back to research** or the OpenBEXI Discovery name to return to search. Saved research stays in this browser on this device. Export JSON for backup and transfer. Import merges new brief IDs, preserves existing briefs, and restores supplied research constraints. Import only trusted workspace files. Export Markdown for mentor review, including references and search provenance. Clearing browser storage removes local saved work, so keep a backup.

## AI assistance

**Settings > Update profile with AI** lets you request changes, review a preview, apply selected fields, and roll back. Searching never changes your profile automatically. Repeating an already-applied request can report no changes.

**Quizzes > Start a quiz** generates eight questions for your level. Each saved quiz has **Start** to retake it without AI and **Delete quiz** to remove it while preserving past scores. Grade locally, review scores and explanations in Quiz history, or remove saved attempts. Every AI task shows a labeled activity bar, elapsed time, and a polite wait message. Use Cancel where available to stop waiting.

For connected data, open **Connections → Connect to an API** or use **Recommend APIs with AI**. Each API row offers **Edit connection**, **Connect/Reconnect**, **Explore API**, and **Delete**. Public presets connect directly; authenticated services support tokens, API keys, or username/password. After retrieving records, review their privacy rules before enabling questions and statistics. **Datasets → Import file → Review privacy** follows the same process for CSV/JSON. Repeated patient names receive consistent labels, credentials are removed, and AI analyzes only an approved working copy. See [API connections and dataset privacy](documentation/USER_GUIDE.md#api-connections).

On Windows 10/11 x64, the [self-contained installer](WINDOWS_INSTALLATION.md) supplies the local backend and opens the browser automatically. Use its tray menu to reopen/quit the app. Private keys live in `%LOCALAPPDATA%\REIResearchExplorer\.env`; installation updates preserve that folder.

AI is optional and runs through the Python backend. Click **Connect AI**, choose **Model** and **Reasoning** (default **GPT-6 Astra / xHigh**), enter your key, then select **Save & connect**. The password field clears after submission; the local backend saves the key and choices in ignored `.env` and checks model access without sending research evidence. No restart is needed. The same status button reopens the dialog, where you can change choices without entering the saved key again. **By profile and model** shows local usage; an **AI tokens unavailable** notice appears when the provider reports exhausted credits or quota.

The local REI workspace searches **Last Embryology research** once at launch. The input stays empty and shows that text as a placeholder; it disappears as soon as you type. Local-only or sensitive mode keeps this manual. The white results area retains its height even with zero records. The workspace omits recent-query chips, research-constraint panels, and tips. The search row contains only Search and, while searching, Cancel. Open Settings → Saved research → New brief to draft a research question. AI runs when you request an explanation, comparison, summary, or analysis.

Saved-material rows include a preview and actions on the right. **Summarize** and **Analyze with AI** open a compact review panel; approve the text before sending it. Dataset analysis uses only a privacy-reviewed working copy. PDF summaries use saved notes. **Edit** is offered where supported, and **Delete** asks for confirmation.

Alternatively, configure `.env` using `.env.example` and restart the backend:

```dotenv
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-6-astra
OPENAI_REASONING_EFFORT=xhigh
```

Keys are stored only on the server. Never embed a key in HTML source, browser storage, exported research, or Git. UI key entry is available only through a local HTTP backend. OpenAI API usage is metered and requires model access and sufficient quota; the connection check verifies key and model access without generating text.

`py -3 serve_frontend.py` starts the full application on port 8765. In IntelliJ, run **OpenBEXI Discovery**, `backend/app.py`, or `serve_frontend.py` and open the URL printed in Run. Use `--browser-only` only for the static demo; that mode needs a separate backend on port 8000 for full features. A custom backend URL in **Help → AI & connection** overrides automatic detection. `.env.example` is a public template.

Use **Explain with AI**, comparison, or saved-item analysis when evidence is available. Suggestions should cite supplied records and identify uncertainty. A suggested gap or novel question is provisional. Exports preserve the evidence identifiers, model, and prompt version for review. Canceling a browser request may not stop a provider request that has already started.

## Demonstration and browser-only use

The [GitHub Pages live demo](https://arcazj.github.io/openbexi_discovery/) runs the standalone frontend, with live PubMed/Ensembl requests where browser access is available, manual research briefs, and exports. It hosts no Python backend. **Run with AI** opens local setup instructions; no key is entered on the public demo.

Demonstration mode is explicitly labeled and uses illustrative material. It is for learning the workflow, not research evidence or AI input. A live search failure never silently switches to demonstration mode.

The HTML works without the AI backend for sources that allow browser requests. Starting the Python backend enables AI and proxied sources from the same standalone page. Serve the HTML over local HTTP; a double-clicked `file://` page cannot access the local AI backend. Documentation files can be opened from Help or directly beside `index.html`.

## 3D views

3D is deferred in the first version because the initial workflows do not supply validated spatial genome data or a task that benefits from 3D. A visualization extension point is reserved. Schematics must be labeled; physical structure claims need suitable spatial evidence.

## Troubleshooting

- **No findings:** inspect the search interpretation, exact source queries, and coverage; try a synonym or broader topic.
- **One source failed:** review the available results and retry later. Limits and timeouts are reported separately from empty results.
- **Backend unavailable:** check the backend URL and startup command in the README. Browse compatible sources or use the explicit demonstration.
- **Windows socket error / busy port:** the standalone launcher tries port 8765 and alternatives, printing the actual URL. Use --port 0 to request an available port. A new port has separate browser storage; import your JSON backup to restore research there. Local HTTP ports can connect to the AI backend.
- **AI unavailable:** use the header status to enter or update a key. If the local backend is unavailable, start it before key entry. Check model access and billing; manual `.env` edits require restart.
- **Saved work missing:** check the browser and device, then restore your JSON backup.

## Licences and project documentation

Read [commercial licensing notes](COMMERCIAL_LICENSING.md), [third-party notices](THIRD_PARTY_NOTICES.md), and the [NCBI copyright and disclaimer notice](https://www.ncbi.nlm.nih.gov/home/about/policies/). Publication text and datasets have source-specific reuse terms. The project's original-code license remains pending owner selection.

The [README](README.md) contains startup instructions. The [implementation prompt](REI_RESEARCH_EXPLORER_PROMPT.md) records the agreed scope and acceptance criteria.
