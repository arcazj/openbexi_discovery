"""Profile proposals, opt-ins, history relevance, and durable rollback."""
import copy
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.app import app
from backend import budget, library, profiles, profile_adaptation


class ProfileAdaptationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DISCOVERY_DATA_DIR": self.temp.name, "DISCOVERY_LIBRARY_DIR": "", "OPENAI_API_KEY": "sk-test-fixture"})
        self.env.start()
        self.client = TestClient(app, client=("127.0.0.1", 50001))
        self.client.__enter__()
        self.original = profiles.get_profile("rei")

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()
        self.temp.cleanup()

    def proposal(self, **changes):
        value = {key: copy.deepcopy(self.original[key]) for key in (*profile_adaptation.FIELDS, "ui")}
        value.update(goal="Investigate ovarian aging and fertility outcomes.", explanation="Focus the goal and search examples on ovarian aging.")
        value["ui"]["examples"] = ["ovarian aging fertility outcomes"]
        value.update(changes)
        return profile_adaptation.ProfileProposal.model_validate(value)

    def draft(self, proposed, **request_changes):
        parse = AsyncMock(return_value=SimpleNamespace(output_parsed=proposed, usage={"input_tokens": 100, "output_tokens": 50}))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=SimpleNamespace(responses=SimpleNamespace(parse=parse)))
        context.__aexit__ = AsyncMock(return_value=False)
        request = {"task": "adapt_profile", "profile": self.original, "instruction": "Focus my profile on ovarian aging.", **request_changes}
        with patch("backend.ai.AsyncOpenAI", return_value=context):
            response = self.client.post("/api/discovery/ai/draft", json=request)
        return response, parse

    def test_proposal_has_diff_and_does_not_save_or_send_other_material(self):
        library.save_activity({"profile_id": "rei", "kind": "note", "title": "Private note", "content": "Do not send this private note."})
        caller_profile = copy.deepcopy(self.original)
        caller_profile.update(goal="Forged caller goal", connection_ids=["private-connection"], hidden_source_ids=["pubmed"])
        response, parse = self.draft(self.proposal(), profile=caller_profile)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(profiles.get_profile("rei"), self.original)
        self.assertEqual({c["field"] for c in result["changes"]}, {"goal", "ui.examples"})
        self.assertEqual(result["profile"]["connection_ids"], self.original["connection_ids"])
        self.assertEqual(result["profile"]["hidden_source_ids"], self.original["hidden_source_ids"])
        self.assertEqual(result["profile"]["provenance"]["goal"]["origin"], "ai")
        sent = json.dumps(parse.await_args.kwargs["input"])
        self.assertNotIn("private note", sent)
        self.assertNotIn("private-connection", sent)
        self.assertNotIn("Forged caller goal", sent)
        self.assertFalse(parse.await_args.kwargs["store"])
        self.assertEqual(budget.status()["total_tokens"], 150)
        self.assertEqual(library.get_activity(result["activity_id"])["profile_snapshot"], self.original)

    def test_level_and_layout_require_opt_in(self):
        proposal = self.proposal(learning_level="researcher", tabs=["evidence", "quizzes"], panels=["tip"])
        response, _ = self.draft(proposal)
        self.assertEqual(response.status_code, 200, response.text)
        for field in ("learning_level", "tabs", "default_tab", "panels"):
            self.assertEqual(response.json()["profile"][field], self.original[field])
        response, _ = self.draft(proposal, allow_level_change=True, allow_layout_changes=True)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["profile"]["learning_level"], "researcher")
        self.assertEqual(response.json()["profile"]["tabs"], ["evidence", "quizzes"])

    def test_invalid_theme_stale_profile_and_sensitive_consent(self):
        response, _ = self.draft(self.proposal(themes=["invented-theme"]))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(profiles.get_profile("rei"), self.original)
        response, parse = self.draft(self.proposal(), sensitive=True)
        self.assertEqual(response.status_code, 403)
        parse.assert_not_called()
        response, _ = self.draft(self.proposal(), sensitive=True, consent_ai=True, instruction="Sensitive instruction")
        self.assertEqual(response.status_code, 200, response.text)
        archived = library.get_activity(response.json()["activity_id"])
        self.assertEqual(archived["request"], "[sensitive request omitted]")
        self.assertEqual(archived["prompts"], [])
        self.assertNotIn("profile", archived["payload"])
        profiles.profile_action("rei", "reset", 1)
        response, parse = self.draft(self.proposal())
        self.assertEqual(response.status_code, 409)
        parse.assert_not_called()

    def search(self, query, pid="rei", **changes):
        return library.save_activity({"profile_id": pid, "kind": "search", "title": "Search", "request": query,
                                      "payload": {"coverage": [{"status": "ok"}], "records": []}, **changes})

    def recent(self, pid="rei"):
        response = self.client.get("/api/discovery/profiles/" + pid + "/recent-searches")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_recent_related_searches_are_local_scoped_bounded_and_private(self):
        self.assertEqual(self.recent()["searches"], [])
        self.search("ovarian aging")
        self.assertTrue(self.recent()["latest_related"])
        self.search("quantum entanglement")
        self.assertFalse(self.recent()["latest_related"])
        self.assertEqual([s["query"] for s in self.recent()["searches"]], ["ovarian aging"])
        self.search("PCOS", status="canceled")
        self.search("PCOS", payload={"demo": True})
        self.search("PCOS", payload={"coverage": [{"status": "error"}]})
        self.search("PCOS private", sensitive=True, consent_local=True)
        self.search("[sensitive query omitted]", payload={"omitted": "Sensitive search content excluded"})
        self.assertFalse(self.recent()["latest_related"])
        self.assertEqual(len(self.recent()["searches"]), 1)
        other = profiles.save_profile(profiles.template("general"), create=True)
        self.search("BRCA1", pid=other["id"])
        self.assertNotIn("BRCA1", json.dumps(self.recent()))
        for index in range(7):
            self.search("ovarian aging " + str(index))
        self.search("ovarian aging 6")
        result = self.recent()
        self.assertTrue(result["latest_related"])
        self.assertEqual(len(result["searches"]), 5)
        self.assertEqual(len({s["query"] for s in result["searches"]}), 5)
        self.assertEqual(budget.status()["total_tokens"], 0)

    def test_apply_and_rollback_restore_profile_and_retain_history(self):
        original_note = library.save_activity({"profile_id": "rei", "kind": "note", "title": "Keep this note"})
        response, _ = self.draft(self.proposal(themes=["02.01"]))
        saved = self.client.post("/api/discovery/profiles/save", json={"profile": response.json()["profile"], "base_revision": 1}).json()
        self.assertEqual(saved["revision"], 2)
        stale = self.client.post("/api/discovery/profiles/action", json={"id": "rei", "revision": 1, "action": "undo"})
        self.assertEqual(stale.status_code, 409)
        restored = self.client.post("/api/discovery/profiles/action", json={"id": "rei", "revision": 2, "action": "undo"}).json()
        self.assertEqual(restored["revision"], 3)
        for field in (*profile_adaptation.FIELDS, "ui", "provenance", "connection_ids", "hidden_source_ids"):
            self.assertEqual(restored[field], self.original[field])
        self.assertEqual(library.get_activity(original_note["id"])["profile_snapshot"], self.original)
        self.assertEqual(library.get_activity(response.json()["activity_id"])["profile_snapshot"], self.original)

    def test_theme_context_is_bounded_and_includes_existing_and_requested_themes(self):
        context = profile_adaptation.proposal_context(self.original, "Study Quantum Physics", False, False)
        self.assertLessEqual(len(context["available_themes"]), 100)
        ids = {node["id"] for node in context["available_themes"]}
        self.assertTrue(set(self.original["themes"]).issubset(ids))
        self.assertIn("02.01", ids)

    def test_rollback_restores_original_ai_provenance_after_manual_edit(self):
        response, _ = self.draft(self.proposal())
        generated = profiles.save_profile(response.json()["profile"], 1)
        edited = copy.deepcopy(generated)
        edited["goal"] = "My edited goal"
        edited = profiles.save_profile(edited, 2)
        self.assertEqual(edited["provenance"]["goal"]["origin"], "ai_edited")
        restored = profiles.profile_action("rei", "undo", 3)
        self.assertEqual(restored["goal"], generated["goal"])
        self.assertEqual(restored["provenance"], generated["provenance"])

    def test_repeating_an_applied_update_is_a_local_no_op_even_without_tokens(self):
        response, _ = self.draft(self.proposal())
        generated = profiles.save_profile(response.json()["profile"], 1)
        # A fresh request can reconstruct the match from disk, including after restart.
        for instruction in ("Focus my profile on ovarian aging.", "Please   focus my profile on ovarian aging!"):
            with patch("backend.budget.check_available") as availability:
                repeat, parse = self.draft(self.proposal(), profile=generated, instruction=instruction)
            self.assertEqual(repeat.status_code, 200, repeat.text)
            self.assertEqual(repeat.json()["decision"], "repeated_request")
            self.assertEqual(repeat.json()["changes"], [])
            self.assertEqual(repeat.headers["X-Discovery-AI-Reused"], "true")
            self.assertTrue(repeat.json()["cached"])
            parse.assert_not_called()
            availability.assert_not_called()
        self.assertEqual(profiles.get_profile("rei"), generated)
        self.assertEqual(budget.status()["total_tokens"], 150)
        self.assertEqual(len(library.list_activities(profile="rei", kind="ai")), 1)

    def test_new_requirements_and_rollback_are_not_blocked_by_a_previous_request(self):
        response, _ = self.draft(self.proposal())
        generated = profiles.save_profile(response.json()["profile"], 1)
        update, parse = self.draft(self.proposal(goal="Explore ovarian aging in people under 30."), profile=generated,
                                   instruction="Focus my profile on ovarian aging in people under 30.")
        self.assertEqual(update.status_code, 200, update.text)
        self.assertTrue(update.json()["changes"])
        parse.assert_awaited_once()
        sent = json.loads(parse.await_args.kwargs["input"][1]["content"].split("\n", 1)[1])
        self.assertEqual(sent["reference_data"]["requests_already_reflected"], ["Focus my profile on ovarian aging."])
        for changed in ("Do not focus my profile on ovarian aging.", "Focus my profile on ovarian aging in people under 30."):
            self.assertNotEqual(profile_adaptation.normalized_request(changed), profile_adaptation.normalized_request("Focus my profile on ovarian aging."))
        self.assertNotEqual(profile_adaptation.normalized_request("age < 30"), profile_adaptation.normalized_request("age > 30"))
        rolled_back = profiles.profile_action("rei", "undo", generated["revision"])
        response, parse = self.draft(self.proposal(), profile=rolled_back)
        self.assertTrue(response.json()["changes"])
        parse.assert_awaited_once()

    def test_semantic_repeat_decision_preserves_every_value_even_if_ai_rephrases(self):
        response, _ = self.draft(self.proposal())
        generated = profiles.save_profile(response.json()["profile"], 1)
        semantic = self.proposal(decision="repeated_request", goal="Unnecessary equivalent wording",
                                 explanation="No profile changes needed. Your earlier request already covers this focus.")
        response, parse = self.draft(semantic, profile=generated, instruction="Please tailor my workspace around fertility outcomes and ovarian ageing.")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["profile"], generated)
        self.assertEqual(response.json()["changes"], [])
        self.assertEqual(response.json()["goal"], generated["goal"])
        parse.assert_awaited_once()
        self.assertEqual(profiles.get_profile("rei"), generated)

    def test_drafts_partial_updates_sensitive_requests_and_permissions_do_not_false_match(self):
        response, _ = self.draft(self.proposal())
        self.assertEqual(profile_adaptation.satisfied_requests(self.original, False, False), [])
        partial = copy.deepcopy(self.original)
        partial["goal"] = response.json()["profile"]["goal"]
        partial = profiles.save_profile(partial, 1)
        self.assertEqual(profile_adaptation.satisfied_requests(partial, False, False), [])
        full = profiles.save_profile(response.json()["profile"], 2)
        self.assertEqual(profile_adaptation.satisfied_requests(full, True, False), [])
        self.assertEqual(profile_adaptation.satisfied_requests(full, False, True), [])
        response, parse = self.draft(self.proposal(), profile=full, sensitive=True, consent_ai=True)
        self.assertFalse(response.json().get("cached"))
        parse.assert_awaited_once()
        sent = json.loads(parse.await_args.kwargs["input"][1]["content"].split("\n", 1)[1])
        self.assertEqual(sent["reference_data"]["requests_already_reflected"], [])


if __name__ == "__main__":
    unittest.main()
