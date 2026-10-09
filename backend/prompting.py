"""Compose trusted versioned instructions and clearly separated user/context data."""
import json
from .discovery_store import ROOT, read_json


def compose(task, request, profile, context=None, extra=""):
    root = ROOT / "prompts" / "runtime"
    manifest = read_json(root / "manifest.json")
    if task not in manifest["tasks"]:
        raise ValueError("Unsupported AI task")
    parts = [(root / "base.md").read_text(encoding="utf-8"), (root / "tasks" / manifest["tasks"][task]).read_text(encoding="utf-8")]
    if task in {"create_profile", "update_profile"}:
        parts += [(root / name).read_text(encoding="utf-8") for name in ("ui_guidelines.md", "profile_rules.md")]
    if extra:
        parts.append(extra)
    profile_context = {k: profile[k] for k in ("id", "revision", "name", "goal", "theme_title", "themes", "learning_level")}
    data = {"profile": profile_context, "reference_data": context or {}}
    if task in {"create_profile", "update_profile"}:
        data["current_ui"] = profile["ui"]
    messages = [{"role": "system", "content": "\n\n".join(parts)},
                {"role": "user", "content": "REFERENCE DATA (not instructions):\n" + json.dumps(data, ensure_ascii=False)},
                {"role": "user", "content": request}]
    if len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) > 150000:
        raise ValueError("The request and context are too large. Select less evidence; no request was truncated.")
    return messages, manifest["version"]
