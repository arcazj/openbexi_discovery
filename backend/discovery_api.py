"""Discovery 1.1 API. All mutations remain on the loopback-only JSON API."""
import asyncio
import base64
import json
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import Field, StrictInt

from . import profiles, budget, library, connections, ai, datasets, api_connections, private_store, profile_adaptation
from .discovery_store import ROOT, LOCK, stamp, settings, update_settings
from .prompting import compose

router = APIRouter(prefix="/api/discovery")
ACTIVE_AI = set()


async def tracked_ai(coroutine):
    task = asyncio.create_task(coroutine)
    ACTIVE_AI.add(task)
    try:
        return await task
    except asyncio.CancelledError:
        raise HTTPException(423, "AI request canceled. Local work is preserved; incurred usage is retained.") from None
    finally:
        ACTIVE_AI.discard(task)


def cancel_active():
    for task in list(ACTIVE_AI):
        task.get_loop().call_soon_threadsafe(task.cancel)


class ProfileSave(profiles.Strict):
    profile: profiles.Profile
    base_revision: Optional[int] = None
    create: bool = False


class ProfileAction(profiles.Strict):
    id: str
    action: Literal["activate", "delete", "reset", "undo"]
    revision: int


class WorkspaceSave(profiles.Strict):
    profile_id: str
    revision: int
    data: Dict[str, Any]


class SettingsSave(profiles.Strict):
    local_only: bool


class ArchiveUpload(profiles.Strict):
    file_base64: str = Field(max_length=library.MAX_ZIP * 2)


class ArchiveImport(profiles.Strict):
    id: str
    consent_sensitive: bool = False


class Export(profiles.Strict):
    profile_id: str = ""
    activity_id: str = ""
    include_sensitive: bool = False


class Connect(profiles.Strict):
    name: str
    path: str = ""
    file_base64: str = Field(default="", max_length=library.MAX_FILE * 2)
    sensitive: bool = True
    consent_local: bool = False
    profile_id: str = 'rei'


class DatabaseQuery(profiles.Strict):
    connection_id: str
    table: str
    fields: List[str] = Field(min_length=1, max_length=40)
    filters: Dict[str, str] = Field(default_factory=dict)
    offset: int = Field(default=0, ge=0, le=1_000_000)
    snapshot: bool = False
    profile_id: str = "rei"
    consent_local: bool = False


class QuizAttempt(profiles.Strict):
    activity_id: str
    answers: List[StrictInt] = Field(max_length=50)
    profile_id: Optional[str] = None


class RestoreProfile(profiles.Strict):
    consent_sensitive: bool = False


class QuizHistoryDelete(profiles.Strict):
    profile_id: str
    attempt_id: Optional[str] = None


class DraftRequest(profiles.Strict):
    task: Literal["create_profile", "update_profile", "adapt_profile", "create_quiz", "answer"]
    profile: profiles.Profile
    instruction: str = Field(min_length=1, max_length=8000)
    sensitive: bool = False
    consent_ai: bool = False
    allow_level_change: bool = False
    allow_layout_changes: bool = False


class ProfileTextDraft(profiles.Strict):
    theme_title: str
    ui: profiles.Copy
    explanation: str


class Answer(profiles.Strict):
    text: str


class DatasetImport(profiles.Strict):
    profile_id: str
    filename: str = Field(max_length=200)
    file_base64: str = Field(max_length=library.MAX_FILE * 2)


class DatasetPreview(profiles.Strict):
    rules: List[datasets.Rule] = Field(min_length=1, max_length=100)
    terms: List[str] = Field(default_factory=list, max_length=100)
    offset: int = Field(default=0, ge=0, le=5000)


class DatasetSave(profiles.Strict):
    preview_id: str
    reviewed: bool = False
    retain_original: bool = False
    title: str = Field(default='Reviewed dataset', min_length=1, max_length=200)


class DatasetQuestion(profiles.Strict):
    question: str = Field(min_length=1, max_length=4000)
    consent_ai: bool = False


class DatasetAnswer(profiles.Strict):
    answer: str = Field(min_length=1, max_length=8000)
    limitations: List[str] = Field(max_length=8)


class APIProfile(profiles.Strict):
    profile_id: str


class APIQuery(APIProfile):
    query: str = Field(default='', max_length=1000)


@router.get('/api-connections/catalog')
def api_catalog():
    return {'services':api_connections.CATALOG}


@router.get('/api-connections')
def api_list(profile_id: str):
    return {'connections':api_connections.public(profile_id)}


