# OpenBEXI Discovery: build a profile-driven learning and research UI

Evolve the original REI application into **OpenBEXI Discovery**, with the Git repository named `openbexi_discovery` and this mission:

> Make human knowledge accessible to everyone, from the first lesson to the frontiers of scientific discovery.

Use this mission consistently in the project's README, introductory documentation, and appropriate UI introduction or About content. Let it guide clear language and experiences suited to both beginning learners and advanced researchers.

The product vision is **from beginner to discovery**: organize the experience around seven progressive knowledge levels, from foundational concepts to experimental inquiry. Users choose their starting level and can move between levels as their needs change.

Update the existing Research Explorer so users can personalize the page for one or more learning and research themes. Each user profile must store a JSON configuration that determines the page's text, supported panel structure, and theme-specific guidance.

Inspect the existing UI, backend, AI integration, and taxonomy before implementing. Reuse the application's design patterns and working features.

### Scope and shared concepts

A **profile** is a saved learning or research workspace configuration, not a login identity or a grant of access to data. A **theme** is a selection from the research taxonomy. A **level** sets the preferred depth of learning and guidance. An **activity** records a submitted request or meaningful action and its resulting materials. A **connection** is a separately authorized data source referenced by a profile.

Deliver profile management, taxonomy and level selection, JSON-driven rendering, runtime prompt composition, the local library, ZIP support, and the core workspace tabs as functional features. Include document viewing, local dataset browsing, saved quizzes with local grading, notes, and at least one documented read-only database connector. Reuse existing evidence and AI capabilities. Provide a connector extension interface for external accounts; add named providers only when their authentication and data-access behavior are implemented and verified.

Treat new 3D simulation engines, a full adaptive tutor, advanced exercise engines, interactive knowledge graphs, and autonomous research agents as optional extensions. Their configuration hooks and availability states belong in this design, but they must not appear operational until implemented. This distinction defines the initial delivery scope; it does not exclude REI from any implemented enhancement.

Use shared schemas and a capability registry to keep the frontend, Python backend, profile validation, and AI requests consistent. Distinguish a capability that is not implemented from one that is available but needs setup or is temporarily offline. Profile preferences never override actual capability availability or data-access permissions.

## 1. Preserve the existing experience as an REI profile

Capture the existing REI experience in a bundled **REI** template that initializes the active profile at `user_profiles/rei.json`. Preserve its reproductive endocrinology and infertility focus, UI wording, source integrations, search behavior, research constraints, saved briefs, evidence inspection, comparisons, import/export, and AI-assisted workflows.

Preserve the familiar REI page layout, styling, panel order, and initial wording while moving configuration into JSON. Add the Discovery branding, settings icon, theme summary, workspace tabs, Local library access, and the provenance-color corrections specified below as deliberate enhancements. Put profile setup and the level selector in right-side panels. Loading REI at Advanced must not automatically rewrite legacy text or rearrange its panels. Explicit profile edits may change its supported presentation settings; the underlying REI workflows remain available.

Keep these capabilities working through the shared application components and the REI profile's configuration. Inventory the current features before refactoring and use that inventory to verify parity afterward.

Keep **REI as the default profile for both existing and new installations**, at Advanced level. For existing installations, activate REI during the initial migration and retain saved research, preferences, constraints, and AI connection settings. After setup, restore the user's last selected profile rather than resetting it on each launch. Offer General Learning & Research as an optional template for creating another profile.

Apply all enhancements in this specification to the default REI profile: profile settings, theme and level selection, configurable UI content, supported workspace tabs and learning tools, database/account connections, and the local library with offline and ZIP support. Preserve the existing REI capabilities and keep Evidence as its initial workspace tab. Make implemented enhancements accessible from REI without requiring a different profile; connections and optional tools still require their normal setup and user choices.

## 2. Rename the Git project and product

Publish release 1.1 on `master` in the GitHub repository `openbexi_discovery`, preserving the existing Git history. Use `openbexi_discovery` as the sole repository and `origin` remote.

Use **OpenBEXI Discovery** as the product name. Review and update active project references, repository links, documentation, build and package metadata, launchers, and CI or publishing configuration affected by the rename. Keep REI as the specialized profile name. Preserve compatibility with existing user data and configuration paths, or provide an explicit migration where paths must change.

Verify that repository links, installation instructions, builds, and launch commands still work. If repository-host permissions prevent the remote rename, complete the local preparation and report the exact remaining hosting action; do not claim the rename is complete.

## 3. Add profile settings

Add a gear icon immediately after the **AI settings** button. Give it the accessible label and tooltip **Profile settings**.

Clicking it opens a panel on the right where users can:

- Create, select, rename, edit, and delete profiles.
- View and edit the active profile's learning or research goal, experience level, and preferred learning tools, and view its selected themes.
- Edit its UI wording and supported display options through clear form controls.
- Preview changes before saving.

Store each active profile as a separate JSON file under the application's writable `user_profiles/` directory, using a stable profile ID as the filename. Keep an immutable bundled REI template separately and use it to initialize `user_profiles/rei.json` only when missing. Commit templates and schemas; exclude mutable user profiles, runtime settings, credentials, and library data from Git. Never replace an edited profile with a bundled template during normal startup or an upgrade.

