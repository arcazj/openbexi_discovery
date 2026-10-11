# AI, usage, and data

## Connection and prompts

Open **Connect AI** in the header to choose **Model** and **Reasoning**, enter your key, and select **Save & connect**. The default is **GPT-6 Astra / xHigh**. After connecting, the same status button reopens this dialog; there is no separate AI settings button. You can change the model or reasoning without entering the saved key again. The server saves these choices in private `.env`, not browser storage, profiles, or exports. Environment equivalents are `OPENAI_MODEL=gpt-6-astra` and `OPENAI_REASONING_EFFORT=xhigh`; errors never substitute another model.

Reasoning choices are Low, Medium, High, xHigh, and Max. These are supported by the [GPT-6 Astra API](https://developers.openai.com/api/docs/models/gpt-6-astra). Higher reasoning can use more output tokens and take longer. Both research assistance and quiz/profile generation use the selected reasoning level.

Generation uses versioned task templates from `prompts/runtime/`, relevant profile context, and the user's distinct request. Reference documents are data, not instructions. Profile edits are validated and previewed; ordinary answers/quizzes cannot change profiles.

Every AI request shows a shared progress panel with the task name, an animated activity bar, elapsed time, and a polite wait message. It follows the active dialog or appears in the workspace corner. Concurrent tasks have independent bars, removed on completion, failure, timeout, or cancellation. The bar is not a percentage estimate. Quiz and profile preparation retain their Cancel actions; cancellation may not stop an already-dispatched provider request or its charges.

**Update profile with AI** is an explicit, metered `adapt_profile` task. It uses the saved profile, the instructions you review, and a bounded set of existing taxonomy themes. The recent-search shortcut performs a local keyword check and includes only reviewed query text; it does not attach result bodies, notes, datasets, or connection credentials. Mark sensitive instructions before generating to review the outgoing request; routine AI history then omits request and response bodies. Profile configuration is saved locally when you apply it, so avoid including personal identifiers or secrets in permanent profile text.

The server constrains proposed fields and preserves level and layout unless their options were enabled. A preview does not save the profile. Applying selected changes checks the original revision, and **Roll back profile** restores the preceding saved configuration with its original provenance. AI cannot change connection credentials, source visibility, permissions, budgets, or application code through a profile proposal.

Repeating an update whose complete proposal still matches the saved profile can return **No profile changes needed** locally, without reserving tokens or creating another profile revision. Other similar phrasings are evaluated by AI using up to three prior non-sensitive profile requests already reflected in the current configuration. A no-change decision preserves all current values, even if the returned wording differs. Changed requirements and rolled-back or partially applied proposals are not silently treated as duplicates. A locally reused result does not clear a provider quota warning.

## Usage and availability

The connection dialog retains **By profile and model**, showing locally recorded requests, tokens, and estimated costs. The former **Usage & budget** controls have been removed. These counts describe this installation's requests, not the remaining balance in your provider account.

If the provider reports exhausted credits or quota, an **AI tokens unavailable** notice explains how to restore access. Automatic guidance pauses; saved work remains available. A successful generation clears the notice. Temporary rate limits display a retry message instead. Checking model access alone does not establish that generation quota is available.

Previously saved local limits remain enforced. When one blocks AI, the connection dialog shows its reason and an explicit **Remove saved local limits** action. Daily/monthly boundaries are UTC. Blocked requests are not replayed. The backend reserves conservative input and bounded output allowances before dispatch, shares allowances across concurrent requests, and reconciles reported usage. Failed/canceled requests may retain estimated usage when final usage is unknown.

Costs are local estimates, not the provider's final bill or usage in other applications. Rates are stored with requests. Bundled rates cover [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) and [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol); other model costs display as unknown until added to `templates/pricing.json`. Unknown prices block generation when a saved cost limit applies. Reasoning tokens count within output, not twice. Paid AI tools and nonstandard service tiers are not enabled.

## Quizzes

**Quizzes → Start a quiz** generates exactly eight questions using the active profile's themes, goal, and learning level, then saves and opens the quiz. Answer all questions and select **Grade & save attempt** to see the score, percentage, correct answers, and explanations. Grading is local and does not consume AI tokens. Attempts retain a snapshot of the questions, original model attribution, and level, so reviews remain available after the quiz is changed or deleted.

**Quiz history** belongs to the active profile. **Remove attempt** deletes one attempt; **Clear history** deletes that profile's attempts. Saved quizzes and other profiles' history remain available. Existing exported ZIP backups retain their copies.

## Provenance and sensitive content

Green means source/user content or unknown upstream AI origin, not verified human authorship or correctness. Orange means app-generated AI content, with the original model/date retained after model changes. Edited generated content remains AI-assisted.

The color key below the workspace introduction explains both backgrounds and shows the connected model or current connection status. It remains visible in browser-only and offline modes and when switching profiles. The connected model applies to new AI text; saved text keeps its original model attribution.

The workspace heading and description, source bar/profile badge, and search controls are visual exceptions: their backgrounds stay standard even when AI drafted their wording. Provenance metadata and attribution remain available. AI-generated answers, tips, and profile previews retain orange highlighting.

Viewing data does not authorize AI transmission or export. Mark sensitive uploads and authorize local retention. Snapshots are excluded from ZIPs unless explicitly selected. Keys/credential-like values are omitted from routine history. Sensitive prompts require marking and authorization; their request/response bodies are excluded from routine history.

Dataset analysis requires a locally reviewed working copy and explicit authorization. Original rows, replacement mappings, original filenames, API credentials, and private connection settings are excluded from AI context. The backend verifies a private receipt against the saved copy, so an imported or edited privacy flag alone cannot enable AI. Statistics are computed locally over the complete saved copy; AI receives those statistics and a bounded sample of at most 100 rows. Keep patient identifiers out of general prompts and constraints. Local detection cannot identify every sensitive value. Profiles organize work; they are not separate authenticated accounts.

External data-API credentials, replacement mappings, and optional retained originals are encrypted under `.discovery/private/`, outside the library and its exports. The OpenAI key continues to use the private `.env` described above. Windows uses user-scoped [DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata); other platforms use [Fernet](https://cryptography.io/en/stable/fernet/) with an owner-readable local key file. Protect the OS account and private data directory; these are local protections, not a multi-user vault. Portable copies need a new privacy review after import, and encrypted Windows originals are generally tied to the originating account/computer.

The app binds to loopback, checks browser origins, and restricts Discovery mutations to the local peer. A multi-user network deployment needs separate authentication/authorization. Ordinary library records, working copies, and exported ZIPs are not encrypted by the application; sensitive exports still require explicit selection.
