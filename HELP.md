# REI Research Explorer Help


For Discovery 1.1 profiles, themes, offline archives, SQLite connections, and AI budgets, read the [Discovery user guide](documentation/USER_GUIDE.md). The REI workflow below remains available in the default Advanced profile.

## Quick start

Search a topic such as **ovarian aging** or **PCOS**, a human gene such as **BRCA1**, or a chromosome region such as `17:43044295-43170245`. Check the interpreted search type and change it if necessary. Open a finding to inspect its source, then start a research brief with the references you want to keep.

## Sources and coverage

The **Sources** row sits above search and stays visible while browsing results. Use its checkboxes, per-source limit, and **Reset** control. Changing sources requires a new search; the existing coverage report describes the completed search.

- **PubMed:** publications and available abstracts.
- **Ensembl:** human genes, transcripts, and regions, using GRCh38.
- **GWAS Catalog:** reported trait and genetic associations.

Coverage reports the source query, match count when available, retrieved count, and failures or limits. A small result set is not proof that no research exists. Sources can use different search vocabularies; inspect their queries and original records.

## Reading evidence

Open source links to check findings. Study design, population, sample size, and human/animal context are shown when available; missing information remains unknown. Retractions, corrections, and expressions of concern are displayed when the source provides them. A reported association does not establish causation. Genome coordinates are displayed with their assembly and convention.

## Research briefs

Record a question, population, exposure/intervention, outcome, study design, required data, notes, and feasibility uncertainties. Optionally record your deadline, available datasets, and mentor expertise. Review access, sample size, methods, and time with your mentor; the application cannot establish these from publications alone.

Saved research stays in this browser on this device. Export JSON for backup and transfer. Import merges new brief IDs, preserves existing briefs, and restores supplied research constraints. Import only trusted workspace files. Export Markdown for mentor review, including references and search provenance. Clearing browser storage removes local saved work, so keep a backup.

## AI assistance

On Windows 10/11 x64, the [self-contained installer](WINDOWS_INSTALLATION.md) supplies the local backend and opens the browser automatically. Use its tray menu to reopen/quit the app. Private keys live in `%LOCALAPPDATA%\REIResearchExplorer\.env`; installation updates preserve that folder.

AI is optional and runs through the Python backend. The compact header shows verified access, missing credentials, and errors. Click **Connect AI**, then **Save key & connect**. The password field clears after submission; the local backend saves the key in ignored `.env` and checks model access without sending research evidence. No restart is needed. **AI settings** opens connection settings on the right; tap the short mobile status for full model details.

After each completed live search, **Make the next step useful** and **Tip** use AI to offer one short next step and one contextual tip. The request contains up to 20 retrieved records, source coverage, research constraints, and up to three saved questions. Guidance is cached for the session until that context changes; it is not generated on every keystroke. **Refresh suggestions** requests another response; turn automatic guidance off in **AI settings** to use manual refresh only.

Open **Why this suggestion?** to review supporting source records and the model/date. **Use refined query** searches the proposed terms. **Save proposed question** opens a brief for review. **Add next step to a brief** lets you choose a saved brief and review the added note before saving. Saved AI material retains its evidence and provenance. Failed, canceled, empty, example, and browser-only states show labeled fallback guidance; browsing and saved work remain available.

Alternatively, configure `.env` using `.env.example` and restart the backend:

```dotenv
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-6.1-sol
```

Keys are stored only on the server. Never embed a key in HTML source, browser storage, exported research, or Git. UI key entry is available only through a local HTTP backend. OpenAI API usage is metered and requires model access and sufficient quota; the connection check verifies key and model access without generating text.

`py -3 serve_frontend.py` starts the full application on port 8765. In IntelliJ, run **OpenBEXI Discovery**, `backend/app.py`, or `serve_frontend.py` and open the URL printed in Run. Use `--browser-only` only for the static demo; that mode needs a separate backend on port 8000 for full features. A custom backend URL in **Help → AI & connection** overrides automatic detection. `.env.example` is a public template.

Use **Explain**, question generation, or comparison when evidence is available. Suggestions should cite supplied records and identify uncertainty. A suggested gap or novel question is provisional. Exports preserve the evidence identifiers, model, and prompt version for review. Canceling a browser request may not stop a provider request that has already started.

## Demonstration and browser-only use

The [GitHub Pages live demo](https://arcazj.github.io/openbexi_REI/) runs the standalone frontend, with live PubMed/Ensembl requests where browser access is available, manual research briefs, and exports. It hosts no Python backend. **Run with AI** opens local setup instructions; no key is entered on the public demo.

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