Implement persistence through the backend so profiles survive application restarts. Store the active profile ID in local application settings and restore it when the page opens. Confirm deletion of custom profiles and fall back to REI if the active custom profile is deleted. Keep REI available; offer reset to its bundled configuration instead of deletion. Resetting or deleting a profile must retain its saved research and library history, with a profile snapshot identifying archived work. Deleting archived content is a separate explicit action.

Apply preview, schema validation, revision checks, and atomic saves to both manual and AI-assisted edits. Offer save, discard, or cancel when switching profiles with unsaved changes. Associate new work with its originating profile; migrate legacy saved research to REI once, without duplication or loss, and keep it accessible through the existing Saved view and Local library.

## 4. Make the page configurable through JSON

Define and validate a versioned profile schema covering:

- Schema version, profile ID, revision, name, description, and creation/update timestamps. The server manages IDs, revisions, and timestamps.
- The user's learning or research goal.
- The selected experience level as a validated `learning_level` value.
- Preferred learning tools and their supported configuration.
- Selected taxonomy IDs and their source references.
- A short theme title and goal summary.
- UI headings, descriptions, labels, placeholders, example queries, helper text, and default guidance.
- Supported panel visibility, ordering, and field configuration.
- Workspace tab IDs, labels, order, visibility, default selection, and references to available tools or connections. Store connection IDs rather than credentials in profiles.
- Relevant source preferences and context for AI guidance.
- A stable reference to the profile's local archive, using portable relative paths.

Keep configuration separate from user content and transient state. Store actual research-constraint values, notes, quiz attempts, queries, and results in profile-associated workspace data or the library; keep field definitions, labels, and defaults in the profile JSON. Store active tabs, filters, and in-progress search state separately from the declarative profile. Profile edits must not overwrite entered constraint values or saved research.

Use this configuration to personalize all of these areas:

1. The **Find evidence. Shape a question.** header and introductory text.
2. The **Sources / Select evidence** panel.
3. The search panel, including its labels, placeholders, and examples.
4. The **Start with your curiosity** panel and welcome state, including profile-configured workspace tabs.
5. The **Make the next step useful** panel.
6. The **My research constraints (optional)** panel, including field labels and hints.
7. The **Tip** panel.

Use reusable UI components with declarative JSON settings. Application code must implement supported behaviors; JSON selects and configures them. Define the supported panel order, visibility options, field types, and limits in the schema and capability registry. Keep essential navigation and profile recovery accessible. Validate all profile input, including imported files and AI-generated settings, and render text safely. Provide defaults for missing optional values and explicit migrations for older schemas.

Treat profile guidance as the starting content. After searches, generate contextual guidance using the active profile, selected themes, experience level, learning or research goal, permitted constraints, and retrieved evidence when AI is connected and automatic guidance is enabled. Respect existing refresh/cancel behavior and local-only mode. Tie requests and cached guidance to the profile revision and activity context so a late response cannot overwrite another profile's UI. Show local fallback guidance or clearly dated saved guidance when generation is unavailable.

## 5. Add a visible theme selector

Immediately after the **Sources / Select evidence** label in the source strip, add a clickable theme summary showing the active theme title, a one-sentence page goal, and a clear change-theme affordance. Keep it distinct from evidence-source selection.

For the default REI profile, use:

- **Theme:** REI — Reproductive Endocrinology & Infertility
- **Goal:** Explore reproductive health evidence, connect genetic and clinical insights, and develop answerable research questions.
- **Experience level:** Advanced (`learning_level: "advanced"`).

Clicking this area opens a theme-selection panel on the right.

Keep the summary compact and responsive so it does not obscure source controls. Distinguish **Switch profile**, which restores an existing configuration, from **Create profile from themes**, which opens the creation flow.

## 6. Build a searchable, hierarchical theme picker

Use the taxonomy under `themes/` as the source of available choices. Start with `themes/world_research_taxonomy/world_research_overview.json` and follow its relative file references.

The existing hierarchy is **World > Branch > Theme > Discipline > Research Area**. These files describe research categories; define the UI configuration separately in the profile schema. Validate IDs against the taxonomy and resolve file references within its configured root. Map REI to existing applicable taxonomy nodes without inventing IDs. General Learning & Research is a broad template rather than a fabricated taxonomy node; allow it to start with no specific theme selected.

Create an intuitive picker with:

- Search across taxonomy names.
- Expandable categories and breadcrumbs for navigating the hierarchy.
- Selection of one or multiple themes, with optional discipline or research-area refinements.
- Removable selection chips, a selection count, and a clear-selection action.
- A short goal field asking what the user wants to learn or investigate.
- A review step summarizing the selected themes, experience level, preferred learning tools, and goal before profile generation.

Support combinations across branches, such as artificial intelligence and public health. Load choices from the taxonomy files so additions do not require hard-coded picker changes.

## 7. Select a learning and research level

During profile creation, ask users to choose one experience level. Present the selector as **OpenBEXI Discovery — Knowledge Progression**, with the following seven numbered levels, descriptions, and theme-specific examples:

