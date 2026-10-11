"""AI must use supplied citations, keep credentials server-side, and avoid fallback."""

import json
import os
import unittest
import tempfile
import httpx
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from openai import RateLimitError
from pydantic import ValidationError

from backend import ai


def evidence():
    return ai.EvidenceRecord(
        id="pubmed:123456", source="pubmed", type="publication",
        title="Fixture publication", summary="Evidence supplied to the model.",
        url="https://pubmed.ncbi.nlm.nih.gov/123456/",
        metadata={"evidence_scope": "Abstract and bibliographic metadata"},
    )


def request():
    return ai.AIRequest(action="explain", query="ovarian aging", records=[evidence()])


def guidance():
    return ai.GuidanceResult(
        next_step="Review the population in the supplied abstract [pubmed:123456].",
        tip="Confirm available outcome data before choosing a design.",
        refined_query="ovarian aging reproductive outcomes",
        explanation="The supplied evidence is abstract-level [pubmed:123456]. Feasibility is unknown.",
        citation_ids=["pubmed:123456"],
        candidate_question=ai.CandidateQuestion(
            title="Ovarian aging and reproductive outcomes", question="Is ovarian reserve associated with reproductive outcomes?",
            population="Unknown", exposure="Ovarian reserve", outcome="Reproductive outcomes",
            design="Unknown", required_data="Unknown", feasibility="Unknown", uncertainties="Verify with mentor",
            rationale="Provisional question from the supplied evidence.", citations=["pubmed:123456"]),
    )


class GuidanceValidationTests(unittest.TestCase):
    def test_guidance_reconstructs_citations_and_preserves_actionable_question(self):
        result = ai.validate_guidance_result(guidance(), [evidence()])
        self.assertEqual(result["refined_query"], "ovarian aging reproductive outcomes")
        self.assertEqual(result["candidate_question"]["citations"], ["pubmed:123456"])
        self.assertEqual(result["citations"][0]["url"], evidence().url)

    def test_each_guidance_field_rejects_invented_links_and_citations(self):
        for field in ("next_step", "tip", "refined_query", "explanation"):
            for content in ("Claim [pubmed:999999].", "Open https://invented.example."):
                with self.subTest(field=field, content=content):
                    data = guidance().model_dump()
                    data[field] = content
                    with self.assertRaises(ValueError):
                        ai.validate_guidance_result(ai.GuidanceResult(**data), [evidence()])

    def test_uncited_proposed_question_and_oversized_brief_fields_are_rejected(self):
        for change in ({"citations": []}, {"title": "x" * 241}, {"feasibility": ""}):
            with self.subTest(change=change):
                data = guidance().model_dump()
                data["candidate_question"].update(change)
                with self.assertRaises(ValueError):
                    ai.validate_guidance_result(ai.GuidanceResult(**data), [evidence()])

    def test_display_text_and_search_query_are_bounded(self):
        for field, content in (("next_step", "x" * 481), ("tip", "x" * 481), ("refined_query", "x" * 251)):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    ai.GuidanceResult(**dict(guidance().model_dump(), **{field: content}))
        data = guidance().model_dump()
        data["refined_query"] = "ovarian\naging"
        with self.assertRaises(ValueError):
            ai.validate_guidance_result(ai.GuidanceResult(**data), [evidence()])


class CitationValidationTests(unittest.TestCase):
    def test_supported_citations_use_source_urls_instead_of_generated_links(self):
        result = ai.AIResult(text="Limited evidence [pubmed:123456].", citation_ids=["pubmed:123456"], candidate_questions=[])
        verified = ai.validate_ai_result(result, [evidence()])
        self.assertEqual(verified["citations"], [{"id": "pubmed:123456", "title": "Fixture publication", "url": "https://pubmed.ncbi.nlm.nih.gov/123456/"}])

    def test_invented_citation_in_prose_is_rejected_even_with_a_valid_citation_list(self):
        result = ai.AIResult(text="Claim [pubmed:999999].", citation_ids=["pubmed:123456"], candidate_questions=[])
        with self.assertRaises(ValueError):
            ai.validate_ai_result(result, [evidence()])

    def test_uncited_output_and_model_generated_urls_are_rejected(self):
        for text, ids in (("Unsupported claim", []), ("See https://invented.example/paper", ["pubmed:123456"])):
            with self.subTest(text=text):
                result = ai.AIResult(text=text, citation_ids=ids, candidate_questions=[])
                with self.assertRaises(ValueError):
                    ai.validate_ai_result(result, [evidence()])

    def test_a_candidate_question_requires_its_own_supporting_citation(self):
        question = ai.CandidateQuestion(
            title="Candidate", question="Is exposure associated with outcome?", population="Unknown",
            exposure="Unknown", outcome="Unknown", design="Cohort", required_data="Unknown",
            feasibility="Unknown", uncertainties="Unknown", rationale="Provisional", citations=[],
        )
        result = ai.AIResult(text="Evidence [pubmed:123456].", citation_ids=["pubmed:123456"], candidate_questions=[question])
        with self.assertRaises(ValueError):
            ai.validate_ai_result(result, [evidence()])

    def test_invented_citation_in_candidate_rationale_is_rejected(self):
        question = ai.CandidateQuestion(
            title="Candidate", question="Is exposure associated with outcome?", population="Unknown",
            exposure="Unknown", outcome="Unknown", design="Cohort", required_data="Unknown",
            feasibility="Unknown", uncertainties="Unknown", rationale="Claim [pubmed:999999].",
            citations=["pubmed:123456"],
        )
        result = ai.AIResult(text="Evidence [pubmed:123456].", citation_ids=["pubmed:123456"], candidate_questions=[question])
        with self.assertRaises(ValueError):
            ai.validate_ai_result(result, [evidence()])

    def test_mismatched_record_id_and_url_are_rejected(self):
        data = evidence().model_dump()
        for url in ("https://pubmed.ncbi.nlm.nih.gov/999999/", "https://pubmed.ncbi.nlm.nih.gov.attacker.example/123456/"):
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    ai.EvidenceRecord(**dict(data, url=url))

    def test_duplicate_records_and_unbounded_metadata_are_rejected(self):
        with self.assertRaises(ValidationError):
            ai.AIRequest(action="explain", query="topic", records=[evidence(), evidence()])
        with self.assertRaises(ValidationError):
            ai.EvidenceRecord(**dict(evidence().model_dump(), metadata={"content": "a" * 12001}))


class ResponsesContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="discovery-ai-test-")
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"DISCOVERY_DATA_DIR": directory.name, "DISCOVERY_LIBRARY_DIR": ""})
        environment.start()
        self.addCleanup(environment.stop)

    async def test_guidance_uses_its_structured_schema_and_exact_model_without_storage(self):
        parsed = guidance()
        client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=SimpleNamespace(output_parsed=parsed))))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        payload = ai.AIRequest(action="guidance", query="ovarian aging", records=[evidence()],
                               constraints=ai.ResearchConstraints(data="Clinic registry"),
                               questions=[{"question": "Saved fellowship question"}])
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fixture", "OPENAI_MODEL": "gpt-6.1-sol", "OPENAI_REASONING_EFFORT": "high"}), patch.object(ai, "AsyncOpenAI", return_value=context):
            result = await ai.generate(payload)
        arguments = client.responses.parse.await_args.kwargs
        self.assertEqual(arguments["model"], "gpt-6.1-sol")
        self.assertEqual(arguments["reasoning"], {"effort": "high"})
        self.assertEqual(result["reasoning_effort"], "high")
        self.assertIs(arguments["text_format"], ai.GuidanceResult)
        self.assertFalse(arguments["store"])
        self.assertEqual(result["evidence_snapshot"]["constraints"]["data"], "Clinic registry")
        self.assertEqual(result["evidence_snapshot"]["questions"], payload.questions)
        self.assertEqual(result["evidence_ids"], [evidence().id])

    async def test_missing_key_fails_before_constructing_openai_client(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}), patch.object(ai, "AsyncOpenAI") as constructor:
            with self.assertRaises(HTTPException) as error:
                await ai.generate(request())
        self.assertEqual(error.exception.status_code, 503)
        constructor.assert_not_called()

    async def test_response_uses_exact_configured_model_and_reproducible_evidence(self):
        parsed = ai.AIResult(text="Limited evidence [pubmed:123456].", citation_ids=["pubmed:123456"], candidate_questions=[])
        client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=SimpleNamespace(output_parsed=parsed))))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        key = "sk-test-server-only"
        with patch.dict(os.environ, {"OPENAI_API_KEY": key, "OPENAI_MODEL": "gpt-6-astra", "OPENAI_REASONING_EFFORT": "xhigh"}), patch.object(ai, "AsyncOpenAI", return_value=context) as constructor:
            result = await ai.generate(request())
        self.assertEqual(constructor.call_args.kwargs["api_key"], key)
        self.assertEqual(constructor.call_args.kwargs["base_url"], "https://api.openai.com/v1")
        arguments = client.responses.parse.await_args.kwargs
        self.assertEqual(arguments["model"], "gpt-6-astra")
        self.assertEqual(arguments["reasoning"], {"effort": "xhigh"})
        self.assertGreaterEqual(arguments["max_output_tokens"], 25000)
        self.assertFalse(arguments["store"])
        self.assertIs(arguments["text_format"], ai.AIResult)
        self.assertEqual(result["model"], "gpt-6-astra")
        self.assertEqual(result["reasoning_effort"], "xhigh")
        self.assertEqual(result["evidence_snapshot"]["records"][0]["id"], "pubmed:123456")
        self.assertIn("prompt_version", result)
        self.assertNotIn(key, json.dumps(result))

    async def test_unverifiable_model_response_is_not_replaced_by_other_model(self):
        client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=SimpleNamespace(output_parsed=None))))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fixture"}), patch.object(ai, "AsyncOpenAI", return_value=context):
            with self.assertRaises(HTTPException) as error:
                await ai.generate(request())
        self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(client.responses.parse.await_count, 1)

    async def test_exhausted_quota_is_distinct_from_a_temporary_rate_limit(self):
        response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        for code in ("insufficient_quota", "billing_hard_limit_reached", "rate_limit_exceeded"):
            with self.subTest(code=code):
                error = ai.ai_error(RateLimitError("private provider details", response=response, body={"code": code}))
                self.assertEqual(error.status_code, 429)
                self.assertNotIn("private provider details", str(error.detail))
                if code == "rate_limit_exceeded":
                    self.assertIsInstance(error.detail, str)
                    self.assertIn("temporary rate limit", error.detail)
                else:
                    self.assertEqual(error.detail["code"], "insufficient_quota")
                    self.assertIn("credits or quota are exhausted", error.detail["message"])


if __name__ == "__main__":
    unittest.main()
