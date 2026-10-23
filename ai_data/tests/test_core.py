import json
import tempfile
import unittest
from pathlib import Path
from chageun_ai.core import (chunk_pages, chunk_law_pages, chunk_manual_pages, chunk_appendix_pages, build_index, search,
                              answer_from_hits, evaluate, ingest, VERIFY_SYSTEM)

SUPPORTED = json.dumps({'supported': True, 'unsupported': []})


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

    def test_law_chunks_follow_articles_across_pages(self):
        doc = {'doc_id': 'law', 'title': '가상법', 'kind': 'law', 'source_url': 'https://example.invalid/law',
               'retrieved_at': '2026-10-22', 'revision': 'fixture-v1', 'effective_date': '2026-10-01',
               'file': 'raw/law.pdf', 'usage_note': 'synthetic fixture only'}
        pages = ['법제처 1 국가법령정보센터\n가상법\n가상법\n[시행 2026. 10. 1.] [법률 제1호, 2026. 10. 1., 제정]\n'
                 '가상청 (가상계) 02-0000-0000\n제1장 총칙 <개정 2020. 1. 1.>\n'
                 '제1조(목적) 이 법은 가상 목적을 정한\n다. <개정 2020. 1. 1.>\n제2조 삭제 <2021. 1. 1.>\n'
                 '제3조(정의(가상)) ① 첫째 항의 내용이 다음 페이지로',
                 '법제처 2 국가법령정보센터\n가상법\n이어진다.\n1. 첫째 호\n[전문개정 2022. 1. 1.]\n'
                 '부칙 <제1호,2026. 10. 1.>\n제1조(시행일) 부칙은 조문이 아니다.']
        chunks, empty = chunk_law_pages(doc, pages, 'hash')
        self.assertEqual(empty, [])
        self.assertEqual([c['metadata']['article'] for c in chunks], ['제1조', '제3조'])
        first, third = (c['metadata'] for c in chunks)
        self.assertEqual((first['section'], first['pdf_page'], third['article_title']), ('제1장 총칙', 1, '정의(가상)'))
        self.assertEqual(chunks[0]['text'], '[가상법] 제1조(목적) 이 법은 가상 목적을 정한다.')
        self.assertEqual(chunks[1]['text'], '[가상법] 제3조(정의(가상)) ① 첫째 항의 내용이 다음 페이지로이어진다.\n1. 첫째 호')
        long, _ = chunk_law_pages(doc, ['제9조(긴 조문) ① ' + '가' * 150 + '\n② ' + '나' * 150], 'hash', size=200)
        self.assertEqual(len(long), 2)
        self.assertTrue(long[1]['text'].startswith('[가상법] 제9조(긴 조문) (계속)\n②'))
        self.assertEqual(len({c['chunk_id'] for c in long}), 2)

    def test_manual_chunks_follow_sections(self):
        doc = document()
        footer = '가상  설명서  ( 웹  매뉴얼  변환본 ) · {}/4'
        pages = ['표지\n' + footer.format(1), '[p.9-14 · PDF 396]정기 점검 > 엔진 오일\n오일을 점검하십시오.\n' + footer.format(2),
                 '다음 페이지에 이어진다.\n' + footer.format(3), '[chapter8_1.html]정기 점검 > 냉각수\n냉각수를 확인하십시오.']
        chunks, _ = chunk_manual_pages(doc, pages, 'hash')
        self.assertEqual([(c['metadata']['section'], c['metadata']['printed_page'], c['metadata']['pdf_page']) for c in chunks],
                         [('정기 점검 > 엔진 오일', '9-14', 2), ('정기 점검 > 냉각수', None, 4)])
        self.assertEqual(chunks[0]['text'], '[테스트 전용 가상 설명서] 정기 점검 > 엔진 오일\n오일을 점검하십시오.\n다음 페이지에 이어진다.')

    def test_appendix_signs_become_one_chunk_each(self):
        doc = {'doc_id': 'law-a6', 'title': '가상규칙 [별표 6] 가상 표지', 'kind': 'law',
               'source_url': 'https://example.invalid/law', 'retrieved_at': '2026-10-22', 'revision': 'fixture-v1',
               'effective_date': '2026-10-01', 'file': 'raw/a6.pdf', 'usage_note': 'synthetic fixture only'}
        pages = ['Ⅰ. 일반기준\n표지 색은 흑색으로 한다.\n3. 지시표지\n329 비 보 호\n좌 회 전\n표지\n·좌회전을 조심스럽\n게 할 수 있다는 것',
                 '330 삭제<2007.9.28>\n5. 노면표시\n542 비 보 호\n표시\n•좌회전 표시']
        chunks, _ = chunk_appendix_pages(doc, pages, 'hash')
        self.assertEqual([(c['metadata']['article'], c['metadata']['section'], c['metadata']['article_title']) for c in chunks],
                         [('별표 6', None, None), ('별표 6', '지시표지', '329 비보호좌회전표지'), ('별표 6', '노면표시', '542 비보호표시')])
        self.assertTrue(chunks[1]['text'].startswith('[가상규칙 [별표 6] 가상 표지] 지시표지 329 비보호좌회전표지\n·좌회전'))

    def test_appendix_table_rows_keep_their_own_label(self):
        doc = {'doc_id': 'law-a2', 'title': '가상규칙 [별표 2] 가상 신호', 'kind': 'law',
               'source_url': 'https://example.invalid/law', 'retrieved_at': '2026-10-22', 'revision': 'fixture-v1',
               'effective_date': '2026-10-01', 'file': 'raw/a2.pdf', 'usage_note': 'synthetic fixture only'}
        pages = ['차 량\n신호등\n황색의\n등화\n1. 차마는 정지하여\n야 한다.\n황색\n등화의\n점멸\n차마는 주의하며 진행할 수 있다.\n'
                 '적색화살\n표의 등\n화\n화살표 방향 차마는 정지하여야 한다.\n황색화 차마는 주의하며 화살표',
                 '살표등\n화의 점\n멸\n방향으로 진행할 수 있다.\n비고\n1. 가상 비고이다.']
        chunks, _ = chunk_appendix_pages(doc, pages, 'hash')
        rows = {c['metadata']['article_title']: c['text'].split('\n', 1)[1] for c in chunks}
        self.assertEqual(rows['차량신호등 황색의등화'], '1. 차마는 정지하여야 한다.')
        self.assertEqual(rows['차량신호등 황색등화의점멸'], '차마는 주의하며 진행할 수 있다.')
        self.assertEqual(rows['차량신호등 황색화살표등화의점멸'], '차마는 주의하며 화살표방향으로 진행할 수 있다.')
        self.assertEqual(rows['비고'], '1. 가상 비고이다.')

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

    def test_hybrid_search_lifts_keyword_match(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            texts = ['교차로에서 우회전하려는 경우 서행', '주차금지 장소의 지정', '운전면허 시험 응시']
            chunks = [chunk_pages(dict(document(), kind='law', doc_id=f'law{i}', effective_date='2026-10-01'),
                                  [t], str(i))[0][0] for i, t in enumerate(texts)]
            (root / 'chunks.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in chunks))
            build_index(root / 'chunks.jsonl', root / 'index', lambda t: [[0, 1], [.1, 1], [1, 0]], 'fake')
            # The dense vector favours the licence chunk; the keyword ranking pulls the 우회전 chunk to the top.
            self.assertEqual(search(root / 'index', [1, 0], {'kind': 'law'}, 1)[0]['chunk']['text'], texts[2])
            hits = search(root / 'index', [1, 0], {'kind': 'law'}, 3, query='우회전할 때 서행?')
            self.assertEqual(hits[0]['chunk']['text'], texts[0])
            self.assertEqual(len(hits), 3)

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
        chunks, _ = chunk_pages(document(), ['가상 설명서의 엔진오일 점검 문장이다. (괄호 설명) 계기판을 확인한다.'], 'a')
        hits = [{'chunk': chunks[0], 'score': .5}]
        cid = chunks[0]['chunk_id']
        # The fake model answers, then approves its own answer in the verification pass.
        reply = lambda quotes, verdict=SUPPORTED, **extra: lambda system=None, user=None: verdict if system == VERIFY_SYSTEM else json.dumps(
            {'status': 'answered', 'answer_text': '답', 'speech_text': '답', 'missing_terms': [], 'quotes': quotes, **extra})
        refused = lambda make: answer_from_hits('질문', hits, make)['status'] == 'insufficient_evidence'
        self.assertTrue(refused(reply([{'chunk_id': 'invented', 'quote': '가상 설명서의 엔진오일 점검 문장이다.'}])))
        self.assertTrue(refused(reply([{'chunk_id': cid, 'quote': '가상 설명서의 냉각수 교환 주기는 매년이다.'}])))
        self.assertTrue(refused(reply([{'chunk_id': cid, 'quote': '가상 설명서의 엔진오일 점검 문장이다.'}],
                                      missing_terms=['냉각수'])))
        self.assertTrue(refused(reply([])))
        self.assertEqual(answer_from_hits('질문', hits, lambda *args: 'not JSON')['sources'], [])
        self.assertEqual(answer_from_hits('질문', [], lambda *args: self.fail('must not call model'))['sources'], [])
        # Dropping a parenthetical and changing spacing still counts as a faithful quote.
        good = reply([{'chunk_id': cid, 'quote': '엔진오일 점검 문장이다. 계기판을 확인 한다.'}])
        result = answer_from_hits('질문', hits, good)
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['sources'][0]['pdf_page'], 1)
        self.assertEqual(result['sources'][0]['source_url'], document()['source_url'])
        fenced = lambda system, user: '```json\n' + good(system, user) + '\n```'
        self.assertEqual(answer_from_hits('질문', hits, fenced)['status'], 'answered')
        # A real quote wrapped in claims the evidence does not make is rejected by the verification pass.
        quote = [{'chunk_id': cid, 'quote': '가상 설명서의 엔진오일 점검 문장이다.'}]
        self.assertTrue(refused(reply(quote, json.dumps({'supported': False, 'unsupported': ['답']}))))
        self.assertTrue(refused(reply(quote, 'not JSON')))

    def test_quote_may_join_an_item_to_its_lead_sentence(self):
        from chageun_ai.core import quoted_in
        text = '모든 차의 운전자는 다음 각 호의 곳에서는 차를 정차하거나 주차하여서는 아니 된다. 4. 가상 정류지로부터 10미터 이내인 곳'
        self.assertTrue(quoted_in('가상 정류지로부터 10미터 이내인 곳에서는 차를 정차하거나 주차하여서는 아니 된다.', text))
        self.assertFalse(quoted_in('가상 정류지로부터 5미터 이내인 곳에서는 주차할 수 있다.', text))

    def test_answer_naming_another_engine_is_rejected(self):
        doc = dict(document(), other_powertrain_terms=['LPI'])
        chunks, _ = chunk_pages(doc, ['가솔린 엔진 오일 점검 항목이다. LPI 연료 필터 점검 항목이다.'], 'a')
        hits = [{'chunk': chunks[0], 'score': .5}]
        make = lambda text: lambda system, user: SUPPORTED if system == VERIFY_SYSTEM else json.dumps(
            {'status': 'answered', 'answer_text': text, 'speech_text': '점검해요.', 'missing_terms': [],
             'quotes': [{'chunk_id': chunks[0]['chunk_id'], 'quote': '가솔린 엔진 오일 점검 항목이다.'}]})
        self.assertEqual(answer_from_hits('질문', hits, make('엔진 오일을 점검해요.'), 'K5 G2.0')['status'], 'answered')
        self.assertEqual(answer_from_hits('질문', hits, make('엔진 오일과 LPI 연료 필터를 점검해요.'), 'K5 G2.0')['status'],
                         'insufficient_evidence')
        # The model gets one retry told which engine words to drop.
        answers = iter(['엔진 오일과 LPI 연료 필터를 점검해요.', '엔진 오일을 점검해요.'])
        retried = lambda system, user: SUPPORTED if system == VERIFY_SYSTEM else make(next(answers))(system, user)
        self.assertEqual(answer_from_hits('질문', hits, retried, 'K5 G2.0')['answer_text'], '엔진 오일을 점검해요.')

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