| Step | Level | Purpose | Example activity: quantum physics |
| --- | --- | --- | --- |
| 01 | Foundation | Learn basic concepts, terminology, and principles. | Understand atoms, energy, and light. |
| 02 | Intermediate | Build understanding through lessons and exercises. | Learn wave-particle duality. |
| 03 | Advanced | Solve complex problems and connect concepts. | Solve Schrödinger equations. |
| 04 | Expert | Master specialized domains and technical methods. | Study quantum field theory. |
| 05 | Researcher | Analyze publications, evidence, and open questions. | Analyze recent quantum physics publications. |
| 06 | Frontier | Explore unresolved scientific problems and emerging theories. | Investigate quantum gravity and unresolved questions. |
| 07 | Beyond the Frontier | Formulate original hypotheses, design experiments, and test new ideas. | Develop a testable hypothesis and design a simulation or experiment. |

Map these display labels to stable JSON values in order: `beginner`, `intermediate`, `advanced`, `expert`, `researcher`, `frontier`, and `beyond_frontier`. Keep display labels separate from stored values. Adapt the activity examples to the selected themes; the quantum physics examples illustrate the progression rather than defining activities for every subject. Supply local descriptions and examples when AI is unavailable.

Use a rounded container with a vertical sequence of seven spacious rows, each containing a two-digit step number, a prominent level name, a short description, and a colored accent on the left. Progress from slate and blue through teal to amber and purple using narrow accents only; do not use orange content backgrounds for static level descriptions. Render this as live, responsive UI with accessible single-selection controls, visible keyboard focus, and a clear selected indicator that does not depend on color. This description must be sufficient to implement the selector without needing a separate reference image.

Highlight Advanced for a new profile and the saved level when editing an existing profile. Keep all levels directly selectable without prerequisites or unlock steps, and show the active level in the profile summary. In the selector, show each level's general purpose and a concise example for the chosen themes.

Use the selected level to adjust vocabulary, explanation depth, mathematical detail, prerequisites, exercises, suggested resources, and AI guidance. Treat it as the user's preferred starting point, which they can change through profile settings as their interests or experience develop. Changing only the level updates the existing profile after preview and save; changing the theme selection follows the new-profile flow.

For Frontier and Beyond the Frontier, help users identify open questions, distinguish established findings from hypotheses, and define testable predictions and evaluation methods. Show this explanatory note beneath the progression: **Beyond the Frontier represents experimental inquiry, not a guarantee of scientific discovery. AI-generated hypotheses require independent verification.**

Set the current and default REI profile to Advanced (`learning_level: "advanced"`). Preselect Advanced when creating a new profile, including one based on the optional General Learning & Research template, while allowing the user to choose any level. Preserve the existing REI behavior during migration and allow users to adjust their level later. Restore an explicitly saved level without resetting it to the default.

## 8. Support personalized learning and research tools

Design the profile configuration and UI to support these optional integrations:

- **Personalized AI tutor:** explanations, guided questions, feedback, and next steps adapted to the user's themes, goal, and level.
- **Interactive 3D simulations:** explorable models with adjustable parameters and explanations suited to the selected level.
- **Mathematical exercises:** practice problems with hints, worked solutions, and feedback at an appropriate difficulty.
- **Scientific papers:** discovery, reading support, and evidence-based summaries with source references.
- **Knowledge graphs:** navigation through connected concepts, prerequisites, and supporting evidence.
- **AI research agents:** user-initiated assistance with literature synthesis, research planning, and simulation or experiment design, with traceable sources and reviewable outputs.

Let users select preferred tools during profile creation and edit them later. Recommend tools based on the selected themes and level. Store these preferences in the profile JSON and use them to configure supported panels and actions.

Treat these integrations as an extensible platform direction. Reuse working capabilities now, and distinguish available tools from planned integrations. Enable a tool only when its implementation is available; a profile or AI-generated configuration alone must not make an unsupported simulation, exercise engine, or research agent appear functional.

## 9. Create new profiles with AI assistance

Applying a changed set of taxonomy themes or refinements must create a new profile. Browsing choices or reselecting the existing set does not create one. Guide the user through selecting themes, choosing an experience level and preferred tools, and entering a profile name and goal. For a broad profile, offer the General Learning & Research template. Let users explicitly request an AI-assisted draft using the existing AI integration, or continue with a local template. Generating the draft must use the selected context and supported UI schema without requiring database contents or unrelated library history.

The AI should propose coherent wording, examples, constraints, guidance, and a suitable arrangement of supported panels for the selected level and tools. For multiple themes, produce one integrated learning or research experience.

Show an editable preview before saving. Validate the draft, save the new profile under `user_profiles/`, and activate it only after a successful save. Canceling leaves the current profile active. Selecting an existing profile restores its saved configuration without creating another profile or regenerating it. Creating a new profile must not silently copy sensitive datasets, grant connection access, or move historical work from the original profile.

If AI is unavailable or generation fails, offer a valid template-based draft that the user can edit and save. Display clear loading, validation, and error states.

Source preferences must reference implemented search integrations. A new research theme must not imply that an unsupported evidence source is available; explain source coverage when relevant.

## 10. Add a local knowledge archive and ZIP support

Create a configurable local directory, named `discovery_library/` by default, where the application preserves the user's learning and research history. Make it a persistent knowledge library that works through the local Python server without an AI connection. Keep user-generated library contents outside Git tracking.

Organize the library by profile and activity, using stable IDs and timestamps. Use a structure such as:

```text
discovery_library/
  manifest.json
  profiles/
    <profile_id>/
      profile.json
      history.jsonl
      activities/
        <timestamp>_<activity_id>/
          activity.json
          requests.json
          prompts.json
          responses.json
          data/
          documents/
          notes/
          quizzes/
          assets/
  exports/
    <archive_name>.zip
```

