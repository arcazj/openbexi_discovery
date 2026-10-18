"""Release 1.1 integration tests: real local storage, no paid requests or private data."""
import base64
import io
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import app
from backend import budget, connections, library, profiles
from backend.discovery_api import ProfileTextDraft
from backend.discovery_store import settings, update_settings


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DISCOVERY_DATA_DIR": self.temp.name, "DISCOVERY_LIBRARY_DIR": "", "OPENAI_API_KEY": ""})
        self.env.start()
        self.client = TestClient(app, client=("127.0.0.1", 50001))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()
        self.temp.cleanup()

    def post(self, path, value):
        result = self.client.post('/api/discovery'+path, json=value)
        self.assertLess(result.status_code, 300, result.text)
        return result.json()

    def note(self, **changes):
        return library.save_activity({"profile_id": "rei", "kind": "note", "title": "A source note", "content": "Review evidence", **changes})

    def test_default_schema_taxonomy_and_manual_profile_lifecycle(self):
        initial = self.client.get('/api/discovery/bootstrap').json()
        self.assertEqual(initial['settings']['active_profile'], 'rei')
        rei = initial['profiles'][0]
        self.assertEqual(rei['learning_level'], 'advanced')
        self.assertEqual(len(rei['tabs']), 6)
        self.assertTrue(all(t in profiles.taxonomy() for t in rei['themes']))
        profile = profiles.template('general')
        profile['name'] = 'Physics learning'
        profile['themes'] = ['02.01']
        created = self.post('/profiles/save', {'profile': profile, 'create': True})
        self.assertNotEqual(created['id'], 'general')
        self.post('/profiles/action', {'id': created['id'], 'revision': 1, 'action': 'activate'})
        self.assertEqual(settings()['active_profile'], created['id'])
        created['ui']['heading'] = 'Connect physical ideas'
        edited = self.post('/profiles/save', {'profile': created, 'base_revision': 1})
        self.assertEqual(edited['revision'], 2)
        stale = self.client.post('/api/discovery/profiles/save', json={'profile': created, 'base_revision': 1})
        self.assertEqual(stale.status_code, 409)
        restored = self.post('/profiles/action', {'id': created['id'], 'revision': 2, 'action': 'undo'})
        self.assertEqual(restored['ui']['heading'], profiles.template('general')['ui']['heading'])
        self.post('/profiles/action', {'id': created['id'], 'revision': 3, 'action': 'delete'})
        self.assertEqual(settings()['active_profile'], 'rei')
        self.assertEqual(self.client.post('/api/discovery/profiles/action', json={'id': 'rei', 'revision': 1, 'action': 'delete'}).status_code, 422)

    def test_profile_rejects_unknown_themes_tools_and_paths(self):
        rei = profiles.get_profile('rei')
        for field, value in [('themes', ['not-a-theme']), ('themes', ['WORLD']), ('tools', ['research_agents']),
                             ('id', '../escape'), ('hidden_source_ids', ['unknown']),
                             ('hidden_source_ids', ['api:../escape']), ('hidden_source_ids', ['pubmed', 'pubmed'])]:
            changed = {**rei, field: value}
            response = self.client.post('/api/discovery/profiles/save', json={'profile': changed, 'base_revision': 1})
            self.assertIn(response.status_code, (409, 422), response.text)
        self.assertEqual(profiles.get_profile('rei')['revision'], 1)

    def test_cosmologie_is_seeded_without_overwriting_profiles_or_recreating_deleted_copy(self):
        initial = self.client.get('/api/discovery/bootstrap').json()
        self.assertEqual([p['id'] for p in initial['profiles']], ['rei', 'cosmologie'])
        cosmologie = profiles.get_profile('cosmologie')
        self.assertEqual(cosmologie['name'], 'Cosmologie')
        self.assertIn('02.03.03', cosmologie['themes'])
        self.assertEqual(cosmologie['sources'], [])
        self.assertIn('cosmic microwave', cosmologie['ui']['search_placeholder'])
        updated = profiles.save_profile({**cosmologie, 'goal': 'My personal cosmology goal'}, 1)
        rei = profiles.get_profile('rei')
        profiles.ensure_default()
        self.assertEqual(profiles.get_profile('cosmologie'), updated)
        self.assertEqual(profiles.get_profile('rei'), rei)
        profiles.profile_action('cosmologie', 'delete', updated['revision'])
        self.assertEqual([p['id'] for p in profiles.list_profiles()], ['rei'])

    def test_profile_names_are_trimmed_and_duplicates_or_blank_names_are_rejected(self):
        draft = profiles.template('general')
        created = self.post('/profiles/save', {'profile': {**draft, 'name': '  My research  '}, 'create': True})
        self.assertEqual(created['name'], 'My research')
        for name, code in [('my RESEARCH', 409), ('   ', 422)]:
            response = self.client.post('/api/discovery/profiles/save', json={'profile': {**draft, 'name': name}, 'create': True})
            self.assertEqual(response.status_code, code)
        restored = profiles.save_profile({**created, 'name': 'Renamed research'}, created['revision'])
        self.assertEqual(restored['id'], created['id'])

    def test_theme_and_source_changes_preserve_history_and_undo_in_place(self):
        original = profiles.get_profile('rei')
        other = profiles.save_profile(profiles.template('general'), create=True)
        note = self.note()
        workspace = {'workspace': {'questions': [{'id': 'q1', 'title': 'Keep this research'}]},
                     'prefs': {'sources': ['pubmed', 'gwas']}, 'query': 'ovarian aging'}
        self.post('/workspace', {'profile_id': 'rei', 'revision': 0, 'data': workspace})
        changed = self.post('/profiles/save', {'profile': {**original, 'themes': ['02.01'],
                            'hidden_source_ids': ['gwas', 'api:fixture', 'sqlite:fixture']}, 'base_revision': 1})
        self.assertEqual(changed['id'], 'rei')
        self.assertEqual(changed['revision'], 2)
        self.assertEqual(profiles.get_profile('rei')['themes'], ['02.01'])
        self.assertEqual(profiles.get_profile(other['id']), other)
        self.assertEqual(profiles.workspace('rei')['data'], workspace)
        self.assertEqual(library.get_activity(note['id'])['profile_snapshot']['themes'], original['themes'])
        self.assertEqual(self.client.post('/api/discovery/profiles/action', json={
            'id': 'rei', 'revision': 1, 'action': 'undo'}).status_code, 409)
        restored = self.post('/profiles/action', {'id': 'rei', 'revision': 2, 'action': 'undo'})
        self.assertEqual(restored['themes'], original['themes'])
        self.assertEqual(restored['hidden_source_ids'], [])
        empty = self.post('/profiles/save', {'profile': {**restored, 'themes': [], 'hidden_source_ids': ['pubmed']},
                                           'base_revision': restored['revision']})
        self.assertEqual(empty['themes'], [])
        reset = self.post('/profiles/action', {'id': 'rei', 'revision': empty['revision'], 'action': 'reset'})
        self.assertEqual(reset['themes'], original['themes'])
        self.assertEqual(reset['hidden_source_ids'], [])
        self.assertEqual(profiles.workspace('rei')['data'], workspace)
        self.assertEqual(library.get_activity(note['id']), note)

    def test_workspace_revision_and_profile_reset_preserve_research(self):
        data = {'workspace': {'questions': [{'id': 'q1', 'title': 'Keep me'}], 'constraints': {'mentor': 'Available'}}}
        self.post('/workspace', {'profile_id':'rei', 'revision':0, 'data':data})
        self.assertEqual(self.client.post('/api/discovery/workspace', json={'profile_id':'rei','revision':0,'data':{}}).status_code,409)
        self.post('/profiles/action', {'id':'rei','revision':1,'action':'reset'})
        self.assertEqual(profiles.workspace('rei')['data'],data)

    def test_zip_roundtrip_direct_read_duplicate_import_and_sensitive_exclusions(self):
        first = self.note(filename='notes.md', file_base64=base64.b64encode(b'# Source note').decode())
        sensitive = self.note(title='Sensitive', sensitive=True, consent_local=True)
        exported = library.export_zip()
        opened = library.open_zip(exported)
        self.assertIn(first['id'], [x['id'] for x in opened['activities']])
        self.assertIn(sensitive['id'], opened['manifest']['excluded_sensitive'])
        self.assertEqual(library.import_zip(opened['id'])['skipped'],1)
        # A different installation imports histories without activating or overwriting profiles.
        with tempfile.TemporaryDirectory() as other, patch.dict(os.environ, {'DISCOVERY_DATA_DIR':other}):
            second = library.open_zip(exported)
            result = library.import_zip(second['id'])
            self.assertEqual(len(result['imported']),3)
            self.assertEqual(library.artifact_file(first['id']).read_bytes(),b'# Source note')
            self.assertEqual(settings()['active_profile'],'rei')
            self.assertEqual(library.get_activity(first['id'])['profile_snapshot']['revision'],1)
            restored = library.restore_profile(next(x['id'] for x in second['activities'] if x['kind'] == 'workspace'))
            self.assertNotEqual(restored['id'], 'rei')
            self.assertEqual(restored['learning_level'], 'advanced')

    def test_archive_rejects_traversal_duplicates_corruption_and_arbitrary_code(self):
        for name in ['../escape', '/absolute', 'C:/escape', 'profiles/x/activities/y/code.py']:
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w') as z:
                z.writestr(name,'bad')
                z.writestr('manifest.json','{"schema_version":"1.1","files":{}}')
            with self.assertRaises(HTTPException):
                library.validate_zip(output.getvalue())
        self.note()
        content=library.export_zip()
        with zipfile.ZipFile(io.BytesIO(content)) as src:
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w') as dest:
                for name in src.namelist():
                    dest.writestr(name,src.read(name) if name=='manifest.json' else b'corrupted')
        with self.assertRaises(HTTPException):
            library.validate_zip(output.getvalue())

    def test_sensitive_storage_requires_separate_permission_and_redacts_secrets(self):
        with self.assertRaises(HTTPException):
            self.note(sensitive=True)
        note=self.note(content='sk-fixture-secret-never-real',payload={'api_key':'private-value'})
        serialized=json.dumps(note)
        self.assertNotIn('sk-fixture-secret',serialized)
        self.assertNotIn('private-value',serialized)

    def test_quiz_local_grading_and_ai_provenance_survive_revision(self):
        quiz=library.save_activity({'profile_id':'rei','kind':'quiz','title':'Fixture quiz','payload':{'title':'Quiz','questions':[{'question':'Pick A','choices':['A','B'],'answer':0,'explanation':'A is the fixture answer.'}]},'provenance':{'origin':'ai','model':'fixture-model','generated_at':'2026-10-09'}})
        attempt=library.submit_quiz(quiz['id'],[0])
        self.assertEqual(attempt['payload']['score'],1)
        revision=library.save_activity({'profile_id':'rei','kind':'quiz','title':'Edited','payload':quiz['payload'],'parent_id':quiz['id']})
        self.assertEqual(revision['provenance']['origin'],'ai_edited')
        self.assertEqual(revision['provenance']['model'],'fixture-model')

    def quiz(self, profile_id='rei'):
        return library.save_activity({'profile_id':profile_id, 'kind':'quiz', 'title':'Eight evidence questions',
            'payload':{'title':'Eight evidence questions', 'questions':[
                {'question':f'Question {i + 1}', 'choices':['A','B','C','D'], 'answer':i % 4,
                 'explanation':f'Explanation {i + 1}'} for i in range(8)]},
            'provenance':{'origin':'ai', 'model':'gpt-6-astra', 'generated_at':'2026-10-11'}})

    def test_quiz_requires_every_answer_and_scores_exactly_once_per_question(self):
        quiz = self.quiz()
        correct = [i % 4 for i in range(8)]
        for answers in [[], correct[:7], correct + [0], [-1] + correct[1:], [4] + correct[1:],
                        [None] + correct[1:], [True] + correct[1:], ['0'] + correct[1:]]:
            with self.subTest(answers=answers):
                response = self.client.post('/api/discovery/quiz/attempt', json={'activity_id':quiz['id'], 'answers':answers})
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(library.quiz_history('rei'), [])
        attempt = self.post('/quiz/attempt', {'activity_id':quiz['id'], 'answers':[1] + correct[1:]})
        self.assertEqual((attempt['payload']['score'], attempt['payload']['total']), (7, 8))
        self.assertEqual(attempt['payload']['questions'], quiz['payload']['questions'])
        self.assertEqual(attempt['payload']['quiz_provenance'], quiz['provenance'])
        self.assertEqual(attempt['payload']['quiz_level'], 'advanced')
        self.assertEqual(len(self.client.get('/api/discovery/quiz/history?profile_id=rei').json()['attempts']), 1)

    def test_quiz_history_is_durable_and_deletion_stays_in_selected_profile(self):
        other = profiles.save_profile(profiles.template('general'), create=True)
        first_quiz, other_quiz = self.quiz(), self.quiz(other['id'])
        first = library.submit_quiz(first_quiz['id'], [0] * 8)
        second = library.submit_quiz(first_quiz['id'], [i % 4 for i in range(8)])
        other_attempt = library.submit_quiz(other_quiz['id'], [0] * 8)
        note = self.note()
        mismatch = self.client.post('/api/discovery/quiz/attempt', json={
            'activity_id':first_quiz['id'], 'profile_id':other['id'], 'answers':[0] * 8})
        self.assertEqual(mismatch.status_code, 422)
        mismatch_delete = self.client.post('/api/discovery/quiz/history/delete', json={
            'profile_id':'rei', 'attempt_id':other_attempt['id']})
        self.assertEqual(mismatch_delete.status_code, 404)
        self.assertEqual(self.post('/quiz/history/delete', {'profile_id':'rei', 'attempt_id':first['id']}), {'deleted':1})
        self.assertEqual([x['id'] for x in library.quiz_history('rei')], [second['id']])
        self.assertEqual(library.get_activity(first_quiz['id'])['kind'], 'quiz')
        library.delete_activity(first_quiz['id'])
        # A fresh client reads the saved review even after the original quiz is deleted.
        with TestClient(app, client=('127.0.0.1', 50002)) as reopened:
            review = reopened.get('/api/discovery/library/' + second['id']).json()
            self.assertEqual(len(review['payload']['questions']), 8)
            self.assertEqual(review['payload']['score'], 8)
            self.assertEqual(len(reopened.get('/api/discovery/quiz/history?profile_id=rei').json()['attempts']), 1)
        self.assertEqual(self.post('/quiz/history/delete', {'profile_id':'rei'}), {'deleted':1})
        self.assertEqual(library.quiz_history('rei'), [])
        self.assertEqual(library.get_activity(note['id'])['kind'], 'note')
        self.assertEqual(library.get_activity(other_quiz['id'])['kind'], 'quiz')
        self.assertEqual([x['id'] for x in library.quiz_history(other['id'])], [other_attempt['id']])

    def test_generated_quiz_has_eight_questions_and_uses_saved_learning_level(self):
        draft = library.GeneratedQuiz.model_validate(self.quiz()['payload'])
        response = SimpleNamespace(output_parsed=draft, usage={'input_tokens':100, 'output_tokens':200})
        client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=response)))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        for level in ['beginner', 'expert']:
            with self.subTest(level=level):
                profile = profiles.template('general')
                profile['learning_level'] = level
                profile['goal'] = 'Learn to evaluate scientific evidence.'
                profile['name'] = 'Quiz '+level
                profile = profiles.save_profile(profile, create=True)
                with patch.dict(os.environ, {'OPENAI_API_KEY':'sk-test-fixture', 'OPENAI_MODEL':'gpt-6-astra', 'OPENAI_REASONING_EFFORT':'xhigh'}), patch('backend.ai.AsyncOpenAI', return_value=context):
                    result = self.post('/ai/draft', {'task':'create_quiz', 'profile':profile, 'instruction':'Start a quiz.'})
                arguments = client.responses.parse.await_args.kwargs
                self.assertIs(arguments['text_format'], library.GeneratedQuiz)
                self.assertEqual(arguments['reasoning'], {'effort':'xhigh'})
                self.assertIn('exactly 8', arguments['input'][0]['content'])
                reference = json.loads(arguments['input'][1]['content'].split('\n', 1)[1])
                self.assertEqual(reference['profile']['learning_level'], level)
                self.assertEqual(reference['profile']['goal'], profile['goal'])
                self.assertEqual(len(result['questions']), 8)
                self.assertEqual(result['provenance']['model'], 'gpt-6-astra')
                self.assertEqual(profiles.get_profile(profile['id']), profile)
        self.assertEqual(budget.status()['total_tokens'], 600)

    def test_generated_quiz_rejects_wrong_length_and_invalid_choices(self):
        original = self.quiz()['payload']
        for questions in [original['questions'][:7], original['questions'] + original['questions'][:1],
                          [{**q, 'choices':['A','B','C','a']} for q in original['questions']],
                          [{**q, 'choices':['A','B','C',' ']} for q in original['questions']]]:
            with self.subTest(questions=questions):
                # Revalidation also protects callers if a provider/parser returns malformed output.
                response = SimpleNamespace(output_parsed=library.Quiz.model_validate({**original, 'questions':questions}),
                                           usage={'input_tokens':10, 'output_tokens':10})
                client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=response)))
                context = MagicMock()
                context.__aenter__ = AsyncMock(return_value=client)
                context.__aexit__ = AsyncMock(return_value=False)
                with patch.dict(os.environ, {'OPENAI_API_KEY':'sk-test-fixture'}), patch('backend.ai.AsyncOpenAI', return_value=context):
                    result = self.client.post('/api/discovery/ai/draft', json={
                        'task':'create_quiz', 'profile':profiles.get_profile('rei'), 'instruction':'Start a quiz.'})
                self.assertEqual(result.status_code, 502, result.text)
        self.assertEqual(library.list_activities(kind='attempt'), [])

    def test_sqlite_read_only_filtered_bounded_and_explicit_snapshot(self):
        path=Path(self.temp.name)/'research.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE research (participant TEXT, gene TEXT, outcome REAL)')
            db.executemany('INSERT INTO research VALUES(?,?,?)',[('P01','BRCA1',1.0),('P02','BRCA2',2.0)])
        db.close()
        connection=connections.connect('Synthetic REI',str(path),sensitive=True)
        self.assertNotIn('path',connection)
        result=connections.query(connection['id'],'research',['gene','outcome'],{'gene':'BRCA1'})
        self.assertEqual(result['rows'],[{'gene':'BRCA1','outcome':1.0}])
        self.assertEqual(connections.query(connection['id'],'research',['gene'],{'gene':"' OR 1=1 --"})['rows'],[])
        with self.assertRaises(HTTPException):
            connections.query(connection['id'],'research;DROP TABLE research',['gene'])
        with self.assertRaises(HTTPException):
            connections.snapshot('rei',connection['id'],'research',['gene'],{},0,False)
        saved=connections.snapshot('rei',connection['id'],'research',['gene'],{},0,True)
        self.assertTrue(saved['sensitive'])
        self.assertEqual(library.dataset_rows(saved['id'])['total'],2)
        connections.disconnect(connection['id'])
        self.assertEqual(library.dataset_rows(saved['id'])['total'],2)

    def test_budget_concurrency_reconciliation_restart_and_unknown_price(self):
        budget.configure({'token_limit':20000,'cost_limit':None,'period':'monthly'})
        def reserve():
            try:return budget.reserve('rei','gpt-6.1-sol',[],1000)
            except HTTPException:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:reserve(),range(2)))
        accepted=[x for x in results if x]
        self.assertEqual(len(accepted),1)
        budget.finish(accepted[0],{'input_tokens':100,'output_tokens':30,'input_tokens_details':{'cached_tokens':20}})
        budget.finish(accepted[0],{'input_tokens':100,'output_tokens':30})
        self.assertEqual(budget.status()['total_tokens'],130)
        budget.configure({'token_limit':130,'cost_limit':None,'period':'monthly'})
        self.assertTrue(budget.status()['blocked'])
        budget.configure({'token_limit':None,'cost_limit':1,'period':'monthly'})
        with self.assertRaises(HTTPException):budget.reserve('other-profile','unknown-model',[],100)
        budget.configure({'token_limit':0,'cost_limit':None,'period':'monthly'})
        with patch('backend.ai.AsyncOpenAI') as constructor:
            self.assertEqual(self.client.get('/api/ai/check').status_code,423)
            constructor.assert_not_called()

    def test_local_mode_blocks_network_but_preserves_library_and_profiles(self):
        self.note()
        self.post('/settings',{'local_only':True})
        with patch('backend.app.app.state.sources.search',new=AsyncMock()) as fetch:
            self.assertEqual(self.client.post('/api/search',json={'query':'test'}).status_code,423)
            fetch.assert_not_awaited()
        self.assertEqual(self.client.get('/api/ai/check').status_code,423)
        self.assertEqual(self.client.get('/api/discovery/bootstrap').status_code,200)
        self.assertEqual(len(self.client.get('/api/discovery/library').json()['activities']),1)

    def test_documents_assets_and_loopback_write_boundary(self):
        self.assertEqual(self.client.get('/assets/discovery.js').status_code,200)
        for name in ['/.discovery/settings.json','/user_profiles/rei.json','/discovery_library/manifest.json']:
            self.assertEqual(self.client.get(name).status_code,404)
        with TestClient(app,client=('203.0.113.2',50001)) as remote:
            self.assertEqual(remote.post('/api/discovery/settings',json={'local_only':True}).status_code,403)

    def test_ai_profile_draft_is_reviewable_metered_and_does_not_save(self):
        original = profiles.get_profile('rei')
        wording = dict(original['ui'], heading='Reviewed research workspace')
        response = SimpleNamespace(output_parsed=ProfileTextDraft(theme_title=original['theme_title'], ui=wording, explanation='Changed one heading.'),
            usage={'input_tokens':100, 'output_tokens':20})
        client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=response)))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch.dict(os.environ, {'OPENAI_API_KEY':'sk-test-fixture', 'OPENAI_REASONING_EFFORT':'low'}), patch('backend.ai.AsyncOpenAI', return_value=context):
            result = self.post('/ai/draft', {'task':'update_profile', 'profile':original, 'instruction':'Update the heading.'})
        self.assertEqual(result['changes'], {'heading':'Reviewed research workspace'})
        self.assertEqual(profiles.get_profile('rei'), original)
        self.assertEqual(result['profile']['provenance']['heading']['origin'], 'ai')
        self.assertEqual(budget.status()['total_tokens'], 120)
        self.assertEqual(library.get_activity(result['activity_id'])['request'], 'Update the heading.')
        arguments = client.responses.parse.await_args.kwargs
        self.assertFalse(arguments['store'])
        self.assertEqual(arguments['reasoning'], {'effort':'low'})
        self.assertEqual(result['reasoning_effort'], 'low')
        self.assertEqual(arguments['input'][-1]['content'], 'Update the heading.')
        profiles.profile_action('rei','reset',1)
        with patch('backend.ai.AsyncOpenAI') as constructor, patch.dict(os.environ, {'OPENAI_API_KEY':'sk-test-fixture'}):
            result = self.client.post('/api/discovery/ai/draft', json={'task':'update_profile','profile':original,'instruction':'Old request'})
        self.assertEqual(result.status_code,409)
        constructor.assert_not_called()

    def test_single_activity_export_excludes_workspace_and_sensitive_backup_is_opt_in(self):
        note = self.note()
        profiles.save_workspace('rei', {'workspace':{'questions':[], 'constraints':{}}, 'sensitive':True}, 0)
        single = library.open_zip(library.export_zip(activity=note['id']))
        self.assertEqual([a['id'] for a in single['activities']], [note['id']])
        normal = library.open_zip(library.export_zip(profile='rei'))
        self.assertFalse(any(a['kind']=='workspace' for a in normal['activities']))
        authorized = library.open_zip(library.export_zip(profile='rei',include_sensitive=True))
        self.assertTrue(any(a['kind']=='workspace' for a in authorized['activities']))


if __name__=='__main__':
    unittest.main()
