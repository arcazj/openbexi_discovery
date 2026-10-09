"""Validated profiles, immutable defaults, taxonomy and revisioned workspace state."""
import copy
import json
import uuid
from functools import lru_cache
from typing import Dict, List, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .discovery_store import ROOT, LOCK, data_root, identifier, read_json, write_json, stamp, settings, update_settings, redact

LEVELS = [
    ("beginner", "Foundation", "Learn basic concepts, terminology, and principles.", "Understand atoms, energy, and light."),
    ("intermediate", "Intermediate", "Build understanding through lessons and exercises.", "Learn wave-particle duality."),
    ("advanced", "Advanced", "Solve complex problems and connect concepts.", "Solve Schrödinger equations."),
    ("expert", "Expert", "Master specialized domains and technical methods.", "Study quantum field theory."),
    ("researcher", "Researcher", "Analyze publications, evidence, and open questions.", "Analyze recent quantum physics publications."),
    ("frontier", "Frontier", "Explore unresolved problems and emerging theories.", "Investigate quantum gravity and unresolved questions."),
    ("beyond_frontier", "Beyond the Frontier", "Formulate hypotheses, design experiments, and test ideas.", "Develop a testable hypothesis and design a simulation or experiment."),
]
TABS = ["evidence", "documents", "datasets", "connections", "quizzes", "notes"]
TOOLS = {"papers": "available", "quizzes": "available", "ai_tutor": "planned", "simulations_3d": "planned",
         "math_engine": "planned", "knowledge_graph": "planned", "research_agents": "planned"}
PANELS = ["guidance", "constraints", "tip"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=8000, allow_inf_nan=False)


class Copy(Strict):
    eyebrow: str = Field(max_length=180)
    heading: str = Field(max_length=180)
    introduction: str = Field(max_length=1200)
    sources_title: str = Field(max_length=80)
    sources_caption: str = Field(max_length=120)
    search_label: str = Field(max_length=200)
    search_placeholder: str = Field(max_length=250)
    examples: List[str] = Field(max_length=5)
    welcome_heading: str = Field(max_length=180)
    welcome_title: str = Field(max_length=180)
    welcome_text: str = Field(max_length=1600)
    guidance_heading: str = Field(max_length=180)
    guidance_text: str = Field(max_length=1200)
    constraints_heading: str = Field(max_length=180)
    deadline_label: str = Field(max_length=180)
    deadline_hint: str = Field(max_length=250)
    data_label: str = Field(max_length=180)
    data_hint: str = Field(max_length=250)
    mentor_label: str = Field(max_length=180)
    mentor_hint: str = Field(max_length=250)
    tip_heading: str = Field(max_length=80)
    tip_text: str = Field(max_length=1200)


class Provenance(Strict):
    origin: Literal["template", "user", "ai", "ai_edited", "unverified"] = "template"
    model: Optional[str] = Field(default=None, max_length=100)
    generated_at: Optional[str] = Field(default=None, max_length=80)


