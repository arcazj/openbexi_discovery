"""Portable local activities and bounded, non-executing ZIP archives."""
import base64
import copy
import csv
import hashlib
import io
import json
import shutil
import uuid
import zipfile
from collections import OrderedDict
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from pydantic import Field, model_validator

from .discovery_store import LOCK, data_root, library_root, identifier, read_json, write_json, stamp, redact, SECRET
from .profiles import Strict, Provenance, get_profile

MAX_FILE = 8 * 1024 * 1024
MAX_ZIP = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
EXTENSIONS = {".pdf", ".md", ".txt", ".csv", ".json"}
OPEN_ARCHIVES = OrderedDict()


class QuizQuestion(Strict):
    question: str = Field(min_length=1, max_length=2000)
    choices: List[str] = Field(min_length=2, max_length=8)
    answer: int = Field(ge=0, le=7)
    explanation: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def valid_answer(self):
        if self.answer >= len(self.choices):
            raise ValueError("The answer must refer to a choice.")
        return self


class Quiz(Strict):
    title: str = Field(min_length=1, max_length=200)
    questions: List[QuizQuestion] = Field(min_length=1, max_length=50)


class GeneratedQuizQuestion(QuizQuestion):
    choices: List[str] = Field(min_length=4, max_length=4)
    answer: int = Field(ge=0, le=3)

    @model_validator(mode="after")
    def distinct_choices(self):
        choices = [choice.strip().casefold() for choice in self.choices]
        if not all(choices) or len(set(choices)) != len(choices):
            raise ValueError("Provide four distinct, nonempty choices.")
        return self


class GeneratedQuiz(Quiz):
    questions: List[GeneratedQuizQuestion] = Field(min_length=8, max_length=8)


class ActivityInput(Strict):
    profile_id: str = "rei"
    kind: Literal["document", "dataset", "note", "quiz", "attempt", "search", "ai", "workspace", "connection"]
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(default="", max_length=250000)
    payload: Dict[str, Any] = Field(default_factory=dict)
    request: str = Field(default="", max_length=100000)
    prompts: List[Dict[str, Any]] = Field(default_factory=list, max_length=10)
    provenance: Provenance = Field(default_factory=lambda: Provenance(origin="user"))
    sensitive: bool = False
    consent_local: bool = False
    parent_id: Optional[str] = None
    filename: str = Field(default="", max_length=200)
    file_base64: str = Field(default="", max_length=MAX_FILE * 2)
    status: Literal["complete", "failed", "canceled"] = "complete"


class DocumentUpdate(Strict):
    base_revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(default="", max_length=250000)
    sensitive: bool = False
    consent_local: bool = False
    filename: str = Field(default="", max_length=200)
    file_base64: Optional[str] = Field(default=None, max_length=MAX_FILE * 2)


def decode_file(value, limit=MAX_FILE):
    try:
        content = base64.b64decode(value, validate=True)
    except ValueError:
        raise HTTPException(422, "Invalid file encoding.") from None
    if len(content) > limit:
        raise HTTPException(413, "File exceeds the local size limit.")
    return content


def prepare_attachment(filename, encoded):
    name = Path(filename).name
    if (name != filename or "/" in name or "\\" in name or ":" in name
            or Path(name).suffix.lower() not in EXTENSIONS):
        raise HTTPException(422, "Upload a PDF, Markdown, text, CSV, or JSON file.")
    content = decode_file(encoded)
    text = None
    if Path(name).suffix.lower() == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(422, "This file is not a PDF.")
    else:
        try:
            text = redact(content.decode("utf-8-sig"))
        except UnicodeDecodeError:
            raise HTTPException(422, "Text files must use UTF-8 encoding.") from None
        content = text.encode("utf-8")
    if SECRET.search(content.decode("latin1")):
        raise HTTPException(422, "Remove credentials from this file before saving.")
    return "document" + Path(name).suffix.lower(), content, text


