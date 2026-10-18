"""Search coverage, reasoning, provenance and billing without paid requests."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from backend.app import app
from backend import ai, budget, search


def web_response():
    return SimpleNamespace(status="completed", usage={"input_tokens": 1000, "output_tokens": 200}, output=[
        {"type": "web_search_call", "status": "completed", "action": {"type": "search", "queries": ["BRCA1 current research"]}},
        {"type": "message", "content": [{"type": "output_text", "text": "Evidence from the web [source].",
         "annotations": [{"type": "url_citation", "start_index": 22, "end_index": 30,
                          "url": "https://example.org/research", "title": "Research source"}]}]}])


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.environment = patch.dict(os.environ, {"DISCOVERY_DATA_DIR": self.temp.name, "DISCOVERY_LIBRARY_DIR": "",
                                                  "OPENAI_API_KEY": "sk-fixture", "OPENAI_MODEL": "gpt-6.1-sol"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(app, client=("127.0.0.1", 50000))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.client.get('/api/discovery/bootstrap')
        self.provider = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=web_response()), parse=AsyncMock()))
        context = AsyncMock()
        context.__aenter__.return_value = self.provider
        self.provider_patch = patch.object(ai, 'AsyncOpenAI', return_value=context)
        self.provider_patch.start()
        self.addCleanup(self.provider_patch.stop)
        async def retrieve(source, interpretation, limit):
            return {"records": [], "coverage": {"source": source, "status": "ok", "query": interpretation['term'],
                                                "retrieved": 0, "total": 0, "truncated": False}}
        self.source = AsyncMock(side_effect=retrieve)
        self.source_patch = patch.object(app.state.sources, 'search', self.source)
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)

    def post(self, **overrides):
        return self.client.post('/api/search', json={"query": "BRCA1 research", "scope": "overall",
                                                   "sources": ["pubmed"], **overrides})

    def test_overall_ignores_sources_and_uses_astra_with_selected_reasoning(self):
        result = self.post(reasoning_effort='high')
        self.assertEqual(result.status_code, 200, result.text)
        data = result.json()
        self.assertEqual(data['scope'], 'overall')
        self.assertEqual(data['model'], 'gpt-6-astra')
        self.assertEqual(data['reasoning_effort'], 'high')
        arguments = self.provider.responses.create.call_args.kwargs
        self.assertEqual(arguments['reasoning'], {'effort': 'high'})
        self.assertEqual(arguments['model'], 'gpt-6-astra')
        self.assertFalse(arguments['store'])
        self.assertNotIn('filters', arguments['tools'][0])
        self.assertEqual(arguments['max_tool_calls'], 3)
        self.assertNotIn('pubmed', str(arguments['input']).lower())
        self.source.assert_not_called()
        self.assertEqual(data['coverage'][0]['query'], 'BRCA1 current research')
        self.assertEqual(data['web_sources'][0]['url'], 'https://example.org/research')
        self.assertAlmostEqual(budget.status()['estimated_usd'], 0.03)

    def test_no_selection_falls_back_to_overall_and_keeps_reasoning(self):
        response = self.post(scope='specific', sources=[], reasoning_effort='low')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['scope'], 'overall')
        self.assertEqual(self.provider.responses.create.call_args.kwargs['reasoning'], {'effort': 'low'})
        self.provider.responses.parse.assert_not_called()

    def test_upper_reasoning_levels_reach_astra_for_both_search_scopes(self):
        self.provider.responses.parse.return_value = SimpleNamespace(status='completed', output=[],
            usage={'input_tokens': 100, 'output_tokens': 100}, output_parsed=search.QueryPlan(queries=[
                search.SourceQuery(source='pubmed', query='BRCA1 research', mode='topic')]))
        for scope in ('overall', 'specific'):
            for effort in ('xhigh', 'max'):
                with self.subTest(scope=scope, effort=effort):
                    result = self.post(scope=scope, reasoning_effort=effort)
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertEqual(result.json()['reasoning_effort'], effort)
                    method = self.provider.responses.create if scope == 'overall' else self.provider.responses.parse
                    self.assertEqual(method.call_args.kwargs['reasoning'], {'effort': effort})
                    self.assertEqual(method.call_args.kwargs['max_output_tokens'], ai.output_token_limit(effort))

    def test_specific_profile_topics_constrain_web_search(self):
        response = self.post(scope='specific', sources=[], profile_id='cosmologie', topics=['02.03.03.03'])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['scope'], 'specific')
        self.assertEqual(response.json()['topics'], ['02.03.03.03'])
        request = json.loads(self.provider.responses.create.call_args.kwargs['input'][-1]['content'])
        self.assertEqual(request, {'query': 'BRCA1 research', 'selected_topics': ['Dark matter']})
        self.assertTrue(response.json()['answer'])
        self.source.assert_not_called()
        self.provider.responses.parse.assert_not_called()

    def test_topic_selection_is_ignored_by_overall_search(self):
        result = self.post(topics=['02.03.03.03'])
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['topics'], [])
        self.assertEqual(self.provider.responses.create.call_args.kwargs['input'][-1]['content'], 'BRCA1 research')

    def test_invalid_topic_combinations_and_unconfigured_topic_search(self):
        for overrides in ({'topics': ['unknown']}, {'topics': ['02.03.03.03'], 'sources': ['pubmed']},
                          {'topics': ['02.03.03.03', '02.03.03.03']}, {'topics': ['02.01']}):
            result = self.post(scope='specific', profile_id='cosmologie', **({'sources': []} | overrides))
            self.assertEqual(result.status_code, 422, result.text)
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            result = self.post(scope='specific', sources=[], profile_id='cosmologie', topics=['02.03.03.03'])
            self.assertEqual(result.status_code, 503)
        self.provider.responses.create.assert_not_called()
        self.source.assert_not_called()

    def test_specific_queries_only_selected_sources_and_reports_exact_queries(self):
        self.provider.responses.parse.return_value = SimpleNamespace(status='completed', output=[],
            usage={'input_tokens': 100, 'output_tokens': 100}, output_parsed=search.QueryPlan(queries=[
                search.SourceQuery(source='pubmed', query='BRCA1 AND breast cancer', mode='topic'),
                search.SourceQuery(source='ensembl', query='BRCA1', mode='gene')]))
        result = self.post(scope='specific', sources=['pubmed', 'ensembl'], reasoning_effort='low')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([call.args[0] for call in self.source.call_args_list], ['pubmed', 'ensembl'])
        self.assertEqual([item['query'] for item in result.json()['coverage']], ['BRCA1 AND breast cancer', 'BRCA1'])
        self.assertEqual(self.provider.responses.parse.call_args.kwargs['reasoning'], {'effort': 'low'})
        self.provider.responses.create.assert_not_called()

    def test_generated_plan_cannot_expand_coverage(self):
        self.provider.responses.parse.return_value = SimpleNamespace(status='completed', output=[],
            usage={'input_tokens': 100, 'output_tokens': 100}, output_parsed=search.QueryPlan(queries=[
                search.SourceQuery(source='gwas', query='breast cancer', mode='topic')]))
        response = self.post(scope='specific')
        self.assertEqual(response.status_code, 502)
        self.source.assert_not_called()

    def test_unconfigured_specific_remains_direct_and_overall_is_not_misrepresented(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            specific = self.post(scope='specific')
            self.assertEqual(specific.status_code, 200)
            self.assertIn('Direct source search', specific.json()['search_note'])
            self.assertNotIn('reasoning_effort', specific.json())
            self.assertEqual(self.post().status_code, 503)
        self.provider.responses.create.assert_not_called()
        self.provider.responses.parse.assert_not_called()

    def test_sensitive_and_local_only_gates_precede_external_work(self):
        self.assertEqual(self.post(sensitive=True).status_code, 403)
        self.client.post('/api/discovery/settings', json={'local_only': True})
        self.assertEqual(self.post().status_code, 423)
        self.provider.responses.create.assert_not_called()
        self.source.assert_not_called()

    def test_invalid_reasoning_scope_and_duplicate_sources_are_rejected(self):
        for payload in ({'reasoning_effort': 'none'}, {'scope': 'everything'}, {'sources': ['pubmed', 'pubmed']}, {'limit': 51}):
            self.assertEqual(self.post(**payload).status_code, 422)
        self.provider.responses.create.assert_not_called()

    def test_direct_search_can_retrieve_fifty_records(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            response = self.post(scope='specific', limit=50)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.source.call_args.args[2], 50)
        self.provider.responses.create.assert_not_called()
        self.provider.responses.parse.assert_not_called()

    def test_invalid_specific_region_is_rejected_before_provider_work(self):
        response = self.post(scope='specific', mode='region', query='not a region')
        self.assertEqual(response.status_code, 422)
        self.provider.responses.create.assert_not_called()
        self.provider.responses.parse.assert_not_called()
        self.source.assert_not_called()

    def test_failed_or_uncited_web_response_never_looks_like_verified_results(self):
        for change in ('uncited', 'incomplete', 'unsafe_link'):
            response = web_response()
            if change == 'incomplete':
                response.status = 'incomplete'
            elif change == 'unsafe_link':
                response.output[1]['content'][0]['annotations'][0]['url'] = 'javascript:alert(1)'
            else:
                response.output[1]['content'][0]['annotations'] = []
            self.provider.responses.create.return_value = response
            self.assertEqual(self.post().status_code, 502)

    def test_web_allowance_includes_tools_before_request(self):
        with patch.object(budget, 'reserve', side_effect=__import__('fastapi').HTTPException(423, 'Insufficient allowance')) as reserve:
            self.assertEqual(self.post().status_code, 423)
            self.assertEqual(reserve.call_args.kwargs['web_calls'], 3)
            self.provider.responses.create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
