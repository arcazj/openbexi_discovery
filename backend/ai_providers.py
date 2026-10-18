"""Provider configuration and a small structured-generation transport.

Credentials stay server-side. Compatible providers use Chat Completions; OpenAI
keeps the Responses SDK in ai.py so its cited web search remains unchanged.
"""
import json
import os
import re
from types import SimpleNamespace
from urllib.parse import quote, urlsplit

import httpx
from fastapi import HTTPException
from openai.lib._pydantic import to_strict_json_schema

LEVELS = ("low", "medium", "high", "xhigh", "max")
PROVIDERS = {
    "openai": dict(name="OpenAI", prefix="OPENAI", model="gpt-6-astra", effort="xhigh",
                   url="https://api.openai.com/v1", keys="https://platform.openai.com/api-keys", levels=LEVELS),
    "anthropic": dict(name="Anthropic", prefix="ANTHROPIC", model="claude-opus-5-5", effort="medium",
                      url="https://api.anthropic.com/v1", keys="https://platform.claude.com/settings/keys", levels=LEVELS),
    "gemini": dict(name="Google Gemini", prefix="GEMINI", model="gemini-3.8-flash", effort="medium",
                   url="https://generativelanguage.googleapis.com/v1beta/openai", keys="https://aistudio.google.com/apikey",
                   levels=("low", "medium", "high")),
    "deepseek": dict(name="DeepSeek", prefix="DEEPSEEK", model="deepseek-flash", effort="high",
                     url="https://api.deepseek.com", keys="https://platform.deepseek.com/api_keys", levels=("low", "high", "max")),
    "openrouter": dict(name="OpenRouter", prefix="OPENROUTER", model="", effort="medium",
                       url="https://openrouter.ai/api/v1", keys="https://openrouter.ai/settings/keys", levels=LEVELS),
    "custom": dict(name="Other (OpenAI-compatible)", prefix="CUSTOM_AI", model="", effort="medium",
                   url="", keys="", levels=()),
}


def current_id():
    value = os.getenv("AI_PROVIDER", "openai").strip().lower() or "openai"
    if value not in PROVIDERS:
        raise HTTPException(422, "Choose a supported provider in Connect AI.")
    return value


def config(provider=None):
    provider = provider or current_id()
    item = PROVIDERS[provider]
    prefix = item["prefix"]
    return dict(item, id=provider, key=os.getenv(prefix + "_API_KEY", "").strip(),
                model=os.getenv(prefix + "_MODEL", item["model"]).strip() or item["model"],
                effort=os.getenv(prefix + "_REASONING_EFFORT", item["effort"]).strip().lower() or item["effort"],
                url=os.getenv("CUSTOM_AI_BASE_URL", "").strip() if provider == "custom" else item["url"])


def configured(provider=None):
    value = config(provider)["key"]
    return bool(value and value.lower() not in {"your_api_key", "your_api_key_here", "your-key-here", "replace-me"})


def public_config(provider=None):
    item = config(provider)
    if item["id"] == "custom" and item["url"]:
        try:
            item["url"] = validate_url(item["url"])
        except ValueError:
            item["url"] = ""  # Never expose credentials from a hand-edited URL.
    return {"id": item["id"], "name": item["name"], "configured": configured(item["id"]),
            "model": item["model"], "reasoning_effort": item["effort"], "reasoning_levels": list(item["levels"]),
            "key_url": item["keys"], "base_url": item["url"], "web_search": item["id"] == "openai"}


def status():
    item = public_config()
    return {**item, "provider": item["id"], "providers": [public_config(p) for p in PROVIDERS]}


def validate_effort(effort):
    item = config()
    if effort not in (item["levels"] or ("medium",)):
        raise HTTPException(422, "Choose a reasoning level supported by " + item["name"] + " in Connect AI.")
    return effort


def accounting_model(model):
    return model if current_id() == "openai" else current_id() + ":" + model


def validate_url(value):
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
                 and not parsed.query and not parsed.fragment and parsed.port != 0
                 and not re.search(r"[\s\\]", value))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Enter an HTTPS API base URL without credentials, a query, or a fragment.")
    return value.rstrip("/")


def anthropic_schema(value):
    # Claude's grammar does not implement these constraints; Pydantic enforces
    # the original schema locally before generated content can be saved.
    if isinstance(value, list):
        return [anthropic_schema(v) for v in value]
    if not isinstance(value, dict):
        return value
    unsupported = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength",
                   "minItems", "maxItems", "pattern", "default"}
    result = {}
    for key, val in value.items():
        if key in unsupported:
            continue
        # Property names may themselves be JSON Schema keywords.
        result[key] = {k: anthropic_schema(v) for k, v in val.items()} if key in {"properties", "$defs"} else anthropic_schema(val)
    return result


