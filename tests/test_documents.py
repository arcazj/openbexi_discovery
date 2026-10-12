"""Document CRUD against isolated local storage; no credentials or provider calls."""
import base64
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.app import app
from backend import library
from backend.discovery_store import read_json, write_json


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DISCOVERY_DATA_DIR": self.temp.name,
            "DISCOVERY_LIBRARY_DIR": "", "OPENAI_API_KEY": ""})
        self.env.start()
        self.client = TestClient(app, client=("127.0.0.1", 50001))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()
        self.temp.cleanup()

    def post(self, path, value, status=200):
        response = self.client.post('/api/discovery' + path, json=value)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def document(self, **changes):
        return self.post('/library', {"kind": "document", "profile_id": "rei",
            "title": "Research document", "content": "Initial text", **changes})

    def edit(self, item, status=200, **changes):
        return self.post('/library/' + item['id'] + '/update', {
            "base_revision": item.get('revision', 1), "title": item['title'],
            "content": item['content'], **changes}, status)

    @staticmethod
    def upload(name, content):
        return {"filename": name, "file_base64": base64.b64encode(content).decode()}

    def file(self, item):
        return self.client.get('/api/discovery/library/' + item['id'] + '/file')

    def test_create_read_update_search_delete_same_document(self):
        item = self.document()
        untouched = self.document(title='Keep this document')
        edited = self.edit(item, title='Edited research', content='Updated evidence')
        self.assertEqual(edited['id'], item['id'])
        self.assertEqual(edited['revision'], 2)
        for key in ('created_at', 'profile_id', 'profile_snapshot', 'learning_level', 'themes'):
            self.assertEqual(edited[key], item[key])
        self.assertIn('updated_at', edited)
        read = self.client.get('/api/discovery/library/' + item['id']).json()
        self.assertEqual(read, edited)
        found = self.client.get('/api/discovery/library?q=Updated%20evidence&kind=document').json()['activities']
        self.assertEqual([x['id'] for x in found], [item['id']])
        self.assertEqual(len(library.list_activities(kind='document')), 2)
        self.post('/library/' + item['id'] + '/delete', {})
        self.assertEqual(self.client.get('/api/discovery/library/' + item['id']).status_code, 404)
        self.edit(item, status=404)
        self.assertEqual(self.file(item).status_code, 404)
        self.assertEqual([x['id'] for x in library.list_activities()], [untouched['id']])

    def test_text_attachment_edits_replacements_and_portable_archives(self):
        item = self.document(**self.upload('source.md', b'# Original'))
        self.assertEqual(item['content'], '# Original')
        self.assertEqual(self.file(item).content, b'# Original')
        changed = self.edit(item, content='# Updated\nUnicode: \u03b1')
        self.assertEqual(self.file(changed).content.decode(), changed['content'])
        self.assertEqual(changed['original_filename'], 'source.md')
        folder = library.find_path(item['id']).parent
        self.assertFalse((folder / item['filename']).exists())
        pdf = b'%PDF-1.4\nSynthetic PDF fixture\n%%EOF'
        replaced = self.edit(changed, content='Notes for the PDF', **self.upload('paper.PDF', pdf))
        self.assertEqual(self.file(replaced).content, pdf)
        self.assertIn('application/pdf', self.file(replaced).headers['content-type'])
        renamed = self.edit(replaced, title='Renamed PDF', content='Edited PDF notes')
        self.assertEqual(renamed['filename'], replaced['filename'])
        self.assertEqual(self.file(renamed).content, pdf)
        archive = library.open_zip(library.export_zip(activity=item['id']))
        portable = archive['activities'][0]
        self.assertEqual(portable['filename'], 'document.pdf')
        self.assertEqual(portable['content'], 'Edited PDF notes')
        self.assertEqual(library.import_zip(archive['id'])['skipped'], 1)
        library.delete_activity(item['id'])
        self.assertFalse(folder.exists())
        self.assertEqual(library.import_zip(archive['id'])['imported'], [item['id']])
        restored = library.get_activity(item['id'])
        self.assertEqual(self.file(restored).content, pdf)
        self.edit(restored, title='Edited imported document')
        self.assertEqual(len(library.list_activities(kind='document')), 1)

    def test_empty_file_and_credential_redaction(self):
        item = self.document(**self.upload('empty.txt', b''))
        self.assertEqual(self.file(item).status_code, 200)
        self.assertEqual(self.file(item).content, b'')
        edited = self.edit(item, content='Key: sk-document-fixture-not-real')
        self.assertEqual(edited['content'], 'Key: [credential omitted]')
        self.assertEqual(self.file(edited).text, edited['content'])
        emptied = self.edit(edited, **self.upload('empty-again.md', b''))
        self.assertEqual(emptied['content'], '')
        self.assertEqual(self.file(emptied).content, b'')

    def test_sensitive_consent_and_origin_survive_updates(self):
        item = self.document(sensitive=True, consent_local=True, provenance={'origin': 'ai', 'model': 'test-model'})
        self.edit(item, status=403, sensitive=False)
        edited = self.edit(item, sensitive=False, consent_local=True, content='Human edit')
        self.assertTrue(edited['sensitive'])
        self.assertEqual(edited['provenance']['origin'], 'ai_edited')
        self.assertEqual(edited['provenance']['model'], 'test-model')
        self.assertEqual(library.open_zip(library.export_zip(activity=item['id']))['activities'], [])

    def test_stale_or_invalid_updates_cannot_replace_saved_data(self):
        item = self.document(**self.upload('original.txt', b'Original'))
        for upload in [self.upload('../outside.txt', b'x'), self.upload('bad.exe', b'x'),
                       self.upload('bad.pdf', b'not a PDF'), self.upload('bad.txt', b'\xff'),
                       {'filename': 'bad.txt', 'file_base64': '!'}, {'filename': 'missing.txt'}]:
            with self.subTest(upload=upload):
                self.edit(item, status=422, **upload)
        self.edit(item, status=413, **self.upload('large.txt', b'A' * (library.MAX_FILE + 1)))
        self.assertEqual(library.get_activity(item['id']), item)
        self.assertEqual(self.file(item).content, b'Original')
        edited = self.edit(item, content='New version')
        self.edit(item, status=409, content='Stale version')
        self.assertEqual(library.get_activity(item['id']), edited)
        note = self.post('/library', {'kind': 'note', 'title': 'A note'})
        self.edit(note, status=422)

    def test_concurrent_edits_require_reopening_latest_version(self):
        item = self.document()
        def edit(content):
            return self.client.post('/api/discovery/library/' + item['id'] + '/update',
                json={'base_revision': 1, 'title': item['title'], 'content': content}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(edit, ['First edit', 'Second edit']))
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(library.get_activity(item['id'])['revision'], 2)

    def test_failed_metadata_write_preserves_document_and_attachment(self):
        item = self.document(**self.upload('original.txt', b'Original'))
        folder = library.find_path(item['id']).parent
        before = {file.name: file.read_bytes() for file in folder.iterdir()}
        with patch.object(library, 'write_json', side_effect=OSError('Synthetic disk failure')):
            with self.assertRaises(OSError):
                self.edit(item, **self.upload('replacement.md', b'Replacement'))
        self.assertEqual({file.name: file.read_bytes() for file in folder.iterdir()}, before)

    def test_large_and_legacy_text_previews_cannot_truncate_attachment(self):
        full_text = b'A' * 250100
        item = self.document(**self.upload('large.txt', full_text))
        self.assertTrue(item['content_truncated'])
        self.assertEqual(len(item['content']), 250000)
        # Simulate an imported document saved before revision/preview metadata existed.
        path = library.find_path(item['id'])
        legacy = read_json(path)
        del legacy['revision'], legacy['content_truncated']
        write_json(path, legacy)
        archive = library.open_zip(library.export_zip(activity=item['id']))
        self.assertEqual(library.import_zip(archive['id'])['skipped'], 1)
        loaded = library.get_activity(item['id'])
        self.assertTrue(loaded['content_truncated'])
        renamed = self.edit(loaded, title='Title only')
        self.assertEqual(self.file(renamed).content, full_text)
        self.edit(renamed, status=422, content='Partial edit')
        replaced = self.edit(renamed, **self.upload('replacement.txt', b'Complete replacement'))
        self.assertFalse(replaced['content_truncated'])
        self.assertEqual(self.file(replaced).content, b'Complete replacement')

    def test_ai_preview_consent_conflicts_and_scoped_context(self):
        item = self.document(content='Evidence for a summary. ' * 900)
        context = self.client.get('/api/discovery/library/' + item['id'] + '/ai-context').json()
        self.assertEqual(len(context['text']), 12000)
        self.assertIn('first 12,000 characters', context['scope'])
        request = {'action': 'summarize', 'context_hash': context['context_hash']}
        result = {'text': 'Synthetic summary', 'provenance': {'origin': 'ai', 'model': 'fixture'}}
        with patch('backend.ai.structured_task', new=AsyncMock(return_value=result)) as generate:
            self.post('/library/' + item['id'] + '/analyze', request, 403)
            generate.assert_not_awaited()
            response = self.post('/library/' + item['id'] + '/analyze', {**request, 'consent_ai': True})
            self.assertEqual(response['text'], 'Synthetic summary')
            sent = generate.await_args.args
            self.assertEqual(sent[3]['text'], context['text'])
            self.assertNotIn('file_base64', sent[3])
            self.assertEqual(len(library.list_activities()), 1, 'AI output is not silently persisted')
            self.edit(item, content='Changed text')
            self.post('/library/' + item['id'] + '/analyze', {**request, 'consent_ai': True}, 409)
            self.assertEqual(generate.await_count, 1)
            self.post('/settings', {'local_only': True})
            self.post('/library/' + item['id'] + '/analyze', {**request, 'consent_ai': True}, 423)
            self.assertEqual(generate.await_count, 1)

    def test_ai_does_not_bypass_dataset_review_or_claim_pdf_pages(self):
        dataset = self.post('/library', {'kind': 'dataset', 'title': 'Unreviewed data', 'payload': {'rows': [{'private': 'fixture'}]}})
        self.assertEqual(self.client.get('/api/discovery/library/' + dataset['id'] + '/ai-context').status_code, 422)
        self.post('/library/' + dataset['id'] + '/analyze', {'action': 'analyze', 'context_hash': '0'*64, 'consent_ai': True}, 422)
        pdf = self.document(content='', **self.upload('paper.pdf', b'%PDF-1.4 synthetic pages'))
        self.assertEqual(self.client.get('/api/discovery/library/' + pdf['id'] + '/ai-context').status_code, 422)
        self.edit(pdf, content='Researcher-provided notes')
        preview = self.client.get('/api/discovery/library/' + pdf['id'] + '/ai-context').json()
        self.assertEqual(preview['text'], 'Researcher-provided notes')
        self.assertIn('PDF notes only', preview['scope'])
        self.assertNotIn('synthetic pages', str(preview))


if __name__ == '__main__':
    unittest.main()
