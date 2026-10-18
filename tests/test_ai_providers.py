"""Provider contracts, credential isolation and persistence without paid calls."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from dotenv import dotenv_values
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field

from backend import ai, ai_providers as providers, budget, profiles, search
from backend.app import app
from backend.discovery_store import redact


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=2, max_length=100)


class ProviderConfigurationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        env = {"DISCOVERY_DATA_DIR": directory.name, "DISCOVERY_LIBRARY_DIR": "", "AI_PROVIDER": "openai"}
        for provider in providers.PROVIDERS.values():
            for suffix in ("_API_KEY", "_MODEL", "_REASONING_EFFORT"):
                env[provider["prefix"] + suffix] = ""
        env["CUSTOM_AI_BASE_URL"] = ""
        environment = patch.dict(os.environ, env)
        environment.start()
        self.addCleanup(environment.stop)
        self.client = TestClient(app, client=("127.0.0.1", 50000))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def save(self, **values):
        return self.client.post("/api/ai/configure", json=values)

    def test_openai_default_and_all_choices_without_keys(self):
        del os.environ["AI_PROVIDER"]
        health = self.client.get("/api/health").json()["ai"]
        self.assertEqual(health["provider"], "openai")
        self.assertEqual(health["model"], "gpt-6-astra")
        self.assertEqual(len(health["providers"]), 6)
        self.assertFalse(any(p["configured"] for p in health["providers"]))

    def test_provider_switch_restores_separate_credentials_and_survives_restart(self):
        for provider in providers.PROVIDERS:
            key = "sk-fixture-" + provider + "-private-token"
            values = {"provider": provider, "api_key": key}
            if provider in {"custom", "openrouter"}:
                values["model"] = "organization/model-id"
            if provider == "custom":
                values["base_url"] = "https://compatible.example/v1/"
            result = self.save(**values)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertNotIn(key, result.text)
            self.assertEqual(providers.config()["key"], key)
        saved = dotenv_values(self.root / ".env")
        self.assertEqual(saved["AI_PROVIDER"], "custom")
        self.assertEqual(saved["CUSTOM_AI_BASE_URL"], "https://compatible.example/v1")
        with patch.dict(os.environ, saved, clear=True):
            self.assertEqual(providers.current_id(), "custom")
            self.assertEqual(ai.model_name(), "organization/model-id")
            for provider in providers.PROVIDERS:
                os.environ["AI_PROVIDER"] = provider
                self.assertEqual(providers.config()["key"], "sk-fixture-" + provider + "-private-token")
        result = self.save(provider="openai")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(ai.model_name(), "gpt-6-astra")
        self.assertEqual(ai.reasoning_effort(), "xhigh")
        self.assertEqual(providers.config()["key"], "sk-fixture-openai-private-token")
        self.assertNotIn("private-token", self.client.get("/api/health").text)

    def test_unsaved_provider_does_not_inherit_openai_key(self):
        self.save(provider="openai", api_key="sk-private-fixture-token")
        result = self.save(provider="gemini")
        self.assertFalse(result.json()["configured"])
        self.assertEqual(providers.config()["key"], "")

    def test_invalid_configuration_is_atomic_and_secret_free(self):
        self.save(provider="openai", api_key="sk-private-fixture-token")
        original = (self.root / ".env").read_bytes()
        bad = [dict(provider="unknown"), dict(provider="gemini", reasoning_effort="max"),
               dict(provider="deepseek", reasoning_effort="medium"), dict(provider="custom", model="model", base_url="http://example.org/v1"),
               dict(provider="custom", model="model", base_url="https://user:private@example.org/v1"),
               dict(provider="custom", model="model", base_url="https://example.org/v1?key=private"),
               dict(provider="gemini", api_key="private\nkey"), dict(provider="openai", api_key="invalid-private-key"),
               dict(provider="gemini", base_url="https://other.example"), dict(provider="openrouter")]
        for values in bad:
            result = self.save(**values)
            self.assertEqual(result.status_code, 422, result.text)
            self.assertNotIn("invalid-private-key", result.text)
            self.assertEqual((self.root / ".env").read_bytes(), original)
            self.assertEqual(providers.current_id(), "openai")

    def test_endpoint_change_cannot_send_an_existing_key_elsewhere(self):
        result = self.save(provider="custom", model="model", base_url="https://first.example/v1", api_key="fixture-custom-key")
        self.assertEqual(result.status_code, 200, result.text)
        result = self.save(provider="custom", base_url="https://second.example/v1")
        self.assertEqual(result.status_code, 422)
        self.assertEqual(providers.config()["url"], "https://first.example/v1")

    def test_non_openai_tokens_are_redacted_in_archives(self):
        os.environ["GEMINI_API_KEY"] = "AIza-fixture-non-sk-key"
        self.assertEqual(redact({"text": "key AIza-fixture-non-sk-key", "api_key": "another"}),
                         {"text": "key [credential omitted]", "api_key": "[omitted]"})

    def test_usage_dates_group_by_day_profile_and_model_without_changing_totals(self):
        with patch.object(budget, "bounds", return_value=("2026-10-01T00:00:00+00:00", None)):
            for day, model, tokens in (("16", "gpt-6-astra", 100), ("17", "gemini:model", 200), ("17", "gemini:model", 300)):
                with patch.object(budget, "stamp", return_value="2026-10-" + day + "T23:59:00+00:00"):
                    rid = budget.reserve("rei", model, [], 500)
                    budget.finish(rid, {"input_tokens": tokens, "output_tokens": 10})
            usage = budget.status()
        self.assertEqual(usage["total_tokens"], 630)
        self.assertEqual([(r["date"], r["requests"], r["tokens"]) for r in usage["daily_usage"]],
                         [("2026-10-17", 2, 520), ("2026-10-16", 1, 110)])
        self.assertTrue(usage["daily_usage"][0]["unknown_cost"])
        self.assertEqual(sum(r["tokens"] for r in usage["breakdown"]), 630)


class ProviderTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"DISCOVERY_DATA_DIR": directory.name, "DISCOVERY_LIBRARY_DIR": "",
                                              "OPENAI_API_KEY": "sk-openai-must-not-be-sent"})
        environment.start()
        self.addCleanup(environment.stop)
        self.http_class = httpx.AsyncClient

    def configure(self, provider):
        item = providers.PROVIDERS[provider]
        os.environ.update(AI_PROVIDER=provider, CUSTOM_AI_BASE_URL="https://compatible.example/v1")
        os.environ[item["prefix"] + "_API_KEY"] = "fixture-" + provider + "-secret"
        os.environ[item["prefix"] + "_MODEL"] = item["model"] or "org/model"
        os.environ[item["prefix"] + "_REASONING_EFFORT"] = item["effort"]

    def transport(self, handler):
        return patch.object(providers.httpx, "AsyncClient", side_effect=lambda **kwargs: self.http_class(transport=httpx.MockTransport(handler), **kwargs))

    def response(self, provider, content='{"answer":"Verified response"}', complete=True):
        if provider == "anthropic":
            return {"content": [{"type": "text", "text": content}], "stop_reason": "end_turn" if complete else "max_tokens",
                    "usage": {"input_tokens": 100, "cache_read_input_tokens": 20, "cache_creation_input_tokens": 30, "output_tokens": 10}}
        return {"choices": [{"message": {"content": content}, "finish_reason": "stop" if complete else "length"}],
                "usage": {"prompt_tokens": 150, "completion_tokens": 10, "prompt_tokens_details": {"cached_tokens": 20}}}

    async def test_native_and_compatible_generation_routing_schema_reasoning_and_usage(self):
        for provider in ("anthropic", "gemini", "deepseek", "openrouter", "custom"):
            with self.subTest(provider=provider):
                self.configure(provider)
                seen = []
                def handler(request):
                    seen.append(request)
                    return httpx.Response(200, json=self.response(provider))
                with self.transport(handler), patch.object(ai, "AsyncOpenAI") as openai:
                    result = await ai.structured_task("explain", profiles.get_profile("rei"), "Explain evidence", {}, Result)
                openai.assert_not_called()
                self.assertEqual(result["answer"], "Verified response")
                self.assertEqual(result["provenance"]["provider"], provider)
                self.assertEqual(len(seen), 1)
                request = seen[0]
                self.assertNotIn("sk-openai-must-not-be-sent", str(request.headers))
                self.assertEqual(request.url.host, httpx.URL(providers.config()["url"]).host)
                body = json.loads(request.content)
                if provider == "anthropic":
                    self.assertEqual(request.headers["x-api-key"], "fixture-anthropic-secret")
                    self.assertEqual(body["output_config"]["effort"], "medium")
                    self.assertNotIn("maxLength", json.dumps(body["output_config"]["format"]["schema"]))
                    self.assertIn("maxLength", body["system"])
                else:
                    self.assertEqual(request.headers["authorization"], "Bearer fixture-" + provider + "-secret")
                    self.assertTrue(request.url.path.endswith("/chat/completions"))
                    if provider in {"gemini", "deepseek"}:
                        self.assertEqual(body["reasoning_effort"], providers.config()["effort"])
                    if provider == "openrouter":
                        self.assertEqual(body["reasoning"], {"effort": "medium", "exclude": True})
                        self.assertTrue(body["provider"]["require_parameters"])
                    if provider == "custom":
                        self.assertNotIn("reasoning_effort", body)
                        self.assertNotIn("reasoning", body)
                entry = next(r for r in budget.status()["breakdown"] if r["model"] == providers.accounting_model(ai.model_name()))
                self.assertEqual(entry["tokens"], 160)
                self.assertTrue(entry["unknown_cost"])

    async def test_invalid_or_truncated_generation_still_records_tokens(self):
        self.configure("gemini")
        for content, complete in (("not json", True), ('{"answer":"x"}', True), ('{"answer":"valid"}', False)):
            with self.transport(lambda request: httpx.Response(200, json=self.response("gemini", content, complete))):
                with self.assertRaises(HTTPException) as error:
                    await ai.structured_task("explain", profiles.get_profile("rei"), "Explain evidence", {}, Result)
                self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(budget.status()["total_tokens"], 480)
        self.assertEqual(budget.status()["pending_requests"], 0)

    async def test_missing_usage_keeps_a_conservative_reservation(self):
        self.configure("custom")
        result = self.response("custom")
        result["usage"] = {}
        with self.transport(lambda request: httpx.Response(200, json=result)):
            await ai.structured_task("explain", profiles.get_profile("rei"), "Explain evidence", {}, Result)
        self.assertEqual(budget.status()["pending_requests"], 1)
        self.assertGreater(budget.status()["reserved_tokens"], 0)

    async def test_authentication_errors_and_redirects_never_leak_or_forward_keys(self):
        self.configure("gemini")
        for status in (401, 403, 429, 500, 302):
            requests = []
            def handler(request):
                requests.append(request)
                return httpx.Response(status, json={"error": "fixture-gemini-secret"}, headers={"Location": "https://evil.example"})
            with self.transport(handler):
                with self.assertRaises(HTTPException) as error:
                    await ai.check_connection()
            self.assertNotIn("fixture-gemini-secret", str(error.exception.detail))
            self.assertEqual(len(requests), 1)

    async def test_openrouter_checks_key_before_public_model_catalogue(self):
        self.configure("openrouter")
        paths = []
        def handler(request):
            paths.append(request.url.path)
            return httpx.Response(200, json={"data": [{"id": "org/model"}]} if request.url.path.endswith("models") else {"data": {}})
        with self.transport(handler):
            result = await ai.check_connection()
        self.assertTrue(result["accessible"])
        self.assertEqual(paths, ["/api/v1/key", "/api/v1/models"])

    async def test_specific_source_search_uses_selected_provider_and_web_search_is_explicit(self):
        from backend.app import SearchRequest
        self.configure("gemini")
        def handler(request):
            return httpx.Response(200, json=self.response("gemini", json.dumps({"queries": [{"source": "pubmed", "query": "BRCA1", "mode": "gene"}]})))
        service = AsyncMock()
        service.search.return_value = {"records": [], "coverage": {"source": "pubmed", "status": "ok"}}
        with self.transport(handler), patch.object(ai, "AsyncOpenAI") as openai:
            result = await search.search(SearchRequest(query="BRCA1", scope="specific", sources=["pubmed"]), service)
            self.assertEqual(result["provider"], "gemini")
            self.assertEqual(result["model"], providers.config()["model"])
            service.search.assert_awaited_once()
            with self.assertRaises(HTTPException) as error:
                await search.search(SearchRequest(query="cosmology", scope="overall"), service)
            self.assertIn("currently integrated with OpenAI", str(error.exception.detail))
            openai.assert_not_called()