Keep `user_profiles/` as the authoritative location for active profile configurations. The library's `profile.json` is a portable snapshot; activity records must retain the profile revision, themes, and learning level used at the time. Use filesystem-safe UTC timestamps and relative artifact paths. Maintain durable activity IDs and versioned manifests; indexes are derived data that can be rebuilt from stored records. Let tabs, Saved research, and Local library reference the same underlying artifacts instead of creating competing copies.

### Preserve activity history and materials

- Automatically record permitted submitted user requests, search queries, prompts sent to AI, returned responses, and meaningful actions such as saving notes, creating a quiz, or completing an exercise. Apply the credential and sensitive-data rules before writing any log, cache, or archive. Record submission and completion events, including failures or cancellations, without recording every keystroke.
- Save associated data, search-result snapshots, PDFs, Markdown documents, notes, quiz definitions, answers, attempts, scores, and supported simulation or knowledge-graph assets. Include uploaded files and permitted downloads; retain source links and metadata when the full material cannot be stored locally.
- Link each activity to its inputs, outputs, source references, timestamps, status, and originating profile. Identify AI-produced content and record available model and generation metadata. Preserve earlier versions when users revise saved work.
- Store actual submitted prompts and requests where permitted, while excluding API keys, authentication headers, credentials, and private server configuration from history and exports. Mark omitted or redacted content explicitly so the record does not claim to be a complete replayable request.
- Make save failures visible and provide a retry action so the interface does not claim an activity is archived when persistence failed.

### Work without an AI connection

Add a **Local library** entry with browsing and local search by text, profile, theme, level, date, and content type. Users must be able to open saved PDFs and Markdown, inspect past requests and responses, revisit evidence, edit notes, and resume saved activities without connecting to AI. Search metadata and stored text locally; PDF full-text search requires a locally available extracted-text representation. Keep PDFs readable when extraction is unavailable, and do not imply that scanned pages have searchable text without an implemented OCR capability.

Allow stored quizzes to run locally and grade them when a saved answer key or supported local grading rule is available. Mark activities that require fresh AI evaluation accordingly. Saved interactive materials must work offline only when their required assets and runtime support are available locally.

Support an explicit local-only mode that uses saved content and makes no AI or external-source requests. Bundle the UI assets needed for that mode, suppress remote embeds and background connection checks, and keep the local Python server running. Offline use means the browser and local server work without external connectivity; it does not mean opening the application without its backend. Without AI but with internet access, ordinary supported online searches may still be available outside local-only mode. Clearly identify archived results and their capture dates; retrieving a saved response must not present it as newly generated.

Users can copy a past request into a new draft. Sending it again to AI requires an explicit action and an available connection. Browsing or opening an archive must not replay its recorded actions.

### Create and read portable ZIP archives

Provide ZIP export for a selected activity, a profile's library, or the entire library. Include a versioned manifest, the relevant profile snapshots and history, referenced permitted files, relative paths, file sizes, and checksums. An activity export must not include unrelated profile history. Apply sensitive-data export choices before creating the archive and mark excluded dependencies in the manifest. Exclude the `exports/` directory itself to prevent recursive archive inclusion. Export a consistent snapshot, keep the working library available afterward, and report success only after the ZIP is complete.

Extend the Python server to open and read these ZIP archives directly: list their contents through the manifest, search stored text and metadata, and serve supported documents and quiz data to the UI without requiring manual extraction or AI access. Treat an opened ZIP as read-only; offer import into the working library before editing or resuming an activity that writes new results.

Validate the manifest and archive entries before reading or importing, including when streaming entries directly. Reject unsafe or duplicate paths, links or entries that escape the library directory, and archives that exceed configured entry-count or decompressed-size limits. Enforce limits while reading rather than trusting declared sizes. Verify checksums and report corrupt or unsupported archives clearly. Render stored content safely and never execute code merely because it appears in an archive. Supported interactive content must use trusted application components with validated data.

Preview imports and resolve duplicate IDs explicitly: skip identical items or import conflicting items as separate copies with updated references. Import transactionally so a failure cannot leave partially registered content. Never silently overwrite existing profiles or history, especially the default REI profile, and do not automatically activate an imported profile. Include the theme metadata and permitted local assets needed to browse exported content on another installation without relying on the original machine's absolute paths. Preserve unknown historical taxonomy references for viewing; require an explicit mapping to current taxonomy nodes before activating a profile that uses them. Importing content must not install or execute bundled prompts, scripts, or plugins.

## 11. Add profile-specific workspace tabs

Extend the **Start with your curiosity** panel into a tabbed workspace. Keep its heading and welcome text configurable, and retain the existing evidence/results experience as the initial REI tab. Let profiles determine which additional tabs appear and let users customize them through profile settings.

Use a small set of reusable tab types:

| Tab | Purpose |
| --- | --- |
| Evidence | Show search results, source coverage, and evidence details using the existing workflow. |
| Documents | Import, browse, and read PDFs, Markdown, and other supported local or archived documents. |
| Datasets | Explore uploaded or connected data, inspect fields, apply supported filters, and review provenance. |
| Connections | Configure supported database and external-account integrations, permissions, connection status, and synchronization. |
| Quizzes | Open saved quizzes, practice exercises, and review attempts appropriate to the profile's themes and level. |
| Notes | Maintain research notes, learning summaries, and links to supporting materials. |

