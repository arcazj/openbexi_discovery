"""Complete name-based generation, validation and rejection without paid calls."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from backend.app import app
from backend import ai, budget, profile_creation, profiles


class ProfileCreationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, {'DISCOVERY_DATA_DIR': temporary.name, 'DISCOVERY_LIBRARY_DIR': '',
                                             'OPENAI_API_KEY': 'sk-fixture', 'OPENAI_MODEL': 'gpt-6-astra'})
        environment.start()
        self.addCleanup(environment.stop)
        self.client = TestClient(app, client=('127.0.0.1', 50000))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.client.get('/api/discovery/bootstrap')
        context = AsyncMock()
        self.provider = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock()))
        context.__aenter__.return_value = self.provider
        mock = patch.object(ai, 'AsyncOpenAI', return_value=context)
        mock.start()
        self.addCleanup(mock.stop)
        template = profiles.template('cosmologie')
        self.content = {key: template[key] for key in ('name', 'description', 'goal', 'theme_title', 'themes', 'sources', 'ui')}

        self.content['name'] = '宇宙論研究'
        self.content['ui'].update(heading='Explore the universe', welcome_heading='Start exploring')

    def response(self, content, decision='accepted'):
        self.provider.responses.parse.return_value = SimpleNamespace(
            output_parsed=profile_creation.ProfileCreation(decision=decision, explanation='Choose a clear topic.' if decision=='rejected' else 'A complete astronomy profile.', content=content),
            usage={'input_tokens': 100, 'output_tokens': 100})

    def post(self, name='宇宙論', **overrides):
        draft = profiles.template('general')
        draft['name'] = 'Draft'
        return self.client.post('/api/discovery/ai/draft', json={
            'task': 'generate_profile', 'profile': draft, 'instruction': name, **overrides})

    def test_complete_generated_draft_has_topics_wording_provenance_and_requires_save(self):
        self.response(self.content)
        before = profiles.list_profiles()
        response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['decision'], 'accepted')
        draft = result['profile']
        self.assertEqual(draft['name'], self.content['name'])
        self.assertEqual(draft['themes'], self.content['themes'])
        self.assertEqual(draft['ui'], self.content['ui'])
        self.assertEqual(draft['hidden_source_ids'], ['pubmed', 'ensembl', 'gwas'])
        self.assertEqual(draft['provenance']['themes']['origin'], 'ai')
        self.assertEqual(profiles.list_profiles(), before)
        arguments = self.provider.responses.parse.call_args.kwargs
        self.assertFalse(arguments['store'])
        self.assertEqual(json.loads(arguments['input'][-1]['content'])['area_of_interest'], '宇宙論')
        self.assertIn('topic_catalogue', arguments['input'][1]['content'])
        self.assertGreater(budget.status()['estimated_usd'], 0)
        saved = self.client.post('/api/discovery/profiles/save', json={'profile': draft, 'create': True})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(len(profiles.list_profiles()), 3)

    def test_duplicate_generated_name_is_rejected(self):
        self.response({**self.content, 'name': 'REI'})
        self.assertEqual(self.post().status_code, 409)
        self.assertEqual(len(profiles.list_profiles()), 2)

    def test_selected_reasoning_reaches_provider_and_budget_without_changing_defaults(self):
        self.response(self.content)
        with patch.dict(os.environ, {'OPENAI_REASONING_EFFORT': 'high'}):
            for effort in ('medium', 'high', 'xhigh', 'max'):
                with self.subTest(effort=effort), patch.object(budget, 'reserve', wraps=budget.reserve) as reserve:
                    response = self.post(reasoning_effort=effort)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['reasoning_effort'], effort)
                    arguments = self.provider.responses.parse.call_args.kwargs
                    self.assertEqual(arguments['reasoning'], {'effort': effort})
                    self.assertEqual(arguments['max_output_tokens'], ai.output_token_limit(effort))
                    self.assertEqual(reserve.call_args.args[3], arguments['max_output_tokens'])
                    self.assertEqual(ai.reasoning_effort(), 'high')
            self.assertEqual(self.post().json()['reasoning_effort'], 'medium')

    def test_invalid_creation_reasoning_is_rejected_before_generation(self):
        for effort in ('low', 'ultra', 'unknown'):
            self.assertEqual(self.post(reasoning_effort=effort).status_code, 422)
        self.provider.responses.parse.assert_not_called()

    def test_rejected_name_creates_no_profile(self):
        self.response(None, 'rejected')
        response = self.post('asdf qzxv')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['decision'], 'rejected')
        self.assertNotIn('profile', response.json())
        self.assertEqual(len(profiles.list_profiles()), 2)

    def test_incomplete_or_unknown_topics_are_rejected_without_saving(self):
        for content in ({**self.content, 'themes': ['unknown', 'bad', 'fake']}, None,
                        {**self.content, 'ui': {**self.content['ui'], 'heading': ''}}):
            self.response(content)
            response = self.post()
            self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(len(profiles.list_profiles()), 2)

    def test_sensitive_missing_key_and_local_only_gates(self):
        self.assertEqual(self.post(sensitive=True).status_code, 403)
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            self.assertEqual(self.post().status_code, 503)
        self.client.post('/api/discovery/settings', json={'local_only': True})
        self.assertEqual(self.post().status_code, 423)
        self.provider.responses.parse.assert_not_called()


if __name__ == '__main__':
    unittest.main()