def save_activity(value):
    item = ActivityInput.model_validate(value)
    profile = get_profile(item.profile_id)
    if item.sensitive and not item.consent_local:
        raise HTTPException(403, "Explicit permission is required to retain sensitive content locally.")
    if len(json.dumps(item.payload)) > 500000:
        raise HTTPException(413, "Activity data is too large.")
    if item.kind == "quiz" and not item.file_base64:
        item.payload = Quiz.model_validate(item.payload).model_dump()
    if item.parent_id:
        parent = get_activity(item.parent_id)
        if parent["profile_id"] != item.profile_id:
            raise HTTPException(422, "An activity revision must stay in its originating profile.")
        if parent.get("sensitive"):
            item.sensitive = True
            if not item.consent_local:
                raise HTTPException(403, "Confirm retention of this sensitive revision.")
        if parent.get("provenance", {}).get("origin") in {"ai", "ai_edited"}:
            item.provenance = Provenance(**{**parent["provenance"], "origin": "ai_edited"})
    content = b""
    filename = ""
    text = None
    if item.file_base64 or item.filename:
        filename, content, text = prepare_attachment(item.filename, item.file_base64)
        if text is not None:
            item.content = text[:250000]
            if item.kind == "quiz":
                item.payload = Quiz.model_validate_json(text).model_dump()
    aid = uuid.uuid4().hex
    record = redact(item.model_dump(exclude={"file_base64", "consent_local"}))
    record.update(id=aid, created_at=stamp(), filename=filename, original_filename=item.filename,
                  profile_snapshot=profile, themes=profile["themes"], learning_level=profile["learning_level"],
                  schema_version="1.1")
    if item.kind == "document":
        record.update(revision=1, content_truncated=text is not None and len(text) > 250000)
    folder = library_root() / "profiles" / item.profile_id / "activities" / aid
    with LOCK:
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if filename:
                (folder / filename).write_bytes(content)
            write_json(folder / "activity.json", record)
            write_json(library_root() / "profiles" / item.profile_id / "profile.json", profile)
            write_json(library_root() / "manifest.json", {"schema_version": "1.1", "updated_at": stamp()})
        except BaseException:
            # Only the newly allocated activity directory is removed on failure.
            shutil.rmtree(folder)
            raise
    return record


def activity_paths():
    root = library_root()
    return list(root.glob("profiles/*/activities/*/activity.json")) + list(root.glob("imports/*/profiles/*/activities/*/activity.json"))


def find_path(aid):
    identifier(aid)
    for path in activity_paths():
        if path.parent.name == aid:
            return path
    raise HTTPException(404, "Saved activity not found.")


def get_activity(aid):
    with LOCK:
        item = read_json(find_path(aid))
        # Older documents have no revision or preview-length metadata.
        if item["kind"] == "document":
            item.setdefault("revision", 1)
            if "content_truncated" not in item:
                item["content_truncated"] = bool(item.get("filename") and not item["filename"].endswith(".pdf")
                    and len(artifact_file(aid).read_text(encoding="utf-8-sig")) > 250000)
        return item


def update_document(aid, value):
    update = DocumentUpdate.model_validate(value)
    with LOCK:
        path = find_path(aid)
        folder = path.parent.resolve()
        if library_root().resolve() not in folder.parents or path.parent.is_symlink() or path.is_symlink():
            raise HTTPException(403, "Invalid activity storage path.")
        current = get_activity(aid)
        if current["kind"] != "document":
            raise HTTPException(422, "Choose a saved document to edit.")
        if update.base_revision != current.get("revision", 1):
            raise HTTPException(409, "This document changed in another window. Reopen it before editing again.")
        sensitive = bool(current.get("sensitive") or update.sensitive)
        if sensitive and not update.consent_local:
            raise HTTPException(403, "Confirm retention of this sensitive document.")
        record = copy.deepcopy(current)
        record.update(title=update.title, content=update.content, sensitive=sensitive,
                      revision=update.base_revision + 1, updated_at=stamp())
        attachment = None
        old_filename = current.get("filename", "")
        if old_filename and (Path(old_filename).name != old_filename or "/" in old_filename or "\\" in old_filename):
            raise HTTPException(403, "Invalid attachment storage path.")
        if update.file_base64 is not None:
            filename, attachment, text = prepare_attachment(update.filename, update.file_base64)
            record["original_filename"] = update.filename
            record["content_truncated"] = text is not None and len(text) > 250000
            if text is not None:
                record["content"] = text[:250000]
        elif update.filename:
            raise HTTPException(422, "Include the replacement file contents.")
        elif old_filename and not old_filename.endswith(".pdf") and update.content != current["content"]:
            if current.get("content_truncated"):
                raise HTTPException(422, "This text is a partial preview. Upload a replacement file to edit the full document.")
            filename = old_filename
            attachment = redact(update.content).encode("utf-8")
        if current.get("provenance", {}).get("origin") in {"ai", "ai_edited"}:
            record["provenance"]["origin"] = "ai_edited"
        record = redact(record)
        new_file = None
        try:
            if attachment is not None:
                # Write a new attachment, then atomically publish its pointer in activity.json.
                # A failed save leaves the previous document and attachment intact.
                record["filename"] = "doc-" + uuid.uuid4().hex[:16] + Path(filename).suffix
                new_file = folder / record["filename"]
                new_file.write_bytes(attachment)
            write_json(path, record)
        except BaseException:
            if new_file is not None:
                new_file.unlink(missing_ok=True)
            raise
        if new_file is not None and old_filename:
            try:
                (folder / old_filename).unlink(missing_ok=True)
            except OSError:
                # Windows may still have the previous PDF open. Deletion of the
                # activity removes the entire folder, including any retired files.
                pass
        return record