Database and account connections supply content to the Documents and Datasets tabs; their setup belongs in Connections. Give connected datasets recognizable names and show where they came from. An account integration must identify its provider, available data, and authorized access rather than presenting a generic promise to connect to any account.

Show only tabs backed by implemented capabilities. The core delivery must implement the six tab types above; their visibility is profile-configurable, and Evidence remains REI's initial selection. A Connections tab may offer setup before a connection exists. Show unavailable optional extensions in settings with an explanation rather than as empty functional tabs. Selecting another tab must preserve the current search, filters, selected records, and unsaved drafts. Use accessible tab navigation and a compact layout on narrow screens. Make Local library the cross-profile view over these same stored materials.

### REI example: connect and explore a research dataset

An REI user opens Connections, selects an implemented database connector, and connects to a database they are authorized to access. They select permitted tables or views containing genetic, participant, patient, or clinical-outcome data. The Datasets tab shows the schema and a limited preview, supports configured field mapping and filters, and lets the user relate selected data to literature and saved research questions.

Implement connectors through the Python backend with read-only access, bounded queries, pagination, and timeouts. Offer structured browsing and filtering as the initial workflow; database writes and unrestricted AI-generated SQL are outside this specification. Parameterize filter values and validate selected tables and fields against the authorized schema. Document and test at least one supported database type end to end using a synthetic REI dataset. Keep credentials in private server-side storage; never embed them in profile JSON, browser responses, activity logs, or ZIP archives. AI-generated configuration cannot grant access or execute database queries by itself.

Provide an explicit field-selection and data-use step for sensitive datasets. Keep patient records and identifying genetic or account data out of AI requests, routine activity logs, and portable archives by default. Before any supported AI analysis or export involving selected sensitive data, show the exact fields and records involved, the destination, and any transformations, and require explicit user authorization. Authorization to view data is distinct from authorization to send it to AI, retain a local snapshot, or export it. Apply exclusions to derived responses as well as raw inputs. Do not describe data as anonymous solely because names were removed. Do not rely on an AI classifier to detect every sensitive value; enforce the selected source and field policies in application code.

Record connection activity as metadata, such as the connection ID, operation, selected dataset, timestamp, and outcome, without automatically copying database rows or sensitive query values. Apply these rules ahead of the general archive-history requirements. The same exclusions apply to stored request and response bodies containing sensitive data.

Apply the same data-use controls to sensitive uploaded documents, imported archives, and manually entered content. Treat a profile as an organizational boundary, not as security isolation between people. Preserve existing application access protections; a multi-user deployment would require separate authentication and authorization design.

Let users explicitly save permitted dataset snapshots for offline work. Display their capture time and source, and distinguish them from a live connection. ZIP exports may include approved snapshots and non-secret provenance, but must omit credentials and require reconnection on another installation. Users can disconnect a source and separately choose whether to retain or delete its local snapshots.

## 12. Compose AI requests from reusable prompt templates

Create a versioned library under `prompts/runtime/` for the instructions the application sends to AI. Keep runtime templates separate from implementation specifications such as this document. Suggested organization:

```text
prompts/runtime/
  manifest.json
  base.md
  ui_guidelines.md
  profile_rules.md
  tasks/
    answer.md
    research_guidance.md
    create_profile.md
    update_profile.md
    create_quiz.md
```

Define the platform mission, evidence standards, and common response rules in `base.md`. Define supported rendering conventions in `ui_guidelines.md` and profile-editing constraints in `profile_rules.md`. Give each task a focused template, an expected output schema, and explicit allowed operations. The manifest must identify template versions and supported task types. Reuse existing working AI instructions where applicable.

### Assemble coherent, task-specific requests

Implement a shared prompt composer in the Python backend. For each supported AI action, combine:

1. The common application instructions and relevant task template.
2. UI and profile rules only when the task needs them.
3. The active profile's relevant configuration, revision, themes, goal, and selected level.
4. The available source, tool, and UI-component capabilities and the task's output schema.
5. Relevant recent context, selected evidence, and permitted local-library content.
6. The user's current request, preserved as a distinct user message.

Use structured messages with clear roles and boundaries. Treat documents, database values, archived prompts, and retrieved text as reference data; their contents cannot override application rules or grant permissions. Include only task-relevant context within a defined size budget, and never silently truncate the current request. Apply the sensitive-data and credential exclusions before sending context to AI.

Route requests according to the action the user initiated. Answering a question or creating a quiz should return that content without changing the profile. A request to personalize the UI may propose configuration changes. Theme changes must still use the new-profile flow. Ask a focused clarification when the intended change is ambiguous.

### Validate AI output before rendering or saving

Use structured output matching the task schema where supported, and validate every response on the server. For profile edits, request a minimal set of changes with the profile ID, base revision, and a short explanation. Restrict editable fields to those permitted for the action; AI output cannot modify credentials, access permissions, usage limits, storage paths, or application code.

Check both the proposed changes and the resulting full profile against the schema and capability registry. Reject unknown components, attempts to activate unimplemented tools, invalid taxonomy references, and stale revisions. A configured connection that is temporarily offline remains a valid reference but cannot run. Preserve unrelated settings and existing REI capabilities. For profile creation, validate the AI-editable draft, assign server-managed IDs, revision, and timestamps, then validate the complete profile before saving.

