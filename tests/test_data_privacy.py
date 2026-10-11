"""Real local storage and mocked remote APIs; originals and credentials never enter AI."""
import base64
import io
import json
import os
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from backend import api_connections, datasets, library, private_store, profiles
from backend.app import app
from backend.discovery_api import DatasetAnswer
from backend.discovery_store import update_settings, write_json


class DataPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DISCOVERY_DATA_DIR':self.temp.name, 'DISCOVERY_LIBRARY_DIR':'', 'OPENAI_API_KEY':'', 'OPENAI_MODEL':'gpt-6-astra', 'OPENAI_REASONING_EFFORT':'xhigh'})
        self.env.start()
        self.client = TestClient(app, client=('127.0.0.1', 51000))
        self.client.__enter__()
        self.rows = [{'patient_name':'Alice Example','age':34,'outcome':2,'notes':'Alice Example contact alice@example.org','password':'fictional-password'},
                     {'patient_name':'Bob Example','age':46,'outcome':4,'notes':'Bob Example','password':'fictional-password'},
                     {'patient_name':'Alice Example','age':34,'outcome':6,'notes':'Alice Example follow-up','password':'fictional-password'}]

    def tearDown(self):
        self.client.__exit__(None,None,None)
        datasets.STAGES.clear()
        self.env.stop()
        self.temp.cleanup()

    def post(self, path, value=None, expected=200):
        response = self.client.post('/api/discovery'+path, json=value or {})
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def import_rows(self, rows=None):
        return self.post('/datasets/import', {'profile_id':'rei','filename':'patient-Alice-SECRET.json',
            'file_base64':base64.b64encode(json.dumps(rows or self.rows).encode()).decode()})

    def working_copy(self, retain=False):
        stage = self.import_rows()
        preview = self.post('/dataset-reviews/'+stage['stage_id']+'/preview', {'rules':stage['rules']})
        return self.post('/dataset-reviews/'+stage['stage_id']+'/save', {'preview_id':preview['preview_id'],'reviewed':True,'retain_original':retain})

    def ai_client(self, output):
        client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=SimpleNamespace(output_parsed=output, usage={'input_tokens':50,'output_tokens':20}))))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        return client, context

    def test_local_review_consistent_labels_free_text_and_forced_credential_removal(self):
        with patch('backend.ai.AsyncOpenAI') as constructor:
            stage = self.import_rows()
            rules = stage['rules']
            for rule in rules:
                if rule['field'] in ('notes','password'):
                    rule['action'] = 'keep'
            preview = self.post('/dataset-reviews/'+stage['stage_id']+'/preview', {'rules':rules})
            constructor.assert_not_called()
        rows = preview['rows']
        self.assertEqual([row['patient_name'] for row in rows], ['Patient 1','Patient 2','Patient 1'])
        serialized = json.dumps(rows)
        for secret in ['Alice Example','Bob Example','alice@example.org','fictional-password','password']:
            self.assertNotIn(secret, serialized)
        self.assertIn('Patient 1 contact', rows[0]['notes'])
        self.assertEqual(self.rows[0]['patient_name'], 'Alice Example')
        self.assertEqual(datasets.get_stage(stage['stage_id'])['rows'][0]['patient_name'], 'Alice Example')

    def test_confirmation_current_preview_and_complete_rules_are_required(self):
        stage = self.import_rows()
        prefix = '/dataset-reviews/'+stage['stage_id']
        self.post(prefix+'/save', {'preview_id':'none','reviewed':True}, 409)
        self.post(prefix+'/preview', {'rules':stage['rules'][:-1]}, 422)
        first = self.post(prefix+'/preview', {'rules':stage['rules']})
        self.post(prefix+'/save', {'preview_id':first['preview_id']}, 403)
        second = self.post(prefix+'/preview', {'rules':stage['rules'],'terms':['Example']})
        self.post(prefix+'/save', {'preview_id':first['preview_id'],'reviewed':True}, 409)
        self.post(prefix+'/save', {'preview_id':second['preview_id'],'reviewed':True})
        self.post(prefix+'/preview', {'rules':stage['rules']}, 410)

    def test_mask_generalize_nested_fields_and_additional_terms(self):
        stage = self.import_rows([{'patient':{'name':'Alice Example'}, 'birthDate':'1980-03-12', 'age':46,
            'tag':'Project Secret', 'apiKey':'fictional-api-value','misc':'alice@example.org'}])
        for rule in stage['rules']:
            if rule['field']=='age':rule['action']='band'
        value = self.post('/dataset-reviews/'+stage['stage_id']+'/preview', {'rules':stage['rules'],'terms':['Project Secret']})['rows'][0]
        self.assertEqual(value['patient.name'], 'Patient 1')
        self.assertEqual(value['birthDate'], '1980')
        self.assertEqual(value['age'], '40–49')
        self.assertEqual(value['tag'], 'Sensitive 1')
        self.assertNotIn('apiKey', value)
        self.assertNotIn('alice@example.org', str(value))

    def test_numeric_identifiers_do_not_change_unrelated_measurements_or_statistics(self):
        stage=self.import_rows([{'patient_id':1,'outcome':1},{'patient_id':2,'outcome':2}])
        value=self.post('/dataset-reviews/'+stage['stage_id']+'/preview',{'rules':stage['rules']})
        self.assertEqual([row['patient_id'] for row in value['rows']],['Patient 1','Patient 2'])
        self.assertEqual([row['outcome'] for row in value['rows']],[1,2])
        self.assertEqual(datasets.scrub('Patient 1 has an outcome of 1.',{'1':'Patient 1','2':'Patient 2'}),'Patient 1 has an outcome of 1.')

    def test_encrypted_original_and_mapping_never_enter_export_or_ai(self):
        item = self.working_copy(True)
        private = private_store.read('dataset', item['id'])
        self.assertEqual(private['original'], self.rows)
        self.assertNotIn(b'Alice Example', private_store.path_for('dataset', item['id']).read_bytes())
        archive = library.export_zip(activity=item['id'], include_sensitive=True)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            exported = b''.join(z.read(name) for name in z.namelist()).decode()
        for secret in ['Alice Example','fictional-password','patient-Alice-SECRET','mapping','original_preview']:
            self.assertNotIn(secret, exported)
        client, context = self.ai_client(DatasetAnswer(answer='Mean outcome is 4 for these 3 saved rows.', limitations=['This is a small working copy.']))
        with patch.dict(os.environ, {'OPENAI_API_KEY':'sk-test-fixture'}), patch('backend.ai.AsyncOpenAI',return_value=context):
            result = self.post('/datasets/'+item['id']+'/ask', {'question':'Compare Alice Example with Bob Example','consent_ai':True})
        arguments = client.responses.parse.await_args.kwargs
        sent = json.dumps(arguments['input'])
        for secret in ['Alice Example','Bob Example','fictional-password','alice@example.org','patient-Alice-SECRET']:
            self.assertNotIn(secret, sent)
        self.assertEqual(result['question'], 'Compare Patient 1 with Patient 2')
        self.assertFalse(arguments['store'])
        self.assertEqual(arguments['reasoning'], {'effort':'xhigh'})
        self.assertIn('statistics', sent)

    def test_raw_forged_imported_or_modified_copy_cannot_reach_ai(self):
        raw = library.save_activity({'profile_id':'rei','kind':'dataset','title':'Legacy','payload':{'rows':self.rows, 'privacy':{'status':'pseudonymized'}}})
        reviewed = self.working_copy()
        path = library.find_path(reviewed['id'])
        reviewed['payload']['rows'][0]['patient_name'] = 'Tampered identity'
        write_json(path,reviewed)
        with patch('backend.ai.AsyncOpenAI') as constructor, patch.dict(os.environ, {'OPENAI_API_KEY':'sk-test-fixture'}):
            for aid in [raw['id'],reviewed['id']]:
                self.post('/datasets/'+aid+'/ask', {'question':'Summarize','consent_ai':True},403)
            constructor.assert_not_called()
        clean = self.working_copy()
        private_store.delete('dataset', clean['id'])  # Same boundary as a portable imported copy.
        self.post('/datasets/'+clean['id']+'/ask', {'question':'Summarize','consent_ai':True},403)

    def test_statistics_original_preservation_revision_and_delete_private_data(self):
        item = self.working_copy(True)
        value = self.client.get('/api/discovery/datasets/'+item['id']+'/statistics').json()
        outcome = next(c for c in value['columns'] if c['field']=='outcome')
        self.assertEqual((outcome['mean'], outcome['median'], outcome['minimum'], outcome['maximum']), (4,4,2,6))
        review = self.post('/datasets/'+item['id']+'/review')
        self.assertTrue(review['original_available'])
        self.assertEqual(review['original_preview'],self.rows)
        self.post('/datasets/'+item['id']+'/ask', {'question':'Summarize'},403)
        library.delete_activity(item['id'])
        self.assertIsNone(private_store.read('dataset',item['id']))

    def test_invalid_and_oversized_data_are_rejected_without_ai(self):
        for rows in [[], [{'x':float('nan')}], [{'x':i} for i in range(5001)], [{'a.b':1,'a':{'b':2}}]]:
            result = self.client.post('/api/discovery/datasets/import',json={'profile_id':'rei','filename':'x.json',
                'file_base64':base64.b64encode(json.dumps(rows).encode()).decode()})
            self.assertIn(result.status_code,(413,422))
        self.post('/datasets/import',{'profile_id':'rei','filename':'x.csv','file_base64':base64.b64encode(b'name,name\na,b').decode()},422)

    def connection(self, **changes):
        return {'profile_id':'rei','name':'Synthetic API','url':'https://research.example/data','query_parameter':'q','rows_path':'rows', **changes}

    def transport(self, handler):
        return patch('backend.api_connections.HTTP_CLIENT', side_effect=lambda **kwargs:httpx.AsyncClient(transport=httpx.MockTransport(handler),**kwargs))

    def test_api_authentication_modes_scope_edit_and_credential_erasure(self):
        requests=[]
        def handler(request):
            requests.append(request)
            return httpx.Response(200,json={'rows':[{'value':1}]})
        with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(handler):
            for kind in ['none','bearer','api_key_header','api_key_query','basic']:
                item=self.post('/api-connections',self.connection(auth_type=kind,username='fixture-user',credential='fixture-secret'))
                output=json.dumps(item)
                self.assertNotIn('fixture-secret',output)
                self.assertNotIn('fixture-user',output)
                request=requests[-1]
                if kind=='bearer':self.assertEqual(request.headers['Authorization'],'Bearer fixture-secret')
                if kind=='api_key_header':self.assertEqual(request.headers['X-API-Key'],'fixture-secret')
                if kind=='api_key_query':self.assertEqual(request.url.params['X-API-Key'],'fixture-secret')
                if kind=='basic':self.assertTrue(request.headers['Authorization'].startswith('Basic '))
                update=self.post('/api-connections',self.connection(id=item['id'],auth_type=kind))
                self.assertEqual(update['id'],item['id'])
                reference=api_connections.get(item['id'],'rei')['credential_ref']
                other=profiles.save_profile(profiles.template('general'),create=True)
                self.post('/api-connections/'+item['id']+'/check',{'profile_id':other['id']},404)
                self.assertEqual(self.client.get('/api/discovery/api-connections?profile_id='+other['id']).json()['connections'],[])
                self.post('/api-connections/'+item['id']+'/disconnect',{'profile_id':'rei'})
                self.assertIsNone(private_store.read('api',reference))

    def test_api_connection_query_stages_data_before_any_ai_call(self):
        requests=[]
        def handler(request):
            requests.append(request)
            return httpx.Response(200,json={'rows':self.rows})
        with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(handler),patch('backend.ai.AsyncOpenAI') as constructor:
            connection=self.post('/api-connections',self.connection())
            stage=self.post('/api-connections/'+connection['id']+'/query',{'profile_id':'rei','query':'evidence'})
            self.assertEqual(requests[-1].url.params['q'],'evidence')
            self.assertEqual(stage['total'],3)
            self.assertEqual(library.list_activities(kind='dataset'),[])
            constructor.assert_not_called()
            update_settings({'local_only':True})
            self.post('/api-connections/'+connection['id']+'/query',{'profile_id':'rei'},423)
            self.assertEqual(len(requests),2)

    def test_api_errors_do_not_echo_provider_secrets_or_follow_redirects(self):
        for status,expected in [(401,401),(403,401),(429,429),(500,502),(302,422)]:
            with self.subTest(status=status),patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(lambda request:httpx.Response(status,json={'secret':'DO-NOT-ECHO'},headers={'Location':'https://elsewhere.example/'})):
                value=self.post('/api-connections',self.connection(),expected)
                self.assertNotIn('DO-NOT-ECHO',json.dumps(value))
        self.assertEqual(api_connections.saved(),{})
        for url in ['http://example.org/data','https://localhost/data','https://user:secret@example.org/data','https://example.org/data?api_key=secret']:
            self.post('/api-connections',self.connection(url=url),422)
        with patch('backend.api_connections.asyncio.get_running_loop') as loop:
            loop.return_value.getaddrinfo=AsyncMock(return_value=[(None,None,None,None,('127.0.0.1',443))])
            self.post('/api-connections',self.connection(),422)

    def test_api_recommendations_use_profile_and_verified_catalog_only(self):
        result=api_connections.Recommendations(recommendations=[api_connections.Choice(service_id='clinicaltrials',reason='Review study design at your advanced level.')])
        client,context=self.ai_client(result)
        with patch.dict(os.environ,{'OPENAI_API_KEY':'sk-test-fixture'}),patch('backend.ai.AsyncOpenAI',return_value=context):
            response=self.post('/api-connections/recommend',{'profile_id':'rei'})
        self.assertEqual(response['recommendations'][0]['url'],'https://clinicaltrials.gov/api/v2/studies')
        sent=json.dumps(client.responses.parse.await_args.kwargs['input'])
        self.assertIn('advanced',sent)
        self.assertIn('catalog',sent)
        reference=json.loads(client.responses.parse.await_args.kwargs['input'][1]['content'].split('\n',1)[1])
        self.assertEqual(set(reference['reference_data']),{'catalog'})

    def test_api_empty_results_and_response_format_limits(self):
        with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(lambda request:httpx.Response(200,json={'rows':[]})):
            item=self.post('/api-connections',self.connection())
            self.assertEqual(item['sample_count'],0)
            self.post('/api-connections/'+item['id']+'/query',{'profile_id':'rei','query':'missing'},404)
        for response,expected in [(httpx.Response(200,text='not JSON'),422),
                                  (httpx.Response(200,content=b' '*(2*1024*1024+1),headers={'Content-Type':'application/json'}),413)]:
            with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(lambda request:response):
                self.post('/api-connections',self.connection(),expected)

    def test_failed_api_edit_retains_previous_endpoint_and_credentials(self):
        with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(lambda request:httpx.Response(200,json={'rows':[{'value':1}]})):
            item=self.post('/api-connections',self.connection(auth_type='bearer',credential='original-fixture-secret'))
        with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(lambda request:httpx.Response(401,json={'password':'new-fixture-secret'})):
            self.post('/api-connections',self.connection(id=item['id'],auth_type='bearer',credential='new-fixture-secret'),401)
        self.assertEqual(api_connections.credentials_for(api_connections.get(item['id'],'rei'))['credential'],'original-fixture-secret')
        self.assertEqual(api_connections.saved()[item['id']]['url'],item['url'])

    def test_connection_save_failure_cannot_send_new_credentials_to_old_endpoint(self):
        with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(lambda request:httpx.Response(200,json={'rows':[{'value':1}]})):
            item=self.post('/api-connections',self.connection(auth_type='bearer',credential='old-fixture-secret'))
            before=api_connections.get(item['id'],'rei')
            with patch('backend.api_connections.write_json',side_effect=OSError('Disk failure')):
                self.post('/api-connections',self.connection(id=item['id'],url='https://new.example/data',auth_type='bearer',credential='new-fixture-secret'),500)
        after=api_connections.get(item['id'],'rei')
        self.assertEqual(after,before)
        self.assertEqual(api_connections.credentials_for(after)['credential'],'old-fixture-secret')
        self.assertEqual(len(list(private_store.folder().glob('api-*.enc'))),1)

    def test_query_credentials_are_redacted_from_http_client_logs(self):
        with patch('backend.api_connections.public_address',new=AsyncMock()),self.transport(lambda request:httpx.Response(200,json={'rows':[{'value':1}]})),self.assertLogs('httpx',level='INFO') as logs:
            self.post('/api-connections',self.connection(auth_type='api_key_query',credential='fixture +private-token'))
        output='\n'.join(logs.output)
        self.assertNotIn('fixture',output)
        self.assertIn('credential removed',output)


if __name__=='__main__':
    unittest.main()
