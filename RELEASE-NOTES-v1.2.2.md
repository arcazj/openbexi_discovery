# OpenBEXI Discovery v1.2.2

Version 1.2.2 introduces broad and source-specific search with compact reasoning controls and a prominent, lightweight prompt box.

## Search

- **Overall Search** uses GPT-6 Astra and live web search, independently of checked sources. Answers show clickable provider citations, their model and reasoning level; actual search coverage stays in the saved result.
- **Specific Search** uses GPT-6 Astra to prepare precise queries for checked PubMed, Ensembl and GWAS sources, then retrieves records from those services. Generated plans cannot add unselected sources. Leaving everything unchecked performs an overall search.
- Each green split button has its own **Low**, **Medium** or **High** reasoning choice, defaulting to Medium. Changing a choice does not run a search. These search choices are saved per profile; other AI tools keep their connection settings.
- The search box has a modestly taller input, clear contrast and a visible focus state. Overall Search sits on the right, with Specific Search directly below it beside coverage controls. Request privacy sits directly beneath Specific Search.
- Select all / Clear selection, hover and keyboard captions, touch help, a loading state, cancellation, and a broad-search action for empty specific results support refinement. The layout stacks naturally on mobile.
- The results toolbar keeps the workspace tabs, **Source evidence**, and a right-aligned **10 / 20 / 50 records** selector. Routine notices, coverage badges, scope summaries and evidence-type filters are removed. The selector changes visible results without another AI request; searches retrieve up to 50 records per selected source.
- Source failures remain distinct from zero matches. Requests, selections and reasoning remain available after a search. Broad AI answers retain separate source links and AI attribution.

## Compatibility and privacy

Search AI explicitly uses `gpt-6-astra`; provider errors do not substitute another model. Overall Search requires a configured OpenAI key with Astra and web-search access. Without AI, Specific Search can still retrieve checked scientific sources directly. The public demo supports direct Specific Search only.

Sensitive searches require review before being sent. Local-only mode blocks external search. Web-search tool calls and retrieved input tokens are included in local usage estimates. Cancellation stops waiting and discards the pending result; work already accepted by a provider may still incur usage.

The automatic REI launch search remains a direct source request without AI spending. The prompt field stays empty and displays an example; the existing launch query remains Last Embryology research. Existing profiles, saved work, credentials and installation locations are preserved. Application version is `1.2.2`; profile, data and archive schemas remain `1.1`.

## Verification and artifacts

Backend tests cover scope isolation, empty-selection fallback, reasoning parameters, exact source queries, citation validation, privacy and usage gates. Browser checks cover search actions, settings persistence, cancellation, captions, and layouts at desktop, 390px and 320px widths. Verification uses synthetic responses without paid AI calls.

Release artifacts are the Windows installer, named source ZIP/tar.gz archives, these notes and SHA-256 checksums. Installer and hosted-demo publication follows verification of the release commit.

[User guide](documentation/USER_GUIDE.md) · [AI and data](documentation/AI_AND_DATA.md) · [Windows installation](WINDOWS_INSTALLATION.md)