Render proposed UI changes through the existing component system in a preview. Follow the profile preview-and-save flow, save valid changes atomically, and retain the previous revision for undo. A failed, canceled, or outdated AI response must leave the active profile intact. Use a bounded retry for recoverable output-format errors, then show a useful error or a valid local fallback.

Keep layout, responsive behavior, accessibility, and component rendering in application code. AI proposes supported content and configuration; prompt wording alone cannot guarantee correct rendering. Validate the rendered result through appropriate UI checks.

### Keep requests traceable and usable offline

Record the task type, template versions, profile revision, permitted assembled request, response, validation outcome, and applied changes in the local activity history, subject to its sensitive-data exclusions. Preserve the distinction between the user's original request and the application instructions added to it.

Without AI access, continue rendering saved profiles, opening archived responses, and editing supported fields through local forms. Templates do not imply offline AI generation. Test request composition, task boundaries, invalid output handling, stale edits, and preservation of unrelated profile fields.

## 13. Add AI usage, estimated cost, and spending limits

Add a **Usage & budget** section inside the existing **AI settings** panel. Make it available to every profile, including the default REI profile, and keep it accessible when AI requests are blocked.

### Show usage and estimated cost

Display the selected accounting period, AI request count, input tokens, output tokens, total tokens, estimated cost in USD, and remaining allowance. Show completed usage separately from reservations for requests still in progress. Provide a breakdown by model and profile and show when the totals were last updated.

Use provider-reported usage when available. Account for cached input, reasoning tokens, and other billable categories according to the model's usage definitions without double-counting categories already included in totals. Calculate estimated cost from a versioned pricing configuration that records its source and verification date; use the applicable rates for each recorded request. Mark uncertain usage or cost as estimated or unavailable rather than reporting it as zero.

Explain that these totals cover requests made through this local application and may differ from the provider's final bill. They do not include activity from other applications using the same account or API key.

### Set limits with accessible controls

Provide separate **Token limit** and **Estimated cost limit (USD)** controls. Each control must have an enable toggle, a slider, and a synchronized numeric input for exact values, with visible units and validation. Let users enable either limit or both; when both are enabled, the first exhausted allowance blocks AI use. An enabled limit of zero blocks requests, while a disabled limit is clearly labeled as unlimited.

Offer daily, monthly, and cumulative-since-enabled accounting periods, with monthly selected initially. Show the timezone and exact period boundaries; use the same period for both limits. Do not silently impose an arbitrary budget amount on existing installations: show limits as not configured until the user saves them.

Store budgets and the usage ledger in private local application settings, independently of profiles. Apply the budget across all profiles, models, and API keys used by this installation. Switching profiles or keys, restarting the server, resetting REI, or importing a ZIP must not reset usage or bypass limits. Preserve historical usage when limits change and exclude the live budget ledger and enforcement settings from portable profile imports.

### Enforce limits before sending requests

Implement one budget gate in the Python backend for every outgoing AI generation request, including automatic guidance, manual requests, profile generation, retries, and any implemented tutor or agent calls. Frontend indicators alone are insufficient.

Before dispatch, atomically reserve an allowance using the assembled input size and a bounded maximum output, including applicable tool charges. Account for concurrent requests against the same remaining allowance. If the planned request cannot fit within an enabled limit, block it before sending and explain that the remaining budget is insufficient. If a reliable reservation cannot be calculated for an enabled limit, block the request with a clear reason rather than allowing unbounded usage.

Reconcile reservations with reported usage after completion and persist the result. Canceled or failed requests may still consume tokens; retain an estimated reservation when final usage is unknown until it can be reconciled. Never reset uncertain usage to zero merely because a request failed.

When a limit is reached, stop new AI requests, retries, queued generation, and automatic AI connection attempts or polling. Cancel active generation where supported, while accounting for any usage already incurred. Keep credentials saved and preserve normal offline, library, and non-AI functionality. This is an application-side estimated budget control, not a guarantee that the provider's final charges cannot exceed the estimate.

### Warn the user and explain recovery

At the limit, give the **AI settings** button a persistent red warning style and badge, with visible text such as **AI paused — usage limit reached**. Also update the AI connection status so it does not misleadingly show AI as ready. Include a text/icon indicator and an accessible status announcement; do not rely on color alone.

Opening AI settings must identify the reached limit, used and remaining amounts, and the next period reset if applicable. Use a distinct explanation when a particular request exceeds the remaining allowance but the limit has not yet been reached. The red blocked state remains while no further generation fits the configured allowance.

Allow the user to raise or explicitly disable a limit, or wait for the next accounting period. Resume availability only when every enabled limit permits it; cumulative limits do not reset automatically. Do not replay blocked prompts or queued actions automatically after recovery. Ordinary future actions and automatic guidance triggered by a new search may proceed under the existing AI preferences.

## 14. Use consistent colors to identify content provenance

Apply one provenance-color convention across REI and every other profile, including evidence cards, documents, guidance, quizzes, previews, and archived materials:

| Presentation | Meaning | Examples |
| --- | --- | --- |
| Green source styling: green text/accent labels and a light green content background where appropriate | Source or user-provided content that the application did not generate with AI, or whose AI origin is unverified | PubMed records and abstracts, imported documents, dataset excerpts, manually written notes |
| Orange content background with readable contrasting text and an AI label | Content generated or rewritten through the application's configured AI model for that generation | AI summaries, next steps, tips, generated quizzes, and AI-drafted profile wording |

