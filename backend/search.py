"""Explicit broad web search and bounded, source-specific query planning."""
import asyncio
import os
from typing import List, Literal
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import ai, budget
from .profiles import get_profile
from .prompting import compose
from .sources import interpret, utc_now

MODEL = "gpt-6-astra"
MAX_WEB_CALLS = 3


class SourceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["pubmed", "ensembl", "gwas"]
    query: str = Field(min_length=1, max_length=250)
    mode: Literal["topic", "gene", "region"]


class QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queries: List[SourceQuery] = Field(min_length=1, max_length=3)


def web_answer(response):
    """Only provider citation annotations become clickable sources, never prose URLs."""
    parts, sources, seen, queries = [], [], set(), []
    calls = 0
    for item in response.output:
        item = item.model_dump() if hasattr(item, "model_dump") else item
        if item.get("type") == "web_search_call":
            calls += 1
            if item.get("status") != "completed":
                raise ValueError("Incomplete web search")
            action = item.get("action") or {}
            if action.get("type") == "search":
                queries.extend(action.get("queries") or ([action["query"]] if action.get("query") else []))
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") != "output_text":
                continue
            text, citations = part.get("text", ""), []
            for annotation in part.get("annotations", []):
                if annotation.get("type") != "url_citation":
                    continue
                url = annotation.get("url", "")
                parsed = urlsplit(url)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                    continue
                start, end = annotation.get("start_index"), annotation.get("end_index")
                if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(text):
                    continue
                citation = {"url": url, "title": annotation.get("title") or parsed.hostname,
                            "start_index": start, "end_index": end}
                citations.append(citation)
                if url not in seen:
                    seen.add(url)
                    sources.append({"url": url, "title": citation["title"]})
            parts.append({"text": text, "citations": citations})
    if not calls or not parts or not sources:
        raise ValueError("No verifiable web search citations were returned")
    return parts, sources, list(dict.fromkeys(queries)), calls


async def search(request, service):
    scope = "specific" if request.scope == "specific" and request.sources else "overall"
    profile = get_profile(request.profile_id)
    if request.profile_revision is not None and profile["revision"] != request.profile_revision:
        raise HTTPException(409, "The profile changed. Retry from its current revision.")
    if request.sensitive and not request.consent_ai:
        raise HTTPException(403, "Review and authorize this sensitive search before sending it.")
    if scope == "overall" and not ai.configured():
        raise HTTPException(503, "Connect AI to use Overall Search with GPT-6 Astra. Specific Search can retrieve checked scientific sources without AI.")
    try:
        interpretation = {"type": "topic", "term": request.query} if scope == "overall" else interpret(request.query, request.mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    metadata = {"scope": scope, "requested_scope": request.scope, "query": request.query,
                "retrieved_at": utc_now(), "demo": False,
                "interpretation": interpretation}
    if not ai.configured():
        plan = [SourceQuery(source=source, query=request.query, mode=metadata["interpretation"]["type"])
                for source in request.sources]
        metadata["search_note"] = "Direct source search. Connect AI to refine queries with the selected reasoning level."
    else:
        budget.check_available()
        task = "overall_search" if scope == "overall" else "specific_search"
        # Broad search is not constrained by the active profile or checked sources.
        if scope == "overall":
            from .discovery_store import ROOT, read_json
            root = ROOT / "prompts" / "runtime"
            messages = [{"role": "system", "content": (root / "base.md").read_text(encoding="utf-8") + "\n" +
                         (root / "tasks" / "overall_search.md").read_text(encoding="utf-8")},
                        {"role": "user", "content": request.query}]
            version = read_json(root / "manifest.json")["version"]
        else:
            messages, version = compose(task, request.query, profile, {"sources": request.sources})
        maximum = ai.output_token_limit(request.reasoning_effort)
        reservation = budget.reserve(profile["id"], MODEL, messages, maximum,
                                     web_calls=MAX_WEB_CALLS if scope == "overall" else 0)
        response = None
        try:
            async with ai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url="https://api.openai.com/v1",
                                    timeout=240, max_retries=0) as client:
                arguments = dict(model=MODEL, reasoning={"effort": request.reasoning_effort},
                                 input=messages, max_output_tokens=maximum, store=False)
                if scope == "overall":
                    response = await client.responses.create(**arguments, tools=[{"type": "web_search", "search_context_size": "low"}],
                                                             tool_choice="required", max_tool_calls=MAX_WEB_CALLS)
                else:
                    response = await client.responses.parse(**arguments, text_format=QueryPlan)
            if getattr(response, "status", "completed") != "completed":
                raise ValueError("Incomplete search response")
            metadata.update(model=MODEL, reasoning_effort=request.reasoning_effort, prompt_version=version)
            if scope == "overall":
                parts, sources, queries, _ = web_answer(response)
                return {**metadata, "records": [], "answer": parts, "web_sources": sources,
                        "coverage": [{"source": "web", "status": "ok", "total": None,
                                      "retrieved": len(sources), "truncated": True,
                                      "query": "\n".join(queries) or request.query, "retrieved_at": utc_now()}]}
            if response.output_parsed is None:
                raise ValueError("No query plan")
            plan = QueryPlan.model_validate(response.output_parsed.model_dump()).queries
            if len(plan) != len(request.sources) or {entry.source for entry in plan} != set(request.sources):
                raise ValueError("The query plan changed the selected coverage")
            for entry in plan:
                interpret(entry.query, entry.mode)
        except HTTPException:
            raise
        except Exception as exc:
            raise ai.ai_error(exc) from None
        finally:
            calls = None
            if response is not None:
                calls = sum((item.model_dump() if hasattr(item, "model_dump") else item).get("type") == "web_search_call"
                            for item in getattr(response, "output", []))
            budget.finish(reservation, getattr(response, "usage", None), web_calls=calls)
    planned = {entry.source: entry for entry in plan}
    responses = await asyncio.gather(*(service.search(source, interpret(planned[source].query, planned[source].mode), request.limit)
                                       for source in request.sources))
    return {**metadata, "records": [record for result in responses for record in result["records"]],
            "coverage": [result["coverage"] for result in responses]}