class Profile(Strict):
    schema_version: Literal["1.1"] = "1.1"
    id: str = Field(default="draft", pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    revision: int = Field(default=0, ge=0)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    goal: str = Field(min_length=1, max_length=1000)
    theme_title: str = Field(min_length=1, max_length=180)
    themes: List[str] = Field(default_factory=list, max_length=30)
    learning_level: Literal["beginner", "intermediate", "advanced", "expert", "researcher", "frontier", "beyond_frontier"] = "advanced"
    tabs: List[Literal["evidence", "documents", "datasets", "connections", "quizzes", "notes"]] = Field(default_factory=lambda: TABS.copy(), min_length=1, max_length=6)
    default_tab: str = "evidence"
    panels: List[Literal["guidance", "constraints", "tip"]] = Field(default_factory=lambda: PANELS.copy(), max_length=3)
    sources: List[Literal["pubmed", "ensembl", "gwas"]] = Field(default_factory=lambda: ["pubmed", "ensembl", "gwas"], max_length=3)
    tools: List[str] = Field(default_factory=lambda: ["papers", "quizzes"], max_length=7)
    connection_ids: List[str] = Field(default_factory=list, max_length=20)
    ui: Copy
    provenance: Dict[str, Provenance] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @model_validator(mode="after")
    def supported(self):
        for items in (self.tabs, self.panels, self.sources, self.themes, self.tools, self.connection_ids):
            if len(items) != len(set(items)):
                raise ValueError("Duplicate selections are not allowed.")
        if self.default_tab not in self.tabs:
            raise ValueError("The initial tab must be visible.")
        if any(TOOLS.get(t) != "available" for t in self.tools):
            raise ValueError("Choose implemented tools only.")
        if any(k not in Copy.model_fields and k != "theme_title" for k in self.provenance):
            raise ValueError("Unknown content provenance field.")
        for value in self.connection_ids:
            identifier(value)
        return self


@lru_cache(maxsize=1)
def taxonomy():
    base = (ROOT / "themes" / "world_research_taxonomy").resolve()
    nodes = {}
    visited = set()

    def visit_file(path):
        path = path.resolve()
        if base not in path.parents or path in visited:
            return
        visited.add(path)
        visit(json.loads(path.read_text(encoding="utf-8")), path)

    def visit(node, path):
        if "file" in node:
            visit_file(path.parent / node["file"])
            return
        nodes[node["id"]] = {k: node[k] for k in ("id", "name", "node_type", "parent_id") if k in node}
        nodes[node["id"]]["source"] = path.relative_to(base).as_posix()
        for child in node.get("children", []):
            visit(child, path)
    visit_file(base / "world_research_overview.json")
    return nodes


def validate_profile(value, check_themes=True):
    profile = Profile.model_validate(value).model_dump()
    if check_themes and any(t not in taxonomy() or taxonomy()[t]["node_type"] in {"root", "branch"} for t in profile["themes"]):
        raise HTTPException(422, "Choose existing taxonomy themes, disciplines, or research areas.")
    return profile


def template(name="rei"):
    return validate_profile(read_json(ROOT / "templates" / ("general.json" if name == "general" else "rei.json")))


def profile_path(pid):
    return data_root() / "user_profiles" / (identifier(pid) + ".json")


def ensure_default():
    with LOCK:
        if not profile_path("rei").exists():
            value = template()
            value.update(id="rei", revision=1, created_at=stamp(), updated_at=stamp())
            write_json(profile_path("rei"), value)


def get_profile(pid):
    ensure_default()
    value = read_json(profile_path(pid))
    if not value:
        raise HTTPException(404, "Profile not found.")
    return validate_profile(value)


def list_profiles():
    ensure_default()
    return [get_profile(p.stem) for p in sorted((data_root() / "user_profiles").glob("*.json"))]


def save_profile(value, base_revision=None, create=False):
    with LOCK:
        value = validate_profile(value)
        old = None if create else get_profile(value["id"])
        if old:
            if base_revision != old["revision"]:
                raise HTTPException(409, "This profile changed. Reload it before saving.")
            if set(old["themes"]) != set(value["themes"]):
                raise HTTPException(409, "Changed themes require a new profile.")
            write_json(data_root() / ".discovery" / "profile_versions" / old["id"] / (str(old["revision"]) + ".json"), old)
        value.update(id=old["id"] if old else uuid.uuid4().hex,
                     revision=old["revision"] + 1 if old else 1,
                     created_at=old["created_at"] if old else stamp(), updated_at=stamp())
        if old:
            for key in Copy.model_fields:
                prior = old["provenance"].get(key, {})
                if (value["ui"][key] != old["ui"][key] and prior.get("origin") in {"ai", "ai_edited"}
                        and value["provenance"].get(key, {}).get("generated_at") == prior.get("generated_at")):
                    value["provenance"][key] = {**prior, "origin": "ai_edited"}
        value = validate_profile(value)
        write_json(profile_path(value["id"]), value)
        return value


def profile_action(pid, action, revision):
    with LOCK:
        old = get_profile(pid)
        if old["revision"] != revision:
            raise HTTPException(409, "Profile changed; reload it first.")
        if action == "activate":
            update_settings({"active_profile": pid})
            return old
        if action == "delete":
            if pid == "rei":
                raise HTTPException(422, "Reset the default REI profile instead of deleting it.")
            write_json(data_root() / ".discovery" / "deleted_profiles" / (pid + ".json"), old)
            profile_path(pid).unlink()
            if settings()["active_profile"] == pid:
                update_settings({"active_profile": "rei"})
            return {"deleted": pid}
        if action == "reset" and pid == "rei":
            result = template()
        elif action == "undo":
            result = read_json(data_root() / ".discovery" / "profile_versions" / pid / (str(revision - 1) + ".json"))
            if not result:
                raise HTTPException(404, "No earlier revision is available.")
        else:
            raise HTTPException(422, "Unknown profile action.")
        result.update(id=pid, themes=old["themes"])
        return save_profile(result, revision)


def workspace(pid):
    get_profile(pid)
    return read_json(data_root() / ".discovery" / "workspaces" / (pid + ".json"), {"revision": 0, "data": {}})


def save_workspace(pid, data, revision):
    if len(json.dumps(data)) > 2_000_000:
        raise HTTPException(413, "Workspace is too large. Archive older work first.")
    with LOCK:
        old = workspace(pid)
        if old["revision"] != revision:
            raise HTTPException(409, "Workspace changed in another window. Reload before saving.")
        result = {"revision": revision + 1, "data": redact(data), "updated_at": stamp()}
        write_json(data_root() / ".discovery" / "workspaces" / (pid + ".json"), result)
        return result