Green must not certify that content is human-authored, accurate, or free of upstream AI involvement. Use provenance labels such as **Source: PubMed**, **User-provided**, or **Origin unverified**. Orange identifies known application AI generation, not a quality rating.

Change the PubMed source chip and unmodified PubMed result-card backgrounds to the green source palette. Remove orange styling applied merely because the source is PubMed. If an AI summary appears inside a PubMed result, give only that generated subsection the orange background and AI label; keep the original abstract and citation visibly separate.

Attach provenance metadata to content or individual blocks: origin type, source reference where relevant, generating provider/model when known, generation time, and whether a user subsequently edited AI output. Keep that metadata through saves, profile changes, library browsing, and ZIP round trips. User editing must retain an **AI-assisted, user-edited** label for content derived from AI.

The model shown on an orange block is the model that generated that block. Changing the currently selected model must not relabel old output or turn it green. Cached or archived AI output remains orange with its original model/date and saved-content status. Imported content without reliable generation metadata uses **Origin unverified**, rather than attributing it to the active model.

Apply color at the smallest practical content block when source material and AI output are mixed. Ordinary application controls and static UI text can retain neutral styling. In profile previews, identify AI-drafted wording as generated; fixed template labels do not become AI content merely because AI selected their layout.

Add a concise legend explaining green/source-or-unverified and orange/application-AI content. Use shared design tokens, accessible contrast, and text/icon labels alongside color. Keep red reserved for errors and blocking alerts such as the AI usage limit. Connection status and level accents must remain visually distinct from content-provenance backgrounds. Profiles and AI-generated configuration cannot override these meanings.

## 15. Document the proposed licensing and commercial architecture

Position **OpenBEXI Discovery** as the product brand for a proposed open-source Community Edition and optional commercial offerings. Capture the architecture below in project documentation as a proposal pending ownership, dependency, and licensing review:

| Offering | Proposed scope | Proposed licensing approach |
| --- | --- | --- |
| Open-source Community Edition | Research taxonomy, basic explorer, community tools, and public API interfaces | Consider AGPLv3 or another suitable open-source license after reviewing ownership and dependencies |
| Commercial offerings | Managed AI agents, advanced tutoring, institutional administration, and private deployments | Appropriate SaaS terms or a commercial software license, subject to review of the actual component relationships |
| Subscription and enterprise services | Monthly subscriptions, annual institutional contracts, and professional services | Agreements appropriate to the service and deployment model |

Keep the local REI capabilities and the core enhancements required by this specification available in the Community Edition design. New managed or institutional services are a separate commercial roadmap; do not introduce subscriptions, paywalls, billing, or entitlement checks into the current implementation solely because this architecture is documented. Public API interfaces do not imply public access to private user data or unrestricted rights to third-party content.

Document component boundaries and dependencies. Do not assume that naming a module commercial, placing it in a separate directory, or offering it as a service resolves license compatibility. Preserve existing license notices while the licensing decision is pending; selecting or replacing license text requires a verified decision about rights and compatibility.

Before commercialization, record these preparation tasks:

1. Confirm ownership and contributor rights for original code, taxonomy, and other assets; audit third-party code, data, and content rights.
2. Select the Community Edition license and review the boundaries and compatibility of commercial modules, including any proposed dual licensing.
3. Prepare the applicable commercial EULA, SaaS Terms of Service, Privacy Policy, and enterprise agreements.
4. Establish the business entity and check relevant registration, tax, and permit requirements for the intended operating locations.
5. Conduct a trademark search for **OpenBEXI Discovery** before substantial branding investment.
6. Plan the initial commercial launch for adult learners and researchers. Add school or children's accounts only after their required safeguards and account workflows are designed; a Foundation learning level does not imply a child's account.

Have the proposed structure and final licensing documents reviewed by an appropriate software/IP licensing professional before publication. Describe an initial launch with a Community Edition and a paid hosted offering, followed by institution-specific or enterprise licensing when demand supports it. Treat these as planning deliverables, separate from completion of the local application features.

## 16. Implementation sequence and deliverables

Implement in reviewable stages, keeping the application usable throughout:

1. Inventory legacy behavior, establish schemas and the capability registry, and add recoverable migration to the default REI profile.
2. Build profile settings, theme and level selection, declarative rendering, provenance metadata/color rules, and the core tab framework while preserving REI workflows.
3. Implement shared artifact persistence, document/dataset/quiz/note workflows, local-only operation, and ZIP export/read/import.
4. Add and verify the first read-only database connector and the data-use controls before using connected data in AI requests or exports.
5. Integrate versioned runtime prompts, structured task outputs, validated AI-assisted profile editing, and server-enforced usage/cost budgets before enabling new AI workflows.
6. Complete product branding and repository migration, document the proposed licensing architecture and pending commercialization reviews, and finish end-to-end verification. Report any hosting action that remains blocked separately from completed local work.

Deliver the implementation, bundled REI and general templates, versioned schemas, runtime prompt library, migrations, focused automated checks, and setup/backup/extension documentation. State which connector and optional capabilities are implemented. Do not count an empty tab, simulated connection, or placeholder integration as a completed feature.