def delete_activity(aid):
    with LOCK:
        path = find_path(aid)
        root = library_root().resolve()
        folder = path.parent.resolve()
        if root not in folder.parents or folder.name != identifier(aid) or path.parent.is_symlink():
            raise HTTPException(403, "Invalid activity storage path.")
        shutil.rmtree(folder)
        from .private_store import delete
        delete('dataset', aid)
    return {"deleted": aid}


def list_activities(query="", profile="", kind="", level="", theme="", after="", before=""):
    records = []
    for path in activity_paths():
        item = read_json(path)
        if ((profile and item["profile_id"] != profile) or (kind and item["kind"] != kind)
                or (level and item["learning_level"] != level) or (theme and theme not in item["themes"])
                or (after and item["created_at"][:10] < after) or (before and item["created_at"][:10] > before)):
            continue
        searchable = " ".join(str(item.get(k, "")) for k in ("title", "content", "request", "payload"))
        if query.casefold() not in searchable.casefold():
            continue
        summary = item.get("content") or item.get("request") or item.get("payload", {}).get("text") or ""
        if item["kind"] == "dataset":
            rows = item.get("payload", {}).get("rows")
            summary = (str(len(rows)) + " saved rows" if isinstance(rows, list) else "Saved dataset")
            summary += " · " + item.get("payload", {}).get("privacy", {}).get("status", "Privacy review available")
        elif item["kind"] == "quiz":
            summary = str(len(item.get("payload", {}).get("questions", []))) + " questions · Practice and review your answers"
        entry = {k: item.get(k) for k in ("id", "profile_id", "kind", "title", "created_at", "learning_level", "themes", "sensitive", "provenance", "parent_id")}
        entry["summary"] = " ".join(str(summary).split())[:180] or ("Saved " + item["kind"])
        records.append(entry)
    return sorted(records, key=lambda r: r["created_at"], reverse=True)[:1000]


def artifact_file(aid):
    path = find_path(aid)
    name = read_json(path).get("filename", "")
    if not name or Path(name).name != name:
        raise HTTPException(404, "This activity has no attached file.")
    result = path.parent / name
    if result.is_symlink() or not result.is_file():
        raise HTTPException(404, "Attached file missing.")
    return result


def dataset_rows(aid, offset=0, query=""):
    item = get_activity(aid)
    if item["kind"] != "dataset":
        raise HTTPException(422, "Choose a saved dataset.")
    if item.get("filename", "").endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(artifact_file(aid).read_text(encoding="utf-8"))))
    else:
        value = item["payload"].get("rows")
        if value is None:
            try:
                value = json.loads(item["content"])
            except ValueError:
                raise HTTPException(422, "Use a CSV or a JSON array of row objects.") from None
        rows = value
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise HTTPException(422, "Dataset must contain row objects.")
    if query:
        rows = [r for r in rows if query.casefold() in json.dumps(r, ensure_ascii=False).casefold()]
    return {"rows": rows[offset:offset + 50], "total": len(rows), "offset": offset, "captured_at": item["created_at"]}


