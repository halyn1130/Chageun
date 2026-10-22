import json
import tempfile
import unittest
from pathlib import Path
from chageun_ai.core import chunk_pages, build_index, search, answer_from_hits, evaluate, ingest


def document(doc_id='k5', model='K5'):
    return {'doc_id': doc_id, 'title': '테스트 전용 가상 설명서', 'kind': 'manual',
            'source_url': 'https://example.invalid/test', 'retrieved_at': '2026-10-22',
            'revision': 'fixture-v1', 'file': 'raw/test.pdf', 'usage_note': 'synthetic fixture only',
            'manufacturer': '기아' if model == 'K5' else '현대', 'model': model,
            'model_year': 'TEST_YEAR', 'powertrain': 'TEST_POWERTRAIN'}


class PipelineTests(unittest.TestCase):
    def test_chunk_identity_pages_and_empty_page_report(self):
        doc = document()
        chunks, empty = chunk_pages(doc, ['첫째 페이지 ' * 40, '', '셋째 페이지'], 'hash', 100, 20)
        again, _ = chunk_pages(doc, ['첫째 페이지 ' * 40, '', '셋째 페이지'], 'hash', 100, 20)
        self.assertEqual(chunks, again)
        self.assertEqual(empty, [2])
        self.assertEqual(chunks[-1]['metadata']['pdf_page'], 3)
        self.assertTrue(all(c['metadata']['printed_page'] is None for c in chunks))
        self.assertEqual(len(chunks), len({c['chunk_id'] for c in chunks}))
        changed, _ = chunk_pages(doc, ['셋째 페이지'], 'changed-hash')
        self.assertNotEqual(changed[0]['chunk_id'], chunks[-1]['chunk_id'])

    def test_missing_vehicle_variant_is_rejected(self):
        doc = document()
        del doc['model_year']
        with self.assertRaises(ValueError):
            chunk_pages(doc, ['text'], 'hash')

    def make_index(self, folder):
        a, _ = chunk_pages(document(), ['K5 fixture'], 'a')
        b, _ = chunk_pages(document('avante', '디 올 뉴 아반떼'), ['Avante fixture'], 'b')
        corpus = folder / 'chunks.jsonl'
        corpus.write_text(''.join(json.dumps(c) + '\n' for c in a+b))
        build_index(corpus, folder / 'index', lambda texts: [[0, 1], [1, 0]], 'fake-test-embedding')
        return folder / 'index', a[0]

    def test_filter_before_ranking_prevents_wrong_car(self):
        with tempfile.TemporaryDirectory() as d:
            index, correct = self.make_index(Path(d))
            # Query resembles Avante more, but only K5 is an eligible candidate.
            filters = {k: correct['metadata'][k] for k in ('kind','manufacturer','model','model_year','powertrain')}
            hits = search(index, [1, 0], filters, 1)
            self.assertEqual(hits[0]['chunk']['chunk_id'], correct['chunk_id'])
            filters['model_year'] = 'OTHER_YEAR'
            self.assertEqual(search(index, [1, 0], filters), [])
            with self.assertRaises(ValueError):
                search(index, [1, 0], {'kind': 'manual'})

    def test_tampered_corpus_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            index, _ = self.make_index(Path(d))
            with (index / 'chunks.jsonl').open('a') as f:
                f.write('\n')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                search(index, [1, 0], {'kind': 'law'})

    def test_refuse_overwrite_and_bad_embedding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            index, _ = self.make_index(root)
            with self.assertRaises(FileExistsError):
                build_index(root/'chunks.jsonl', index, lambda texts: [[0,1],[1,0]], 'fake')
            with self.assertRaisesRegex(ValueError, 'zero embedding'):
                build_index(root/'chunks.jsonl', root/'invalid', lambda texts: [[0,0],[0,0]], 'fake')

    def test_unknown_citation_and_no_evidence_fail_closed(self):
        chunks, _ = chunk_pages(document(), ['fixture'], 'a')
        hits = [{'chunk': chunks[0], 'score': .5}]
        fake = lambda system, user: json.dumps({'status':'answered','answer_text':'답','speech_text':'답','citation_ids':['invented']})
        self.assertEqual(answer_from_hits('질문', hits, fake)['status'], 'insufficient_evidence')
        self.assertEqual(answer_from_hits('질문', hits, lambda *args: 'not JSON')['sources'], [])
        self.assertEqual(answer_from_hits('질문', [], lambda *args: self.fail('must not call model'))['sources'], [])
        good = lambda *args: json.dumps({'status':'answered','answer_text':'답','speech_text':'답','citation_ids':[chunks[0]['chunk_id']]})
        result = answer_from_hits('질문', hits, good)
        self.assertEqual(result['sources'][0]['pdf_page'], 1)
        self.assertEqual(result['sources'][0]['source_url'], document()['source_url'])

    def test_pending_cases_do_not_inflate_metrics(self):
        cases = [{'id':'draft','status':'draft','category':'rag'},
                 {'id':'ready','status':'reviewed','category':'rag','expected_chunk_ids':['a','b']}]
        report = evaluate(cases, lambda case: [{'chunk':{'chunk_id':'x'}},{'chunk':{'chunk_id':'a'}}])
        self.assertEqual(report['evaluated'], 1)
        self.assertEqual(report['pending'], 1)
        self.assertEqual(report['hit_rate'], 1)
        self.assertEqual(report['mean_recall'], .5)
        self.assertEqual(report['mrr'], .5)
        self.assertIsNone(evaluate(cases[:1], lambda case: [])['hit_rate'])

    def test_blank_pdf_requires_ocr_and_no_output(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'raw').mkdir()
            writer = PdfWriter()
            writer.add_blank_page(width=200, height=200)
            writer.write(root/'raw/test.pdf')
            registry = root/'registry.json'
            registry.write_text(json.dumps({'schema_version':1,'documents':[document()]}))
            with self.assertRaisesRegex(ValueError, 'OCR'):
                ingest(registry, root/'out')
            self.assertFalse((root/'out/chunks.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