Keep release 1.1 fully deliverable through the Windows installer. Bundle the Python runtime, SQLite support, frontend assets, profile templates, taxonomy, runtime prompts, schemas, and documentation. End users must not need Python, Node.js, or a separately installed database server for the local SQLite workflows. Preserve private data across upgrades and uninstall, and smoke-test the installed application, including profile creation, SQLite access, offline library use, and ZIP round trips.

## 17. Acceptance criteria

### REI compatibility and profile lifecycle

- New installations and the initial legacy migration use REI at Advanced. The baseline REI layout, wording, source integrations, Saved workflows, and AI behavior pass the legacy feature inventory with the specified enhancements added.
- Migration retains saved work, constraints, preferences, and AI configuration without duplication. Later startups restore the selected profile and level without rewriting them.
- The gear icon opens the right-side settings panel. Create, preview, save, edit, switch, reset, and custom-profile deletion persist across restarts. Reset/delete retains historical work; failed or conflicting saves preserve the last valid configuration.
- Changed theme selections create a new profile only on save; browsing, canceling, and switching to existing profiles do not. Ordinary edits to level, wording, goal, or tool preferences update the current profile.

### Configurable UI and learning experience

- All seven specified UI areas render from the active profile configuration, with supported changes visible in preview and no loss of entered data.
- The theme summary opens a searchable taxonomy picker supporting multiple themes and refinements. General Learning & Research works as an optional broad template without fabricated taxonomy IDs.
- The numbered Knowledge Progression selector includes all seven display labels, stable stored values, descriptions, relevant examples, and the experimental-inquiry note. New profiles preselect Advanced; existing profiles show their saved level.
- Evidence, Documents, Datasets, Connections, Quizzes, and Notes have working core flows. REI initially selects Evidence; tab switching retains state. Optional tools are accurately labeled by availability and cannot be activated through profile JSON alone.
- Keyboard navigation, focus handling, drawer dismissal, text rendering, and narrow-screen layouts work for the new controls and tabs.
- PubMed source chips and unmodified result cards use the green source palette. Application-generated content uses orange backgrounds with its actual generating model and provenance labels; mixed content keeps source and generated blocks distinguishable.
- The provenance legend avoids claiming that green content is verified human authorship. Switching models, editing AI output, and ZIP round trips preserve provenance, and red usage-limit alerts remain visually distinct.

### Library, offline use, and portability

- Permitted requests, prompts, results, and materials are linked to the originating activity and profile revision. Secrets and excluded sensitive content never enter routine logs or exports.
- With external network access disabled and the local server running, users can manage profiles through local templates, browse and search saved content, read documents, edit notes, and complete quizzes with local grading. Background checks and embedded assets make no external requests in local-only mode.
- Activity, profile, and full-library ZIP exports open directly through the Python server and import on another installation with permitted files, history, and references intact. Single-activity export excludes unrelated history.
- Corrupt, unsafe, oversized, or conflicting archives produce clear outcomes without partial imports, overwritten profiles, executed content, or leaked credentials. Imported connections require setup and authorization before use.

### Data connections and AI behavior

- At least one documented database connector passes an end-to-end REI example using synthetic data, authorized schema selection, bounded read-only filtering, and explicit offline snapshots. External-account providers are listed as supported only when verified.
- Viewing, AI transmission, local retention, and export of sensitive data have distinct controls. These controls apply to connected, uploaded, imported, and derived content and take precedence over automatic history capture.
- Supported AI actions use the shared prompt composer and versioned task templates. The original user request remains distinct from application instructions and reference material; task-specific context respects data-use rules.
- Questions and content-generation tasks do not mutate profiles. Requested profile changes are minimal, validated, previewed, revision-checked, saved atomically, and reversible. Invalid output and late responses cannot overwrite a different or newer profile.
- AI disconnection or generation failure leaves the current workspace usable with local templates and stored content, and never presents cached output as newly generated.

### AI usage and budget enforcement

- AI settings show usage, estimated USD cost, the accounting period, remaining allowance, pending reservations, and model/profile breakdowns. Estimates and unknown values are identified accurately.
- Token and cost sliders remain synchronized with numeric inputs. Either or both limits can be enabled, zero blocks AI, and disabling one limit cannot bypass the other.
- Every AI generation path uses the backend budget gate. Concurrent requests, retries, unknown final usage, period rollover, and server restarts preserve correct accounting without duplicate charges in the local ledger.
- Reaching a limit stops further AI activity and displays a persistent accessible red warning on the AI settings button. Local features remain usable, and recovery never silently replays blocked actions.
- Profile changes, API-key changes, archive imports, and AI-generated configuration cannot alter or bypass the application budget. Tests cover both exhausted limits and requests that exceed the remaining allowance.

### Delivery verification

- OpenBEXI Discovery branding and the exact mission appear in the appropriate UI and documentation. The Git rename preserves history and updates affected references; any blocked hosting step is reported as incomplete.
- Documentation includes the proposed Community Edition/commercial architecture and the six commercialization preparation tasks. Proposed licenses are clearly marked as pending review; existing notices are retained, and no unrequested billing or paywall implementation is introduced.
- Run focused automated checks for the behaviors above, plus rendering and keyboard checks for the changed UI. Use synthetic fixtures for sensitive-data scenarios. Document profile/archive schemas, supported connectors, migration and recovery, backup/restore, and extension points.
