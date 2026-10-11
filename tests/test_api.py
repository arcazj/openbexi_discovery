"""Validate API boundaries without depending on public services or an API key."""

import os
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from dotenv import dotenv_values

from backend.app import app

application_module = importlib.import_module("backend.app")


class APIBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"OPENAI_API_KEY": ""})
        self.environment.start()
        self.client = TestClient(app, client=("127.0.0.1", 50000))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.environment.stop()

    def test_health_is_available_without_openai_credentials(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

    def test_ai_defaults_are_astra_xhigh(self):
        with patch.dict(os.environ, {"OPENAI_MODEL": "", "OPENAI_REASONING_EFFORT": ""}):
            ai = self.client.get("/api/health").json()["ai"]
        self.assertEqual(ai["model"], "gpt-6-astra")
        self.assertEqual(ai["reasoning_effort"], "xhigh")

    def test_model_and_reasoning_persist_without_reentering_a_saved_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OPENAI_API_KEY='sk-existing-private-fixture'\nNCBI_EMAIL=research@example.com\n", encoding="utf-8")
            with patch.object(application_module, "ROOT", Path(directory)), patch.dict(os.environ, {"OPENAI_API_KEY": "sk-existing-private-fixture"}):
                for model, effort in [("gpt-6-astra", "xhigh"), ("gpt-6.1-sol", "low")]:
                    response = self.client.post("/api/ai/configure", json={"model": model, "reasoning_effort": effort})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertNotIn("sk-existing-private-fixture", response.text)
                    saved = dotenv_values(path)
                    self.assertEqual(saved["OPENAI_API_KEY"], "sk-existing-private-fixture")
                    self.assertEqual(saved["NCBI_EMAIL"], "research@example.com")
                    self.assertEqual(saved["OPENAI_MODEL"], model)
                    self.assertEqual(saved["OPENAI_REASONING_EFFORT"], effort)
                    with patch.dict(os.environ, saved):
                        current = self.client.get("/api/health").json()["ai"]
                    self.assertEqual(current["model"], model)
                    self.assertEqual(current["reasoning_effort"], effort)

    def test_invalid_ai_preferences_cannot_partially_change_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            original = "OPENAI_MODEL=gpt-6-astra\nOPENAI_REASONING_EFFORT=xhigh\n"
            path.write_text(original, encoding="utf-8")
            with patch.object(application_module, "ROOT", Path(directory)):
                for payload in ({"model": "nonexistent-model"}, {"model": "gpt-6.1-sol", "reasoning_effort": "ultra"}, {}):
                    response = self.client.post("/api/ai/configure", json=payload)
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertEqual(path.read_text(encoding="utf-8"), original)
                original_writer = application_module.set_key
                def fail_second_write(filename, setting, value, **kwargs):
                    if setting == "OPENAI_REASONING_EFFORT":
                        raise OSError("Synthetic write failure")
                    return original_writer(filename, setting, value, **kwargs)
                with patch("backend.app.set_key", side_effect=fail_second_write), patch.dict(os.environ, {"OPENAI_MODEL": "gpt-6-astra", "OPENAI_REASONING_EFFORT": "xhigh"}):
                    response = self.client.post("/api/ai/configure", json={"model": "gpt-6.1-sol", "reasoning_effort": "low"})
                    self.assertEqual(response.status_code, 500)
                    self.assertEqual(path.read_text(encoding="utf-8"), original)
                    self.assertEqual(os.environ["OPENAI_MODEL"], "gpt-6-astra")
                    self.assertEqual(os.environ["OPENAI_REASONING_EFFORT"], "xhigh")
                self.assertEqual(list(Path(directory).glob(".env-*")), [])

    def test_standalone_local_origins_support_health_preflight_and_ai_check(self):
        origins = [
            "http://127.0.0.1:8765", "http://localhost:8775", "http://127.0.0.1:63514",
            "http://localhost:1", "http://127.0.0.1:65535", "http://localhost", "http://127.0.0.1",
            "http://127.0.0.1:8000", "http://localhost:8080",
        ]
        for origin in origins:
            with self.subTest(origin=origin):
                response = self.client.get("/api/health", headers={"Origin": origin})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
                response = self.client.options("/api/ai/check", headers={
                    "Origin": origin, "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                })
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
                with patch("backend.app.ai.check_connection", new=AsyncMock(return_value={"ok": True})) as check:
                    response = self.client.post("/api/ai/check", json={}, headers={"Origin": origin})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
                check.assert_awaited_once()

    def test_untrusted_and_file_origins_cannot_access_ai(self):
        origins = [
            "null", "https://localhost:8765", "https://127.0.0.1:8765", "https://example.com",
            "http://example.com", "http://192.168.1.2:8765", "http://localhost.evil.example:8765",
            "http://127.0.0.1.evil.example:8765", "http://localhost@evil.example:8765",
            "http://user@localhost:8765", "http://localhost:0", "http://localhost:65536",
            "http://127.0.0.1:100000", "http://localhost:8765/", "http://localhost:8765?query",
            "http://localhost:8765#fragment", "http://localhost:", "http://localhost:08765", "",
        ]
        for origin in origins:
            with self.subTest(origin=origin):
                response = self.client.get("/api/health", headers={"Origin": origin})
                self.assertNotIn("access-control-allow-origin", response.headers)
                response = self.client.options("/api/ai/check", headers={
                    "Origin": origin, "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                })
                self.assertEqual(response.status_code, 400, response.text)
                self.assertNotIn("access-control-allow-origin", response.headers)
                with patch("backend.app.ai.check_connection", new=AsyncMock()) as check:
                    response = self.client.post("/api/ai/check", json={}, headers={"Origin": origin})
                self.assertEqual(response.status_code, 403, response.text)
                self.assertIn("serve_frontend.py", response.json()["detail"])
                check.assert_not_awaited()

    def test_ai_check_without_origin_remains_available_to_local_clients(self):
        with patch("backend.app.ai.check_connection", new=AsyncMock(return_value={"ok": True})) as check:
            response = self.client.post("/api/ai/check", json={})
        self.assertEqual(response.status_code, 200, response.text)
        check.assert_awaited_once()

    def test_invalid_search_never_reaches_a_public_source(self):
        invalid_requests = [
            {"query": "", "mode": "topic", "sources": ["pubmed"]},
            {"query": "a" * 5001, "mode": "topic", "sources": ["pubmed"]},
            {"query": "ovarian aging", "mode": "unsupported", "sources": ["pubmed"]},
            {"query": "ovarian aging", "mode": "topic", "sources": ["arbitrary-source"]},
            {"query": "ovarian aging", "mode": "topic", "sources": ["pubmed"], "limit": -1},
        ]
        for payload in invalid_requests:
            with self.subTest(payload=payload):
                response = self.client.post("/api/search", json=payload)
                self.assertEqual(response.status_code, 422, response.text)

    def test_static_routes_do_not_expose_server_or_environment_files(self):
        paths = [
            "/.env", "/.git/config", "/backend/app.py", "/backend/ai.py",
            "/help/../.env", "/help/%2e%2e/.env", "/help/%2e%2e%2f.env",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404, response.text)

    def test_health_never_returns_a_configured_key(self):
        fake_secret = "sk-contract-test-must-not-leak"
        with patch.dict(os.environ, {"OPENAI_API_KEY": fake_secret}):
            response = self.client.get("/api/health")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(fake_secret, response.text)

    def test_missing_ai_key_returns_actionable_error_without_network(self):
        response = self.client.post("/api/ai", json={
            "action": "explain", "query": "ovarian aging", "records": [{
                "id": "pubmed:123456", "source": "pubmed", "type": "publication",
                "title": "Fixture publication", "url": "https://pubmed.ncbi.nlm.nih.gov/123456/",
            }],
        })
        self.assertEqual(response.status_code, 503, response.text)
        self.assertIn("OPENAI_API_KEY", response.json()["detail"])

    def test_one_failed_source_keeps_successful_evidence_and_failure_coverage(self):
        async def retrieve(source, interpretation, limit):
            if source == "pubmed":
                return {"records": [{"id": "pubmed:123456", "title": "Retrieved publication"}],
                        "coverage": {"source": source, "status": "ok", "total": 1, "retrieved": 1}}
            return {"records": [], "coverage": {"source": source, "status": "error", "total": None, "retrieved": 0, "error": "Fixture timeout"}}
        with patch.object(app.state.sources, "search", new=AsyncMock(side_effect=retrieve)):
            response = self.client.post("/api/search", json={"query": "ovarian aging", "mode": "topic", "sources": ["pubmed", "gwas"]})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual([record["id"] for record in result["records"]], ["pubmed:123456"])
        self.assertEqual([coverage["status"] for coverage in result["coverage"]], ["ok", "error"])
        self.assertFalse(result["demo"])

    def test_validation_does_not_echo_accidentally_pasted_key(self):
        secret = "sk-accidentally-pasted-credential"
        response = self.client.post("/api/search", json={"query": "topic", "sources": [secret]})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)

    def test_local_key_configuration_is_persistent_private_and_immediate(self):
        fake_key = "sk-project-fixture-must-not-leak"
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("OPENAI_API_KEY=old-fixture-key\nOPENAI_MODEL=gpt-6.1-sol\nNCBI_EMAIL=research@example.com\n", encoding="utf-8")
            with patch.object(application_module, "ROOT", Path(directory)), patch.dict(os.environ, {"OPENAI_MODEL": "gpt-6.1-sol"}), patch("backend.app.ai.check_connection", new=AsyncMock()) as check:
                response = self.client.post("/api/ai/configure", json={"api_key": fake_key}, headers={"Origin": "http://127.0.0.1:8765"})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()["configured"])
                self.assertEqual(response.json()["model"], "gpt-6.1-sol")
                self.assertFalse(response.json()["accessible"])
                self.assertNotIn(fake_key, response.text)
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertEqual(response.headers["access-control-allow-origin"], "http://127.0.0.1:8765")
                self.assertEqual(os.environ["OPENAI_API_KEY"], fake_key)
                saved = env_file.read_text(encoding="utf-8")
                self.assertIn("OPENAI_API_KEY='" + fake_key + "'", saved)
                self.assertNotIn("old-fixture-key", saved)
                self.assertIn("OPENAI_MODEL=gpt-6.1-sol", saved)
                self.assertIn("NCBI_EMAIL=research@example.com", saved)
                health = self.client.get("/api/health")
                self.assertTrue(health.json()["ai"]["configured"])
                self.assertNotIn(fake_key, health.text)
                check.assert_not_awaited()

    def test_installed_key_is_saved_in_private_profile_and_not_packaged_assets(self):
        fake_key = "sk-installed-fixture-private-only"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "installed-assets"
            private = root / "private-profile"
            assets.mkdir()
            private.mkdir()
            (assets / ".env").write_text("DO_NOT_CHANGE=asset-fixture\n", encoding="utf-8")
            with patch.object(application_module, "ROOT", assets), patch.dict(os.environ, {"REI_DATA_DIR": str(private)}):
                response = self.client.post("/api/ai/configure", json={"api_key": fake_key})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn(fake_key, response.text)
                self.assertIn(fake_key, (private / ".env").read_text(encoding="utf-8"))
                self.assertEqual((assets / ".env").read_text(encoding="utf-8"), "DO_NOT_CHANGE=asset-fixture\n")


    def test_invalid_key_configuration_never_changes_disk_or_environment(self):
        invalid_values = ["", "sk-short", "not-an-openai-key-that-is-long-enough", "sk-" + "x" * 510, "sk-fixture-key\nwith-control-characters"]
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("NCBI_EMAIL=research@example.com\n", encoding="utf-8")
            with patch.object(application_module, "ROOT", Path(directory)):
                for value in invalid_values:
                    with self.subTest(value_length=len(value)):
                        response = self.client.post("/api/ai/configure", json={"api_key": value})
                        self.assertEqual(response.status_code, 422, response.text)
                        if value:
                            self.assertNotIn(value, response.text)
                        self.assertEqual(os.environ["OPENAI_API_KEY"], "")
                        self.assertEqual(env_file.read_text(encoding="utf-8"), "NCBI_EMAIL=research@example.com\n")

    def test_remote_peer_cannot_configure_key_even_with_local_origin_or_forwarded_address(self):
        fake_key = "sk-project-fixture-must-not-leak"
        with TestClient(app, client=("192.0.2.10", 50000)) as remote_client, patch("backend.app.set_key") as save:
            response = remote_client.post("/api/ai/configure", json={"api_key": fake_key}, headers={
                "Origin": "http://localhost:8765", "X-Forwarded-For": "127.0.0.1",
            })
        self.assertEqual(response.status_code, 403, response.text)
        self.assertNotIn(fake_key, response.text)
        self.assertEqual(os.environ["OPENAI_API_KEY"], "")
        save.assert_not_called()

    def test_untrusted_origin_cannot_configure_key(self):
        fake_key = "sk-project-fixture-must-not-leak"
        with patch("backend.app.set_key") as save:
            for origin in ["null", "https://example.com", "http://localhost.evil.example:8765"]:
                response = self.client.post("/api/ai/configure", json={"api_key": fake_key}, headers={"Origin": origin})
                self.assertEqual(response.status_code, 403, response.text)
                self.assertNotIn(fake_key, response.text)
        save.assert_not_called()

    def test_key_configuration_write_failure_is_sanitized_and_keeps_current_key(self):
        fake_key = "sk-project-fixture-must-not-leak"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "existing-private-fixture"}), patch("backend.app.set_key", side_effect=PermissionError(fake_key)):
            response = self.client.post("/api/ai/configure", json={"api_key": fake_key})
            self.assertEqual(response.status_code, 500, response.text)
            self.assertIn("writable", response.json()["detail"])
            self.assertNotIn(fake_key, response.text)
            self.assertNotIn("existing-private-fixture", response.text)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "existing-private-fixture")


if __name__ == "__main__":
    unittest.main()
