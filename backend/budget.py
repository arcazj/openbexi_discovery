"""Durable, transactional AI allowance reservations, independent of profiles."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import HTTPException
from pydantic import Field

from .discovery_store import ROOT, data_root, read_json, stamp, require_online
from .profiles import Strict


class BudgetConfig(Strict):
    period: Literal["daily", "monthly", "cumulative"] = "monthly"
    token_limit: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    cost_limit: Optional[float] = Field(default=None, ge=0, le=1_000_000)


@contextmanager
def transaction():
    path = data_root() / ".discovery" / "usage.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS usage (id TEXT PRIMARY KEY, at TEXT, profile TEXT, model TEXT, status TEXT, input_tokens INTEGER, output_tokens INTEGER, cached_tokens INTEGER, cost REAL, rates TEXT)")
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def configuration(db):
    row = db.execute("SELECT value FROM config WHERE id=1").fetchone()
    return json.loads(row[0]) if row else {**BudgetConfig().model_dump(), "since": "1970-01-01T00:00:00+00:00"}


def bounds(config):
    now = datetime.now(timezone.utc)
    if config["period"] == "daily":
        from datetime import timedelta
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif config["period"] == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    else:
        return config["since"], None
    return start.isoformat(), end.isoformat()


def summary(db):
    config = configuration(db)
    start, end = bounds(config)
    rows = [dict(r) for r in db.execute("SELECT * FROM usage WHERE at >= ? ORDER BY at", (start,))]
    tokens = sum(r["input_tokens"] + r["output_tokens"] for r in rows)
    cost = sum(r["cost"] or 0 for r in rows)
    unknown = any(r["cost"] is None for r in rows)
    reasons = []
    if config["token_limit"] is not None and tokens >= config["token_limit"]:
        reasons.append("Token limit reached")
    if config["cost_limit"] is not None and (unknown or cost >= config["cost_limit"]):
        reasons.append("Cost is uncertain" if unknown else "Estimated cost limit reached")
    breakdown, daily_usage = {}, {}
    for row in rows:
        key = row["profile"] + ":" + row["model"]
        day = row["at"][:10]  # Stored request timestamps are UTC.
        initial = {"profile": row["profile"], "model": row["model"], "requests": 0, "tokens": 0, "estimated_usd": 0, "unknown_cost": False}
        for group in (breakdown.setdefault(key, dict(initial)), daily_usage.setdefault((day, key), dict(initial, date=day))):
            group["requests"] += 1
            group["tokens"] += row["input_tokens"] + row["output_tokens"]
            group["estimated_usd"] += row["cost"] or 0
            group["unknown_cost"] |= row["cost"] is None
    return {"config": config, "start": start, "reset_at": end, "timezone": "UTC", "updated_at": stamp(),
            "requests": len(rows), "input_tokens": sum(r["input_tokens"] for r in rows),
            "output_tokens": sum(r["output_tokens"] for r in rows), "total_tokens": tokens,
            "estimated_usd": None if unknown else round(cost, 6), "known_usd": round(cost, 6),
            "reserved_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in rows if r["status"] != "complete"),
            "pending_requests": sum(r["status"] != "complete" for r in rows),
            "remaining_tokens": None if config["token_limit"] is None else max(0, config["token_limit"] - tokens),
            "remaining_usd": None if config["cost_limit"] is None or unknown else max(0, config["cost_limit"] - cost),
            "blocked": bool(reasons), "reason": "; ".join(reasons), "breakdown": list(breakdown.values()),
            "daily_usage": sorted(daily_usage.values(), key=lambda row: row["date"], reverse=True),
            "pricing": read_json(ROOT / "templates" / "pricing.json")}


def status():
    with transaction() as db:
        return summary(db)


def configure(value):
    validated = BudgetConfig.model_validate(value).model_dump()
    with transaction() as db:
        old = configuration(db)
        # The first configured period establishes cumulative accounting permanently.
        since = old["since"] if old["since"] != "1970-01-01T00:00:00+00:00" else stamp()
        db.execute("INSERT OR REPLACE INTO config VALUES(1, ?)", (json.dumps({**validated, "since": since}),))
        return summary(db)


def rate(model):
    return read_json(ROOT / "templates" / "pricing.json", {}).get("models", {}).get(model)


def estimated_cost(rates, input_tokens, output_tokens, cached=0, writes=0):
    if not rates:
        return None
    return ((max(0, input_tokens - cached - writes) * rates["input"] + cached * rates["cached"] + writes * rates["write"])
            + output_tokens * rates["output"]) / 1_000_000


def reserve(profile, model, messages, max_output, web_calls=0):
    require_online()
    # UTF-8 bytes plus framing/schema allowance intentionally overestimates input.
    input_tokens = len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) + 16000
    rates = rate(model)
    if web_calls and rates:
        rates = {**rates, "web_search_call": read_json(ROOT / "templates" / "pricing.json")["web_search_call"]}
        # Allow for retrieved web context; this remains a conservative estimate.
        input_tokens += web_calls * 32000
    cost = estimated_cost(rates, input_tokens, max_output)
    if rates:
        cost = max(cost, (input_tokens * rates["write"] + max_output * rates["output"]) / 1_000_000)
        cost += web_calls * rates.get("web_search_call", 0)
    with transaction() as db:
        current = summary(db)
        if current["blocked"]:
            raise HTTPException(423, "AI paused — " + current["reason"] + ". Open AI settings.")
        if current["remaining_tokens"] is not None and input_tokens + max_output > current["remaining_tokens"]:
            raise HTTPException(423, "AI paused — this request exceeds the remaining token allowance. Open AI settings.")
        if current["config"]["cost_limit"] is not None and (cost is None or cost > (current["remaining_usd"] or 0)):
            raise HTTPException(423, "AI paused — insufficient estimated cost allowance or unknown model pricing. Open AI settings.")
        rid = uuid.uuid4().hex
        db.execute("INSERT INTO usage VALUES(?,?,?,?,?,?,?,?,?,?)", (rid, stamp(), profile, model, "reserved", input_tokens, max_output, 0, cost, json.dumps(rates)))
        return rid


def finish(rid, usage=None, web_calls=None):
    with transaction() as db:
        row = db.execute("SELECT * FROM usage WHERE id=?", (rid,)).fetchone()
        if not row or row["status"] == "complete":
            return
        if usage is None:
            db.execute("UPDATE usage SET status='uncertain' WHERE id=?", (rid,))
            return
        value = usage.model_dump() if hasattr(usage, "model_dump") else usage
        inp, out = int(value["input_tokens"]), int(value["output_tokens"])
        details = value.get("input_tokens_details") or {}
        cached = min(inp, int(details.get("cached_tokens") or 0))
        writes = min(inp - cached, int(details.get("cache_write_tokens") or 0))
        rates = json.loads(row["rates"])
        cost = estimated_cost(rates, inp, out, cached, writes)
        if rates and "web_search_call" in rates:
            cost = None if web_calls is None else cost + web_calls * rates["web_search_call"]
        db.execute("UPDATE usage SET status='complete', input_tokens=?, output_tokens=?, cached_tokens=?, cost=? WHERE id=?", (inp, out, cached, cost, rid))


def check_available():
    require_online()
    current = status()
    if current["blocked"]:
        raise HTTPException(423, "AI paused — " + current["reason"] + ". Open AI settings.")
