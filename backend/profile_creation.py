"""Generate a complete profile draft from an area of interest, without saving it."""
import json
from typing import List, Literal, Optional

from fastapi import HTTPException
from pydantic import Field

from . import ai, budget, profiles


class ProfileContent(profiles.Strict):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=360)
    goal: str = Field(min_length=1, max_length=1000)
    theme_title: str = Field(min_length=1, max_length=180)
    themes: List[str] = Field(min_length=3, max_length=8)
    sources: List[Literal["pubmed", "ensembl", "gwas"]] = Field(max_length=3)
    ui: profiles.Copy


class ProfileCreation(profiles.Strict):
    decision: Literal["accepted", "rejected"]
    explanation: str = Field(min_length=1, max_length=500)
    content: Optional[ProfileContent]


async def generate(value):
    area = value.instruction.strip()
    if not area:
        raise HTTPException(422, "Describe a field or area of interest.")
    budget.check_available()
    if not ai.configured():
        raise HTTPException(503, "Connect AI to generate a complete profile from your area of interest.")
    base = profiles.template("general")
    base.update(goal=value.profile.goal, learning_level=value.profile.learning_level)
    catalogue = [{"id": n["id"], "name": n["name"]} for n in profiles.taxonomy().values()
                 if n["node_type"] in {"theme", "discipline", "research_area"}]
    request = json.dumps({"area_of_interest": area, "optional_goal": value.profile.goal,
                          "optional_description": value.profile.description}, ensure_ascii=False)
    result = await ai.structured_task("generate_profile", base, request,
        {"topic_catalogue": catalogue, "learning_level": base["learning_level"],
         "existing_profile_names": [p["name"] for p in profiles.list_profiles()],
         "available_sources": {"pubmed": "Biomedical literature", "ensembl": "Human genomics",
                               "gwas": "Genetic associations"}}, ProfileCreation, effort=value.reasoning_effort or "medium")
    if result["decision"] == "rejected":
        return {key: result[key] for key in ("decision", "explanation", "provenance", "reasoning_effort")}
    content = result["content"]
    if (not content or not 2 <= len(content["ui"]["examples"]) <= 5
            or any(not text.strip() for key, text in content["ui"].items() if key != "examples")
            or any(not text.strip() for text in content["ui"]["examples"])):
        raise HTTPException(502, "AI returned an incomplete profile. Please try again.")
    base.update(content)
    base["hidden_source_ids"] = [source for source in ("pubmed", "ensembl", "gwas") if source not in base["sources"]]
    base["provenance"] = {key: result["provenance"] for key in (*profiles.Copy.model_fields, "name", "description", "goal", "theme_title", "themes")}
    try:
        draft = profiles.validate_profile(base)
    except (ValueError, HTTPException):
        raise HTTPException(502, "AI returned unsupported profile topics or settings. Please try again.") from None
    if any(p["name"].casefold() == draft["name"].casefold() for p in profiles.list_profiles()):
        raise HTTPException(409, "AI suggested a profile name that already exists. Refine your area of interest and try again.")
    return {"decision": "accepted", "profile": draft, "explanation": result["explanation"],
            "provenance": result["provenance"], "reasoning_effort": result["reasoning_effort"]}