def submit_quiz(aid, answers, profile_id=None):
    item = get_activity(aid)
    if item["kind"] != "quiz":
        raise HTTPException(422, "Choose a saved quiz.")
    if profile_id and profile_id != item["profile_id"]:
        raise HTTPException(422, "Save the attempt in the quiz's original profile.")
    quiz = Quiz.model_validate(item["payload"])
    if len(answers) != len(quiz.questions) or any(type(a) is not int or a < 0 or a >= len(q.choices) for a, q in zip(answers, quiz.questions)):
        raise HTTPException(422, "Answer every question.")
    score = sum(a == q.answer for a, q in zip(answers, quiz.questions))
    return save_activity({"profile_id": profile_id or item["profile_id"], "kind": "attempt", "title": "Quiz attempt: " + quiz.title,
                          "payload": {"quiz_id": aid, "quiz_title": quiz.title, "quiz_level": item["learning_level"],
                                      "quiz_provenance": item["provenance"],
                                      "questions": quiz.model_dump()["questions"], "answers": answers,
                                      "score": score, "total": len(answers)},
                          "sensitive": item["sensitive"], "consent_local": item["sensitive"]})


def quiz_history(profile_id):
    identifier(profile_id)
    attempts = []
    for path in activity_paths():
        item = read_json(path)
        if item["kind"] == "attempt" and item["profile_id"] == profile_id:
            payload = item["payload"]
            attempts.append({"id": item["id"], "title": payload.get("quiz_title", item["title"]),
                             "created_at": item["created_at"], "learning_level": payload.get("quiz_level", item["learning_level"]),
                             "score": payload["score"], "total": payload["total"]})
    return sorted(attempts, key=lambda item: item["created_at"], reverse=True)


def delete_quiz_history(profile_id, attempt_id=None):
    with LOCK:
        attempts = quiz_history(profile_id)
        if attempt_id is not None:
            identifier(attempt_id)
            attempts = [item for item in attempts if item["id"] == attempt_id]
            if not attempts:
                raise HTTPException(404, "Quiz attempt not found in this profile.")
        for item in attempts:
            delete_activity(item["id"])
    return {"deleted": len(attempts)}


def export_zip(profile="", activity="", include_sensitive=False):
    output = io.BytesIO()
    files = {}
    excluded = []
    with LOCK, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        items = [read_json(path) for path in activity_paths()]
        if not activity:
            # Capture current settings and briefs even when a profile has no materials yet.
            from .profiles import list_profiles, workspace
            for current in list_profiles():
                if profile and current["id"] != profile:
                    continue
                snapshot = copy.deepcopy(current)
                snapshot["connection_ids"] = []
                stored = workspace(current["id"])
                payload = redact(stored["data"])
                signature = hashlib.sha256(json.dumps([snapshot, payload], sort_keys=True).encode()).hexdigest()[:32]
                items.append({"id": signature, "profile_id": current["id"], "kind": "workspace",
                    "title": current["name"] + " — profile and workspace backup", "schema_version": "1.1",
                    "created_at": stored.get("updated_at", current["updated_at"]), "profile_snapshot": snapshot,
                    "themes": current["themes"], "learning_level": current["learning_level"], "payload": payload,
                    "content": "", "request": "", "prompts": [], "filename": "", "parent_id": None,
                    "provenance": {"origin": "user"}, "sensitive": bool(payload.get("sensitive")), "status": "complete"})
        for item in items:
            if (profile and item["profile_id"] != profile) or (activity and item["id"] != activity):
                continue
            if item.get("sensitive") and not include_sensitive:
                excluded.append(item["id"])
                continue
            prefix = "profiles/" + identifier(item["profile_id"]) + "/activities/" + identifier(item["id"]) + "/"
            portable = redact(item)
            entries = {}
            if item.get("filename"):
                # Preserve the existing portable ZIP format after an in-place edit.
                portable["filename"] = "document" + Path(item["filename"]).suffix.lower()
                entries[prefix + portable["filename"]] = artifact_file(item["id"]).read_bytes()
            entries[prefix + "activity.json"] = json.dumps(portable, ensure_ascii=False).encode("utf-8")
            for name, content in entries.items():
                if len(files) >= 1000 or sum(f["size"] for f in files.values()) + len(content) > MAX_EXPANDED:
                    raise HTTPException(413, "Export a smaller selection (64 MB / 1000 entries maximum).")
                files[name] = {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                archive.writestr(name, content)
        archive.writestr("manifest.json", json.dumps({"schema_version": "1.1", "created_at": stamp(), "files": files, "excluded_sensitive": excluded}))
    result = output.getvalue()
    if len(result) > MAX_ZIP:
        raise HTTPException(413, "Export a smaller selection (32 MB compressed maximum).")
    exports = library_root() / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / (uuid.uuid4().hex + ".zip")).write_bytes(result)
    return result