def normalized_usage(raw, anthropic=False):
    if not isinstance(raw, dict):
        return None
    inp, out = (raw.get("input_tokens"), raw.get("output_tokens")) if anthropic else (raw.get("prompt_tokens"), raw.get("completion_tokens"))
    cached = raw.get("cache_read_input_tokens", 0) if anthropic else (raw.get("prompt_tokens_details") or {}).get("cached_tokens", raw.get("prompt_cache_hit_tokens", 0))
    writes = raw.get("cache_creation_input_tokens", 0) if anthropic else 0
    if not all(type(value) is int and value >= 0 for value in (inp, out, cached, writes)):
        return None  # Retain the reservation if the API omits reliable usage.
    return {"input_tokens": inp + cached + writes if anthropic else inp, "output_tokens": out,
            "input_tokens_details": {"cached_tokens": cached, "cache_write_tokens": writes}}


class ProviderClient:
    def __init__(self, timeout=240):
        self.config = config()
        if not self.config["model"]:
            raise HTTPException(422, "Enter a model ID in Connect AI.")
        if self.config["id"] == "custom":
            try:
                self.config["url"] = validate_url(self.config["url"])
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
        headers = ({"x-api-key": self.config["key"], "anthropic-version": "2023-06-01"}
                   if self.config["id"] == "anthropic" else {"Authorization": "Bearer " + self.config["key"]})
        self.http = httpx.AsyncClient(base_url=self.config["url"].rstrip("/") + "/", timeout=timeout,
                                     follow_redirects=False, headers=headers)
        self.responses = self
        self.models = self

    async def __aenter__(self):
        await self.http.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self.http.__aexit__(*args)

    async def request(self, method, path, **kwargs):
        name = self.config["name"]
        try:
            response = await self.http.request(method, path, **kwargs)
        except httpx.HTTPError:
            raise HTTPException(503, "Cannot reach " + name + ". Check the connection and API base URL.") from None
        # Never return the provider body: it may echo credentials or research.
        if response.status_code in (401, 403):
            raise HTTPException(response.status_code, name + " rejected the API key or model permissions. Update Connect AI.")
        if response.status_code in (402, 429):
            raise HTTPException(429, name + " reported a credit, quota, or rate limit. Check your provider account and retry.")
        if response.status_code == 404:
            raise HTTPException(404, name + " could not find the model or API endpoint. Check Connect AI.")
        if not 200 <= response.status_code < 300:
            raise HTTPException(502, name + " rejected this request. Check that the model supports JSON output and the selected reasoning level.")
        try:
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError()
            return body
        except ValueError:
            raise HTTPException(502, name + " returned an invalid API response.") from None

    async def retrieve(self, model):
        provider = self.config["id"]
        if provider == "openrouter":
            # The model catalogue is public; authenticate separately.
            await self.request("GET", "key")
        if provider in {"openrouter", "deepseek", "custom"}:
            body = await self.request("GET", "models")
            if not any(item.get("id") == model for item in body.get("data", []) if isinstance(item, dict)):
                raise HTTPException(404, "The selected model is absent from this provider's model list. Check its model ID.")
            return body
        return await self.request("GET", "models/" + quote(model, safe=""))

    async def parse(self, *, model, reasoning, input, text_format, max_output_tokens, store=False):
        provider = self.config["id"]
        effort = reasoning["effort"]
        schema = to_strict_json_schema(text_format)
        # Full constraints remain in the prompt even when a provider's grammar
        # supports only a subset. Validation below always uses the original.
        instruction = "Return only a JSON object matching this JSON schema: " + json.dumps(schema)
        messages = [dict(message) for message in input]
        messages.insert(0, {"role": "system", "content": instruction})
        if provider == "anthropic":
            body = {"model": model, "max_tokens": max_output_tokens,
                    "system": "\n\n".join(m["content"] for m in messages if m["role"] in {"system", "developer"}),
                    "messages": [m for m in messages if m["role"] not in {"system", "developer"}],
                    "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": anthropic_schema(schema)}}}
            result = await self.request("POST", "messages", json=body)
            content = "".join(p.get("text", "") for p in result.get("content", []) if p.get("type") == "text")
            complete = result.get("stop_reason") == "end_turn"
            usage = normalized_usage(result.get("usage"), anthropic=True)
        else:
            body = {"model": model, "messages": messages, "max_tokens": max_output_tokens,
                    "response_format": {"type": "json_object"}}
            if provider in {"gemini", "openrouter"}:
                body["response_format"] = {"type": "json_schema", "json_schema": {"name": text_format.__name__, "strict": True, "schema": schema}}
            if provider in {"gemini", "deepseek"}:
                body["reasoning_effort"] = effort
            if provider == "deepseek":
                body["thinking"] = {"type": "enabled"}
            if provider == "openrouter":
                body["reasoning"] = {"effort": effort, "exclude": True}
                body["provider"] = {"require_parameters": True}
            result = await self.request("POST", "chat/completions", json=body)
            choice = (result.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content") or ""
            complete = choice.get("finish_reason") == "stop"
            usage = normalized_usage(result.get("usage"))
        parsed = None
        if complete:
            try:
                parsed = text_format.model_validate_json(content)
            except (ValueError, TypeError):
                pass
        # Return usage even for refusals, malformed JSON and truncation.
        return SimpleNamespace(output_parsed=parsed, usage=usage, status="completed" if complete else "incomplete", output=[])
