# OpenBEXI Discovery v1.2.2

Version 1.2.2 includes broad and source-specific search, compact profile settings, multiple AI providers, and dated token usage. This update also adds explicit result-verification, warranty, and liability notices.

## Profiles and AI connections

- Compact Settings offers REI, Cosmologie, and custom profiles. Selecting a profile opens its workspace and preserves that selection across restarts.
- **Create new profile** asks for a field or area of interest. AI chooses a suitable name and generates an overview, topics, goals, and workspace text; meaningless requests are rejected. AI-generated overviews retain orange attribution. Profile deletion requires confirmation and preserves archived research.
- Profile creation and search offer reasoning choices up to **Ultra** (`max`) where supported. Choices available for other providers reflect their integration limits.
- **Connect AI** defaults to OpenAI / GPT-6 Astra and also offers Anthropic, Google Gemini, DeepSeek, OpenRouter, and custom OpenAI-compatible providers. Each provider retains its own key and settings. Custom endpoints require HTTPS and a model with Chat Completions JSON support.
- AI analysis, profile generation, and scientific-source query planning use the selected provider. Overall and topic web searches currently require OpenAI; no other provider's key is used as a fallback.
- Token usage is grouped by **Date (UTC)**, profile, and model, newest first. Unknown non-OpenAI pricing remains explicit, and missing usage retains a conservative reservation.

## Search

- **Overall Search** uses GPT-6 Astra and live web search, independently of checked sources. Answers show clickable provider citations, their model and reasoning level; actual search coverage stays in the saved result.
- **Specific Search** uses GPT-6 Astra to prepare precise queries for checked PubMed, Ensembl and GWAS sources, then retrieves records from those services. Generated plans cannot add unselected sources. Leaving everything unchecked performs an overall search.
- Each green split button has its own reasoning choice, defaulting to **Medium**, with **Low**, **High**, **xHigh**, and **Ultra** where supported. Changing a choice does not run a search. These choices are saved per profile; other AI tools keep their connection settings.
- The search box has a modestly taller input, clear contrast and a visible focus state. Overall Search sits on the right, with Specific Search directly below it beside coverage controls. Request privacy sits directly beneath Specific Search.
- Select all / Clear selection, hover and keyboard captions, touch help, a loading state, cancellation, and a broad-search action for empty specific results support refinement. The layout stacks naturally on mobile.
- The results toolbar keeps the workspace tabs, **Source evidence**, and a right-aligned **10 / 20 / 50 records** selector. Routine notices, coverage badges, scope summaries and evidence-type filters are removed. The selector changes visible results without another AI request; searches retrieve up to 50 records per selected source.
- Source failures remain distinct from zero matches. Requests, selections and reasoning remain available after a search. Broad AI answers retain separate source links and AI attribution.

## Compatibility and privacy

OpenAI searches use `gpt-6-astra`; other providers use their selected model for scientific-source query planning. Provider errors do not substitute another model or provider. Overall Search and topic web searches require a configured OpenAI key with Astra and web-search access. Without AI, Specific Search can still retrieve checked scientific sources directly. The public demo supports direct Specific Search only.

Sensitive searches require review before being sent. Local-only mode blocks external search. Web-search tool calls and retrieved input tokens are included in local usage estimates. Cancellation stops waiting and discards the pending result; work already accepted by a provider may still incur usage.

The automatic REI launch search remains a direct source request without AI spending. The prompt field stays empty and displays an example; the existing launch query remains Last Embryology research. Existing profiles, saved work, credentials and installation locations are preserved. Application version is `1.2.2`; profile, data and archive schemas remain `1.1`.

## Verification and artifacts

Backend tests cover scope isolation, empty-selection fallback, reasoning parameters, exact source queries, citation validation, provider routing, credential isolation, daily usage, privacy and usage gates. Browser checks cover search actions, AI profile generation and rejection, profile/provider persistence across restarts, cancellation, captions, and layouts at desktop, 390px and 320px widths. Verification uses synthetic responses without paid AI calls.

Release artifacts are the Windows installer, named source ZIP/tar.gz archives, these notes and SHA-256 checksums. Installer and hosted-demo publication follows verification of the release commit.

## Verify every result

Results, sources, citations, and calculations may be incorrect, incomplete, or outdated. Users must independently verify every result before relying on or sharing it and remain responsible for their decisions. The tool is for learning and research, not professional advice. Read the [project license](LICENSE), [commercial terms](COMMERCIAL_LICENSING.md), and [disclaimer](DISCLAIMER.md). Warranty and liability exclusions apply only to the extent permitted by applicable law.

[User guide](documentation/USER_GUIDE.md) · [AI and data](documentation/AI_AND_DATA.md) · [Windows installation](WINDOWS_INSTALLATION.md)