def restore_profile(aid, consent_sensitive=False):
    """Explicitly restore reviewed history as a new inactive profile, never overwrite."""
    from .profiles import save_profile, save_workspace
    item = get_activity(aid)
    if item.get("sensitive") and not consent_sensitive:
        raise HTTPException(403, "Authorize local retention before restoring sensitive work.")
    value = copy.deepcopy(item["profile_snapshot"])
    value["name"] = (value["name"] + " (restored)")[:100]
    value["connection_ids"] = []
    allowed = {}
    if item["kind"] == "workspace" and item.get("payload"):
        allowed = {k: v for k, v in item["payload"].items() if k in {"workspace", "prefs", "query", "sensitive"}}
        state = allowed.get("workspace", {})
        prefs = allowed.get("prefs", {})
        if (not isinstance(state, dict) or not isinstance(prefs, dict)
                or not isinstance(state.get("questions", []), list)
                or len(state.get("questions", [])) > 200
                or any(not isinstance(q, dict) or not isinstance(q.get("id"), str) or not isinstance(q.get("title"), str) for q in state.get("questions", []))
                or not isinstance(state.get("constraints", {}), dict)
                or not isinstance(allowed.get("query", ""), str)
                or len(json.dumps(allowed)) > 2_000_000):
            raise HTTPException(422, "This historical workspace cannot be restored. Its original files remain available.")
        # An imported workspace cannot change the server endpoint or AI settings.
        allowed["prefs"] = {k: v for k, v in prefs.items() if k in {"sources", "limit", "mode", "recent"}}
        if "sources" in allowed["prefs"] and (not isinstance(prefs["sources"], list) or any(x not in {"pubmed", "ensembl", "gwas"} for x in prefs["sources"])):
            raise HTTPException(422, "Unsupported sources in the historical workspace.")
    created = save_profile(value, create=True)
    if allowed:
        save_workspace(created["id"], allowed, 0)
    return created


def validate_zip(content):
    if len(content) > MAX_ZIP:
        raise HTTPException(413, "Archive exceeds 32 MB.")
    entries = {}
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 1001:
                raise ValueError("Too many entries")
            total = 0
            case_names = set()
            for info in infos:
                name = info.filename
                parts = PurePosixPath(name).parts
                if (name.casefold() in case_names or not parts or name.startswith("/") or "\\" in name or ":" in name
                        or any(p in {"..", "."} for p in parts) or info.is_dir()
                        or (info.external_attr >> 16) & 0o170000 == 0o120000
                        or info.file_size > MAX_FILE or info.flag_bits & 1):
                    raise ValueError("Unsafe archive entry")
                case_names.add(name.casefold())
                with archive.open(info) as stream:
                    data = stream.read(MAX_FILE + 1)
                total += len(data)
                if len(data) > MAX_FILE or total > MAX_EXPANDED:
                    raise ValueError("Archive expands beyond limit")
                entries[name] = data
        manifest = json.loads(entries.pop("manifest.json"))
        if manifest.get("schema_version") != "1.1" or set(manifest["files"]) != set(entries):
            raise ValueError("Unsupported manifest")
        for name, data in entries.items():
            expected = manifest["files"][name]
            if expected["size"] != len(data) or expected["sha256"] != hashlib.sha256(data).hexdigest():
                raise ValueError("Checksum mismatch")
            parts = PurePosixPath(name).parts
            if len(parts) != 5 or parts[0] != "profiles" or parts[2] != "activities":
                raise ValueError("Unknown archive layout")
            identifier(parts[1]); identifier(parts[3])
            if parts[4] != "activity.json" and parts[4] not in {"document" + x for x in EXTENSIONS}:
                raise ValueError("Unsupported artifact")
        activities = []
        for name, data in entries.items():
            if name.endswith("/activity.json"):
                item = json.loads(data)
                parts = PurePosixPath(name).parts
                if item["id"] != parts[3] or item["profile_id"] != parts[1]:
                    raise ValueError("Mismatched activity ID")
                from .profiles import validate_profile
                validate_profile(item["profile_snapshot"], check_themes=False)
                ActivityInput.model_validate({k: v for k, v in item.items() if k in ActivityInput.model_fields})
                if item.get("filename") and item["filename"] not in {"document" + x for x in EXTENSIONS}:
                    raise ValueError("Unsupported attachment name")
                if item.get("filename") and str(PurePosixPath(name).parent / item["filename"]) not in entries:
                    raise ValueError("Missing artifact")
                activities.append(item)
        return entries, manifest, activities
    except (ValueError, KeyError, TypeError, zipfile.BadZipFile, OSError, RuntimeError):
        raise HTTPException(422, "Archive is corrupt, unsafe, or uses an unsupported format.") from None


