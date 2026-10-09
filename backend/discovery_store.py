"""Local, atomic persistence. Run the local application with one server worker."""
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
LOCK = threading.RLock()
ID = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")
SECRET = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}|(?i:bearer\s+)[A-Za-z0-9._-]{12,}")


def stamp():
    return datetime.now(timezone.utc).isoformat()


def data_root():
    return Path(os.getenv("DISCOVERY_DATA_DIR") or os.getenv("REI_DATA_DIR") or ROOT).resolve()


def library_root():
    return Path(os.getenv("DISCOVERY_LIBRARY_DIR") or data_root() / "discovery_library").resolve()


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise HTTPException(422, "Invalid local identifier.")
    return value


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise HTTPException(500, "A local data file cannot be read. Restore a backup before continuing.") from None


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep atomic-write names short enough for standard Windows path limits.
    temp = path.with_name(".tmp-" + uuid.uuid4().hex[:16])
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def redact(value):
    if isinstance(value, dict):
        return {k: ("[omitted]" if re.search(r"password|secret|api.?key|authorization|credential", k, re.I)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        result = SECRET.sub("[credential omitted]", value)
        key = os.getenv("OPENAI_API_KEY", "")
        return result.replace(key, "[credential omitted]") if len(key) > 10 else result
    return value


def settings():
    return read_json(data_root() / ".discovery" / "settings.json", {"active_profile": "rei", "local_only": False})


def update_settings(values):
    with LOCK:
        result = {**settings(), **values}
        write_json(data_root() / ".discovery" / "settings.json", result)
        return result


def require_online():
    if settings().get("local_only"):
        raise HTTPException(423, "Local-only mode is on. Use the library or turn it off in AI settings.")
