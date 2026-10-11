"""Explicit, reviewable profile proposals and local search relevance checks."""
import copy
import re
import unicodedata
from typing import List, Literal

from pydantic import Field

from . import library, profiles

FIELDS = ("goal", "theme_title", "themes", "learning_level", "tabs", "default_tab", "panels")
LAYOUT_FIELDS = {"tabs", "default_tab", "panels"}
STOP_WORDS = set("a an and are as at be by for from how i in is it me my of on or the this to with about learning research study studies evidence review analysis clinical health science sciences general explore develop questions question topic topics introduction find compare using understanding learn advanced beginner new recent".split())


class ProfileProposal(profiles.Strict):
    decision: Literal["update", "already_matches", "repeated_request"] = "update"
    goal: str = Field(min_length=1, max_length=1000)
    theme_title: str = Field(min_length=1, max_length=180)
    themes: List[str] = Field(max_length=30)
    learning_level: Literal["beginner", "intermediate", "advanced", "expert", "researcher", "frontier", "beyond_frontier"]
    tabs: List[Literal["evidence", "documents", "datasets", "connections", "quizzes", "notes"]] = Field(min_length=1, max_length=6)
    default_tab: Literal["evidence", "documents", "datasets", "connections", "quizzes", "notes"]
    panels: List[Literal["guidance", "constraints", "tip"]] = Field(max_length=3)
    ui: profiles.Copy
    explanation: str = Field(min_length=1, max_length=2000)


def terms(text):
    return {word for word in re.findall(r"[^\W_]+", text.casefold()) if len(word) >= 3 and word not in STOP_WORDS}


def normalized_request(text):
    # Only remove presentation/politeness. Retain negation, numbers and operators:
    # near-identical medical constraints can mean very different things.
    text = unicodedata.normalize("NFKC", text).casefold().strip()
    text = re.sub(r"^(?:(?:please|kindly|could you|would you|can you)[\s,]+)+", "", text)
    return re.sub(r"\s+", " ", text).strip(" \t\r\n.!?")


def satisfied_requests(profile, allow_level_change, allow_layout_changes):
    """Reuse only proposals whose complete result is still the current profile.

    A partial application, a discarded draft, or a rollback must not be called
    an already-applied update. Sensitive request/output bodies are never reused.
    """
    options = {"allow_level_change": allow_level_change, "allow_layout_changes": allow_layout_changes}
    matches = []
    for summary in library.list_activities(profile=profile["id"], kind="ai")[:30]:
        if summary["title"] != "AI adapt_profile" or summary.get("sensitive"):
            continue
        item = library.get_activity(summary["id"])
        output = item.get("payload", {})
        if item.get("status") != "complete" or not isinstance(output, dict) or output.get("omitted"):
            continue
        proposed = output.get("profile", {})
        if output.get("request_options", {"allow_level_change": False, "allow_layout_changes": False}) != options:
            continue
        if not isinstance(proposed, dict) or any(proposed.get(key) != profile[key] for key in (*FIELDS, "ui")):
            continue
        instruction = item.get("request", "")
        if not instruction or instruction == "[sensitive request omitted]":
            continue
        matches.append({"id": item["id"], "instruction": instruction})
        if len(matches) == 3:
            break
    return matches


def repeated_request_result(profile, instruction, satisfied):
    match = next((item for item in satisfied if normalized_request(item["instruction"]) == normalized_request(instruction)), None)
    if not match:
        return None
    return {"profile": copy.deepcopy(profile), "changes": [], "decision": "repeated_request", "cached": True,
            "explanation": "No profile changes needed. You already requested this update, and your current profile reflects it.",
            "base_revision": profile["revision"], "reused_activity_id": match["id"], "provenance": {"origin": "template"}}


def related_terms(profile):
    # The profile's own examples also capture abbreviations such as PCOS and BRCA1.
    labels = [profile["goal"], profile["theme_title"], *profile["ui"]["examples"]]
    taxonomy = profiles.taxonomy()
    for tid in profile["themes"]:
        node = taxonomy[tid]
        labels.append(node["name"])
        parent = taxonomy.get(node.get("parent_id"))
        if parent and parent["node_type"] in {"discipline", "theme"}:
            labels.append(parent["name"])
    return terms(" ".join(labels))


def recent_searches(profile):
    """Inspect ten local searches, returning up to five related, non-sensitive queries."""
    matches, seen = [], set()
    latest_related = False
    keywords = related_terms(profile)
    for index, summary in enumerate(library.list_activities(profile=profile["id"], kind="search")[:10]):
        item = library.get_activity(summary["id"])
        payload = item.get("payload", {})
        query = item.get("request", "").strip()
        if (item.get("sensitive") or item.get("status") != "complete" or payload.get("omitted")
                or payload.get("demo") or not 1 <= len(query) <= 250
                or not any(c.get("status") == "ok" for c in payload.get("coverage", []) if isinstance(c, dict))):
            continue
        common = sorted(terms(query) & keywords)
        if index == 0:
            latest_related = bool(common)
        if not common or query.casefold() in seen:
            continue
        seen.add(query.casefold())
        matches.append({"id": item["id"], "query": query, "matched_terms": common, "created_at": item["created_at"]})
    return {"profile_id": profile["id"], "revision": profile["revision"], "latest_related": latest_related, "searches": matches[:5]}


def proposal_context(profile, instruction, allow_level_change, allow_layout_changes):
    taxonomy = profiles.taxonomy()
    keywords = terms(instruction) | related_terms(profile)
    selectable = [node for node in taxonomy.values() if node["node_type"] not in {"root", "branch"}]
    # Bound the catalogue context; always include the currently selected themes.
    ranked = sorted(selectable, key=lambda node: (node["id"] in profile["themes"], len(terms(node["name"]) & keywords)), reverse=True)
    return {
        "available_themes": [{"id": node["id"], "name": node["name"]} for node in ranked[:100]],
        "current_layout": {key: profile[key] for key in ("tabs", "default_tab", "panels")},
        "available_tabs": profiles.TABS, "available_panels": profiles.PANELS,
        "available_levels": [{"id": level[0], "name": level[1], "description": level[2]} for level in profiles.LEVELS],
        "allow_level_change": allow_level_change, "allow_layout_changes": allow_layout_changes,
    }


def build_proposal(profile, output, provenance, allow_level_change=False, allow_layout_changes=False):
    if output.get("decision") in {"already_matches", "repeated_request"}:
        return copy.deepcopy(profile), []
    proposed = copy.deepcopy(profile)
    changes = []
    for field in FIELDS:
        if field == "learning_level" and not allow_level_change:
            continue
        if field in LAYOUT_FIELDS and not allow_layout_changes:
            continue
        if output[field] != profile[field]:
            proposed[field] = output[field]
            proposed["provenance"][field] = provenance
            changes.append({"field": field, "before": profile[field], "after": output[field]})
    for field, value in output["ui"].items():
        if value != profile["ui"][field]:
            proposed["ui"][field] = value
            proposed["provenance"][field] = provenance
            changes.append({"field": "ui." + field, "before": profile["ui"][field], "after": value})
    return profiles.validate_profile(proposed), changes
