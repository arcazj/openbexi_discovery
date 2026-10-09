"""Read-only SQLite connector. Credentials/paths never enter portable profiles."""
import json
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import HTTPException

from .discovery_store import data_root, identifier, read_json, write_json, stamp, LOCK
from .library import decode_file, save_activity


def config_path():
    return data_root() / ".discovery" / "connections.json"


def connections():
    return read_json(config_path(), {})


def public_connections():
    return [{k: v for k, v in item.items() if k != "path"} for item in connections().values()]


def _db(path):
    target = Path(path).resolve()
    if not target.is_file() or target.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}:
        raise HTTPException(422, "Choose an existing SQLite .db, .sqlite, or .sqlite3 file.")
    private = (data_root() / ".discovery").resolve()
    if private in target.parents and target.parent != private / "databases":
        raise HTTPException(403, "Application-private databases cannot be connected as research data.")
    try:
        db = sqlite3.connect(target.as_uri() + "?mode=ro", uri=True, timeout=2)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        deadline = time.monotonic() + 2
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        return db
    except sqlite3.Error:
        raise HTTPException(422, "Could not open this SQLite database in read-only mode.") from None


def schema(db):
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND sql NOT LIKE '%VIRTUAL%' LIMIT 100").fetchall()
    return {row[0]: [x[1] for x in db.execute('PRAGMA table_info("' + row[0].replace('"', '""') + '")').fetchall()][:100] for row in tables}


def connect(name, path="", file_base64="", sensitive=True):
    if not name.strip() or len(name) > 100:
        raise HTTPException(422, "Give the connection a short name.")
    cid = uuid.uuid4().hex
    if file_base64:
        content = decode_file(file_base64)
        if not content.startswith(b"SQLite format 3\x00"):
            raise HTTPException(422, "The selected file is not SQLite.")
        target = data_root() / ".discovery" / "databases" / (cid + ".sqlite")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        path = str(target)
    db = _db(path)
    try:
        tables = schema(db)
    except sqlite3.Error:
        raise HTTPException(422, "Database schema could not be read.") from None
    finally:
        db.close()
    value = {"id": cid, "name": name.strip(), "type": "sqlite", "path": str(Path(path).resolve()),
             "sensitive": bool(sensitive), "tables": tables, "created_at": stamp(), "read_only": True,
             "storage": "uploaded copy" if file_base64 else "local file"}
    with LOCK:
        items = connections()
        items[cid] = value
        write_json(config_path(), items)
    return {k: v for k, v in value.items() if k != "path"}


def disconnect(cid):
    with LOCK:
        items = connections()
        item = items.pop(identifier(cid), None)
        if not item:
            raise HTTPException(404, "Connection not found.")
        write_json(config_path(), items)
        if item["storage"] == "uploaded copy":
            path = Path(item["path"])
            if path.parent == data_root() / ".discovery" / "databases" and path.stem == cid:
                path.unlink(missing_ok=True)
    return {"disconnected": cid, "message": "Local library snapshots retained; they can be managed separately."}


def query(cid, table, fields, filters=None, offset=0, limit=50):
    item = connections().get(identifier(cid))
    if not item:
        raise HTTPException(404, "Connection not found.")
    if type(offset) is not int or offset < 0 or offset > 1_000_000 or type(limit) is not int or not 1 <= limit <= 100:
        raise HTTPException(422, "Use a bounded page of up to 100 rows.")
    db = _db(item["path"])
    try:
        allowed = schema(db)
        if table not in allowed or not fields or len(fields) > 40 or any(f not in allowed[table] for f in fields):
            raise HTTPException(422, "Select permitted table columns.")
        filters = filters or {}
        if len(filters) > 10 or any(f not in allowed[table] for f in filters):
            raise HTTPException(422, "Unknown filter field.")
        quote = lambda text: '"' + text.replace('"', '""') + '"'
        statement = "SELECT " + ",".join(quote(f) for f in fields) + " FROM " + quote(table)
        values = []
        if filters:
            statement += " WHERE " + " AND ".join(quote(f) + " = ?" for f in filters)
            values = list(filters.values())
        statement += " LIMIT ? OFFSET ?"
        rows = []
        for row in db.execute(statement, (*values, limit, offset)):
            rows.append({key: ("[binary value]" if isinstance(v, bytes) else str(v)[:4000] if isinstance(v, str) else v) for key, v in dict(row).items()})
        return {"connection_id": cid, "source": item["name"], "table": table, "fields": fields, "rows": rows,
                "offset": offset, "limit": limit, "sensitive": item["sensitive"], "captured_at": stamp()}
    except sqlite3.Error:
        raise HTTPException(422, "Read-only query failed or exceeded its two-second limit.") from None
    finally:
        db.close()


def snapshot(pid, cid, table, fields, filters, offset, consent):
    result = query(cid, table, fields, filters, offset)
    return save_activity({"profile_id": pid, "kind": "dataset", "title": result["source"] + " / " + table,
                          "payload": result, "sensitive": result["sensitive"], "consent_local": consent,
                          "provenance": {"origin": "unverified"}})
