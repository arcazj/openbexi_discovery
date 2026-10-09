# 05 — Medicine & Health Sciences | Research Tree JSON

**Dataset:** 14 themes / 133 disciplines / 568 research areas.
This folder contains **15 JSON files**, with a root index and 14 detailed topic trees.

## Files

- `05_domain_overview.json` — the main overview. It lists the 14 themes, the nested discipline labels, item counts, and their relative file paths.
- `domains/05.01_*.json` through `domains/05.14_*.json` — one full tree per theme, containing every discipline and research area.

## Node format

Every detailed theme JSON contains a `children` hierarchy:

```
05                        Domain (in the overview)
└── 05.01                 Theme
    └── 05.01.01          Discipline
        └── 05.01.01.01   Research area
```

Detailed nodes use `id`, `code`, `name`, `node_type`, `parent_id`, and `children`.
The overview uses `children[].file` to point to the corresponding detailed theme JSON.
IDs are deterministic ordinal codes based on the earlier PDF taxonomy; they are **not official OECD or NIH codes**.

## Browser loading example

```js
const overview = await (await fetch('/medicine_research_taxonomy/05_domain_overview.json')).json();
const selectedTheme = overview.children.find(theme => theme.id === '05.07');
const theme = await (await fetch(`/medicine_research_taxonomy/${selectedTheme.file}`)).json();
console.log(theme.children);  // disciplines with nested research areas
```

UTF-8 encoding; JSON schema version 1.0. Area nodes have empty `children` arrays.