@router.post('/api-connections')
async def api_connect(value: api_connections.APIConfig):
    return await api_connections.connect(value)


@router.post('/api-connections/recommend')
async def api_recommend(value: APIProfile):
    return await tracked_ai(api_connections.recommend(value.profile_id))


@router.post('/api-connections/{cid}/check')
async def api_check(cid: str, value: APIProfile):
    return await api_connections.check(cid, value.profile_id)


@router.post('/api-connections/{cid}/query')
async def api_query(cid: str, value: APIQuery):
    return await api_connections.query(cid, value.profile_id, value.query)


@router.post('/api-connections/{cid}/disconnect')
def api_disconnect(cid: str, value: APIProfile):
    return api_connections.disconnect(cid, value.profile_id)


@router.post('/datasets/import')
def dataset_import(value: DatasetImport):
    return datasets.stage(value.profile_id, datasets.parse_upload(value.filename, value.file_base64), 'File import')


@router.post('/datasets/{aid}/review')
def dataset_review_saved(aid: str):
    return datasets.review_saved(aid)


@router.post('/dataset-reviews/{sid}/preview')
def dataset_preview(sid: str, value: DatasetPreview):
    return datasets.preview(sid, [rule.model_dump() for rule in value.rules], value.terms, value.offset)


@router.post('/dataset-reviews/{sid}/save')
def dataset_save(sid: str, value: DatasetSave):
    return datasets.save_review(sid, value.preview_id, value.reviewed, value.retain_original, value.title)


@router.post('/dataset-reviews/{sid}/discard')
def dataset_discard(sid: str):
    return datasets.discard(sid)


@router.get('/datasets/{aid}/statistics')
def dataset_statistics(aid: str):
    _, rows, _ = datasets.approved(aid)
    return datasets.stats(rows)


@router.get('/datasets/{aid}/privacy')
def dataset_privacy(aid: str):
    try:
        item, _, receipt = datasets.approved(aid)
        return {'reviewed':True, 'original_retained':bool(receipt.get('original')), **item['payload']['privacy']}
    except HTTPException as error:
        if error.status_code not in (403, 409):
            raise
        return {'reviewed':False, 'status':'review required'}


