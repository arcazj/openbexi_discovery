# AI, budgets, and data

## Connection and prompts

Enter your key through AI settings. The server saves it in private `.env`, not browser storage, profiles, or exports. `OPENAI_MODEL` selects the model (default `gpt-6.1-sol`); errors never substitute another model.

Generation uses versioned task templates from `prompts/runtime/`, relevant profile context, and the user's distinct request. Reference documents are data, not instructions. Profile edits are validated and previewed; ordinary answers/quizzes cannot change profiles.

## Usage and limits

Token and USD limits apply across this installation's profiles and keys. Select daily, monthly, or cumulative accounting; boundaries are UTC. Sliders and numeric inputs stay synchronized. Zero blocks requests; disabled limits are unlimited. No budget is imposed until saved.

The backend reserves conservative input and bounded output allowances before dispatch. Concurrent requests share the remaining allowance. Reported usage replaces reservations. Failed/canceled requests can still incur usage, so uncertain final usage retains its reservation rather than being reset to zero.

When blocked, AI settings turns red. New requests/retries/checks stop; local work continues. Explicitly raise/disable a limit or wait for the daily/monthly reset. Blocked requests are not replayed. Cumulative accounting retains the first configuration time.

Costs are local estimates, not the provider's final bill or usage in other applications. Rates are stored with requests. Bundled standard text rates were verified on 2026-10-09 against the [GPT-6.1 Sol model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol). Update `templates/pricing.json` when changing models; unknown prices block cost-limited generation. Reasoning tokens count within output, not twice. Paid AI tools and nonstandard service tiers are not enabled.

## Provenance and sensitive content

Green means source/user content or unknown upstream AI origin, not verified human authorship or correctness. Orange means app-generated AI content, with the original model/date retained after model changes. Edited generated content remains AI-assisted.

Viewing data does not authorize AI transmission or export. Mark sensitive uploads and authorize local retention. Snapshots are excluded from ZIPs unless explicitly selected. Keys/credential-like values are omitted from routine history. Sensitive prompts require marking and authorization; their request/response bodies are excluded from routine history.

Connected rows have no automatic AI analysis path in 1.1.1. Keep patient identifiers out of general prompts and constraints. Explicit source/field choices are controls; arbitrary sensitive text cannot always be detected automatically. Profiles organize work; they are not separate authenticated accounts.

The app binds to loopback, checks browser origins, and restricts Discovery mutations to the local peer. A multi-user network deployment needs separate authentication/authorization. Storage and ZIPs are not encrypted by the application.