def open_zip(content):
    entries, manifest, activities = validate_zip(content)
    zid = uuid.uuid4().hex
    # Browsing is transient; only an explicit import/export retains an archive on disk.
    with LOCK:
        while OPEN_ARCHIVES and (len(OPEN_ARCHIVES) >= 4 or sum(len(v) for v in OPEN_ARCHIVES.values()) + len(content) > MAX_EXPANDED):
            OPEN_ARCHIVES.popitem(last=False)
        OPEN_ARCHIVES[(str(data_root()), zid)] = content
    return {"id": zid, "manifest": manifest, "activities": activities}


def read_zip(zid):
    with LOCK:
        content = OPEN_ARCHIVES.get((str(data_root()), identifier(zid)))
    if content is None:
        raise HTTPException(404, "This ZIP preview expired. Open the original file again.")
    return validate_zip(content)


def import_zip(zid, consent_sensitive=False):
    entries, manifest, activities = read_zip(zid)
    if any(x.get("sensitive") for x in activities) and not consent_sensitive:
        raise HTTPException(403, "Confirm local retention of the sensitive items listed in this archive.")
    token = uuid.uuid4().hex
    staging = library_root() / (".import-" + token)
    target = library_root() / "imports" / token
    imported = []
    skipped = 0
    with LOCK:
        staging.mkdir(parents=True)
        try:
            id_map = {}
            for item in activities:
                try:
                    old = read_json(find_path(item["id"]))
                    if old.get("filename"):
                        old["filename"] = "document" + Path(old["filename"]).suffix.lower()
                except HTTPException as exc:
                    if exc.status_code != 404:
                        raise
                    old = None
                if old == item:
                    skipped += 1
                    continue
                id_map[item["id"]] = uuid.uuid4().hex if old else item["id"]
            for original in activities:
                if original["id"] not in id_map:
                    continue
                item = redact(json.loads(json.dumps(original)))
                item["id"] = id_map[original["id"]]
                if item.get("parent_id") in id_map:
                    item["parent_id"] = id_map[item["parent_id"]]
                if item.get("payload", {}).get("quiz_id") in id_map:
                    item["payload"]["quiz_id"] = id_map[item["payload"]["quiz_id"]]
                prefix = "profiles/" + item["profile_id"] + "/activities/"
                folder = staging / prefix / item["id"]
                write_json(folder / "activity.json", item)
                if item.get("filename"):
                    data = entries[prefix + original["id"] + "/" + item["filename"]]
                    if SECRET.search(data.decode("latin1")):
                        raise HTTPException(422, "Archive contains credentials; remove them before importing.")
                    (folder / item["filename"]).write_bytes(data)
                imported.append(item["id"])
            target.parent.mkdir(parents=True, exist_ok=True)
            staging.replace(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return {"imported": imported, "skipped": skipped, "message": "Historical items imported. Existing profiles were not changed."}