async def analyze_dataset(aid, value):
    if not value.consent_ai:
        raise HTTPException(403, 'Authorize AI analysis of the reviewed working copy.')
    item, rows, receipt = datasets.approved(aid)
    question = datasets.scrub(value.question, receipt['mapping'])
    sample = rows[:100]
    while len(json.dumps(sample)) > 45000:
        sample = sample[:len(sample)//2]
    context = {'sample_rows':[{'row':index + 1, 'values':row} for index, row in enumerate(sample)],
               'sample_size':len(sample), 'statistics':datasets.stats(rows), 'privacy_status':'pseudonymized working copy'}
    result = await ai.structured_task('analyze_dataset', profiles.get_profile(item['profile_id']), question, context, DatasetAnswer)
    # Never attach original rows, mappings, original titles, credentials, or original file metadata.
    result['answer'] = datasets.scrub(result['answer'], receipt['mapping'])
    result['limitations'] = [datasets.scrub(text, receipt['mapping']) for text in result['limitations']]
    result.update(dataset_id=aid, question=question, sample_size=len(sample), row_count=len(rows))
    return result


@router.post('/datasets/{aid}/ask')
async def dataset_ask(aid: str, value: DatasetQuestion):
    return await tracked_ai(analyze_dataset(aid, value))


@router.get("/bootstrap")
def bootstrap():
    values = profiles.list_profiles()
    config = settings()
    if config.get("active_profile") not in {p["id"] for p in values}:
        config = update_settings({"active_profile": "rei"})
    return {"profiles": values, "settings": config, "levels": [dict(zip(("id", "name", "description", "example"), x)) for x in profiles.LEVELS],
            "tools": profiles.TOOLS, "tabs": profiles.TABS, "budget": budget.status(), "connections": connections.public_connections()}


@router.get("/taxonomy")
def taxonomy():
    return {"nodes": list(profiles.taxonomy().values())}


@router.get("/templates/{name}")
def template(name: Literal["rei", "general"]):
    return profiles.template(name)


@router.get("/schema/{name}")
def schema(name: Literal["profile", "quiz", "activity"]):
    return {"profile": profiles.Profile, "quiz": library.Quiz, "activity": library.ActivityInput}[name].model_json_schema()


@router.post("/profiles/save")
def save_profile(value: ProfileSave):
    return profiles.save_profile(value.profile.model_dump(), value.base_revision, value.create)


@router.post("/profiles/action")
def profile_action(value: ProfileAction):
    return profiles.profile_action(value.id, value.action, value.revision)


@router.get("/workspace/{pid}")
def workspace(pid: str):
    return profiles.workspace(pid)


@router.get("/profiles/{pid}/recent-searches")
def profile_recent_searches(pid: str):
    return profile_adaptation.recent_searches(profiles.get_profile(pid))


@router.post("/workspace")
def workspace_save(value: WorkspaceSave):
    return profiles.save_workspace(value.profile_id, value.data, value.revision)


@router.post("/settings")
def settings_save(value: SettingsSave):
    if value.local_only:
        cancel_active()
    return update_settings(value.model_dump())


@router.get("/budget")
def get_budget():
    return budget.status()


@router.post("/budget")
def set_budget(value: budget.BudgetConfig):
    result = budget.configure(value.model_dump())
    if result["blocked"]:
        cancel_active()
    return result


@router.get("/library")
def library_list(q: str = "", profile: str = "", kind: str = "", level: str = "", theme: str = "", after: str = "", before: str = ""):
    return {"activities": library.list_activities(q, profile, kind, level, theme, after, before)}


@router.post("/library")
def library_save(value: library.ActivityInput):
    return library.save_activity(value.model_dump())


@router.get("/library/{aid}")
def activity(aid: str):
    return library.get_activity(aid)


@router.get("/library/{aid}/file")
def activity_file(aid: str):
    path = library.artifact_file(aid)
    media = "application/pdf" if path.suffix == ".pdf" else "text/plain; charset=utf-8"
    return FileResponse(path, media_type=media, headers={"Content-Security-Policy": "sandbox; default-src 'none'"})


@router.post("/library/{aid}/delete")
def activity_delete(aid: str):
    return library.delete_activity(aid)


@router.post("/library/{aid}/restore-profile")
def restore_profile(aid: str, value: RestoreProfile):
    return library.restore_profile(aid, value.consent_sensitive)


@router.get("/library/{aid}/rows")
def dataset_rows(aid: str, offset: int = Query(default=0, ge=0), q: str = ""):
    return library.dataset_rows(aid, offset, q)


@router.post("/quiz/attempt")
def attempt(value: QuizAttempt):
    return library.submit_quiz(value.activity_id, value.answers, value.profile_id)


@router.get("/quiz/history")
def quiz_history(profile_id: str):
    return {"attempts": library.quiz_history(profile_id)}


@router.post("/quiz/history/delete")
def quiz_history_delete(value: QuizHistoryDelete):
    return library.delete_quiz_history(value.profile_id, value.attempt_id)


@router.post("/archives/export")
def archive_export(value: Export):
    return Response(library.export_zip(value.profile_id, value.activity_id, value.include_sensitive), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="OpenBEXI-Discovery.zip"'})


@router.post("/archives/open")
def archive_open(value: ArchiveUpload):
    return library.open_zip(library.decode_file(value.file_base64, library.MAX_ZIP))


@router.get("/archives/{zid}")
def archive_read(zid: str, q: str = ""):
    _, manifest, items = library.read_zip(zid)
    return {"id": zid, "manifest": manifest, "activities": [x for x in items if q.casefold() in json.dumps(x, ensure_ascii=False).casefold()]}


@router.get("/archives/{zid}/file")
def archive_file(zid: str, path: str):
    entries, _, _ = library.read_zip(zid)
    if path not in entries:
        raise HTTPException(404, "Archive entry not found.")
    return Response(entries[path], media_type="application/pdf" if path.endswith(".pdf") else "text/plain; charset=utf-8",
                    headers={"Content-Security-Policy": "sandbox; default-src 'none'"})


@router.post("/archives/import")
def archive_import(value: ArchiveImport):
    return library.import_zip(value.id, value.consent_sensitive)


@router.get("/connections")
def list_connections(profile_id: str = ''):
    return {"connections": [item for item in connections.public_connections() if not profile_id or item.get('profile_id', profile_id) == profile_id]}


@router.post("/connections")
def connection_create(value: Connect):
    if value.file_base64 and value.sensitive and not value.consent_local:
        raise HTTPException(403, "Confirm local retention before uploading a sensitive database.")
    return connections.connect(value.name, value.path, value.file_base64, value.sensitive, value.profile_id)


@router.post("/connections/{cid}/disconnect")
def connection_delete(cid: str):
    return connections.disconnect(cid)


@router.post("/connections/query")
def connection_query(value: DatabaseQuery):
    if value.snapshot:
        return connections.snapshot(value.profile_id, value.connection_id, value.table, value.fields, value.filters, value.offset, value.consent_local)
    return connections.query(value.connection_id, value.table, value.fields, value.filters, value.offset)


async def generate_draft(value):
    if value.sensitive and not value.consent_ai:
        raise HTTPException(403, "Review and authorize this sensitive AI request first.")
    profile = profiles.validate_profile(value.profile.model_dump())
    if value.task != "create_profile":
        current = profiles.get_profile(profile["id"])
        if current["revision"] != profile["revision"]:
            raise HTTPException(409, "Profile changed. Reload before generating.")
    context = {"themes": [profiles.taxonomy()[x] for x in profile["themes"]], "tools": profiles.TOOLS}
    if value.task == "adapt_profile":
        # Adapt the saved revision, never caller-supplied permissions or connections.
        profile = current
        satisfied = [] if value.sensitive else profile_adaptation.satisfied_requests(profile, value.allow_level_change, value.allow_layout_changes)
        repeated = profile_adaptation.repeated_request_result(profile, value.instruction, satisfied)
        if repeated:
            return repeated
        context = profile_adaptation.proposal_context(profile, value.instruction, value.allow_level_change, value.allow_layout_changes)
        # Only requests already reflected by this profile are relevant to duplicate
        # detection; never attach arbitrary research history to a profile request.
        context["requests_already_reflected"] = [item["instruction"] for item in satisfied]
    budget.check_available()
    if not ai.configured():
        raise HTTPException(503, "Connect AI to generate a draft, or use the editable local template.")
    messages, version = compose(value.task, value.instruction, profile, context)
    output_type = profile_adaptation.ProfileProposal if value.task == "adapt_profile" else ProfileTextDraft if value.task.endswith("profile") else library.GeneratedQuiz if value.task == "create_quiz" else Answer
    model, effort = ai.model_name(), ai.reasoning_effort()
    max_output = ai.output_token_limit(effort)
    reservation = budget.reserve(profile["id"], model, messages, max_output)
    response = None
    try:
        import os
        async with ai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url="https://api.openai.com/v1", timeout=240, max_retries=0) as client:
            response = await client.responses.parse(model=model, reasoning={"effort": effort}, input=messages,
                                                    text_format=output_type, max_output_tokens=max_output, store=False)
        if response.output_parsed is None:
            raise ValueError("Incomplete draft")
        output = output_type.model_validate(response.output_parsed.model_dump()).model_dump()
        provenance = {"origin": "ai", "model": model, "generated_at": stamp()}
        if value.task == "adapt_profile":
            output["profile"], output["changes"] = profile_adaptation.build_proposal(
                profile, output, provenance, value.allow_level_change, value.allow_layout_changes)
            output["request_options"] = {"allow_level_change": value.allow_level_change, "allow_layout_changes": value.allow_layout_changes}
            if not output["changes"]:
                output["decision"] = "repeated_request" if output["decision"] == "repeated_request" else "already_matches"
                for field in (*profile_adaptation.FIELDS, "ui"):
                    output[field] = output["profile"][field]
        elif value.task.endswith("profile"):
            changed = {key: text for key, text in output["ui"].items() if text != profile["ui"][key]}
            profile["ui"].update(changed)
            if profile["theme_title"] != output["theme_title"]:
                profile["provenance"]["theme_title"] = provenance
            profile["theme_title"] = output["theme_title"]
            profile["provenance"].update({key: provenance for key in changed})
            output["profile"] = profiles.validate_profile(profile)
            output["changes"] = changed
        output.update(provenance=provenance, reasoning_effort=effort, prompt_version=version, base_revision=profile["revision"])
        archive_profile = profile["id"] if value.task != "create_profile" else settings()["active_profile"]
        record = library.save_activity({"profile_id": archive_profile, "kind": "ai", "title": "AI " + value.task,
                                       "request": "[sensitive request omitted]" if value.sensitive else value.instruction,
                                       "prompts": [] if value.sensitive else messages,
                                       "payload": {"omitted": "Sensitive input/output excluded"} if value.sensitive else output,
                                       "provenance": provenance})
        output["activity_id"] = record["id"]
        return output
    except HTTPException:
        raise
    except Exception as exc:
        raise ai.ai_error(exc) from None
    finally:
        budget.finish(reservation, getattr(response, "usage", None) if response else None)


@router.post("/ai/draft")
async def draft(value: DraftRequest):
    result = await tracked_ai(generate_draft(value))
    if result.get("cached"):
        return JSONResponse(result, headers={"X-Discovery-AI-Reused": "true"})
    return result
