import json
import unittest
from chageun_ai.agent import rag_query, TOOLS
from chageun_ai.core import chunk_law_pages, VERIFY_SYSTEM

LAW = {'doc_id': 'law', 'title': '가상법', 'kind': 'law', 'source_url': 'https://example.invalid/law',
       'retrieved_at': '2026-10-22', 'revision': 'fixture-v1', 'effective_date': '2026-10-01',
       'file': 'raw/law.pdf', 'usage_note': 'synthetic fixture only'}
CAR = {'manufacturer': '기아', 'model': 'K5', 'model_year': 'TEST_YEAR', 'powertrain': 'TEST_POWERTRAIN'}
VEHICLE = {'id': 3, **CAR, 'mileage_km': None}


def picks(name, **args):
    return lambda system, question, tools: (name, args)


class AgentTests(unittest.TestCase):
    def ask(self, choose, generate=None, retrieve=None, **request):
        request = {'request_id': 'req_1', 'question': '가상 질문입니다', 'vehicle': None, 'location': None,
                   'maintenance': {'lookup_status': 'not_requested', 'items': [], 'records': []}, 'history': [], **request}
        return rag_query(request, choose, retrieve or (lambda q, f: self.fail('must not search')),
                         generate or (lambda s, u: self.fail('must not generate')))

    def test_contract_fields_and_conversation_id(self):
        r = self.ask(picks('decline', kind='realtime'), conversation_id='c_1')
        self.assertEqual(set(r), {'request_id', 'conversation_id', 'status', 'answer', 'speech_text', 'sources',
                                  'needs_review', 'handoff', 'action', 'missing_fields'})
        self.assertEqual((r['status'], r['request_id'], r['conversation_id'], r['missing_fields']),
                         ('out_of_scope', 'req_1', 'c_1', []))
        self.assertTrue(self.ask(picks('decline', kind='unrelated'))['conversation_id'].startswith('c_'))
        with self.assertRaises(ValueError):
            self.ask(picks('decline'), question='가')

    def test_navigation_is_declined_and_maintenance_opens_my_car(self):
        r = self.ask(picks('decline', kind='navigation'))
        self.assertEqual((r['status'], r['action']), ('out_of_scope', None))
        self.assertIn('내비게이션', r['answer'])
        self.assertFalse({'find_places', 'show_route'} & {t['function']['name'] for t in TOOLS})
        self.assertEqual(self.ask(picks('open_maintenance', item='engine_oil'))['status'], 'need_vehicle')
        self.assertEqual(self.ask(picks('open_maintenance', item='engine_oil'), vehicle=VEHICLE)['action'],
                         {'type': 'open_my_car', 'vehicle_id': 3, 'item': 'engine_oil'})
        for item in ('oil_filter', 'cabin_filter', 'brake_fluid'):
            self.assertEqual(self.ask(picks('open_maintenance', item=item), vehicle=VEHICLE)['action'],
                             {'type': 'open_my_car', 'vehicle_id': 3, 'item': item})
        # Arguments outside the enums, unknown tools and no tool call are never passed to the UI.
        self.assertEqual(self.ask(picks('open_maintenance', item='hospital'), vehicle=VEHICLE)['status'], 'not_found')
        self.assertEqual(self.ask(picks('find_places', category='parking'))['status'], 'not_found')
        self.assertEqual(self.ask(lambda *a: None)['status'], 'not_found')

    def test_vague_warning_light_asks_back_and_shape_names_the_light(self):
        for question in ('지금 계기판에 빨간 불 들어왔어', '계기판에 빨간색 경고등이 켜졌는데 뭐야?'):
            for choice in (picks('search_manual', query='경고등'), picks('decline', kind='realtime')):
                r = self.ask(choice, question=question, vehicle=VEHICLE)
                self.assertEqual((r['status'], r['missing_fields']), ('need_clarification', ['warning_light']))
        seen, asked = [], []
        self.ask(picks('search_manual', query='경고등'), lambda s, u: asked.append(u) or '{}',
                 lambda q, f: seen.append(q) or [{'chunk': {'chunk_id': 'x', 'text': 't', 'metadata': {}}, 'score': 1}],
                 question='계기판에 주전자 모양 빨간 불이 켜졌어', vehicle=VEHICLE)
        self.assertIn('엔진 오일 압력 경고등', seen[0])
        self.assertIn('주전자 = 엔진 오일 압력 경고등', asked[0])
        # A light named outside the icon table is searched, not questioned.
        self.ask(picks('search_manual', query='냉각수'), lambda s, u: '{}', lambda q, f: seen.append(q) or [],
                 question='냉각수 경고등이 켜지면?', vehicle=VEHICLE)
        self.assertEqual(len(seen), 2)

    def test_law_search_cites_article_and_refusal_asks_review(self):
        chunks, _ = chunk_law_pages(LAW, ['제5조(가상 규칙) ① 모든 운전자는 가상 교차로에서 일시정지하여야 한다.'], 'h')
        seen = []
        retrieve = lambda query, filters: seen.append((query, filters)) or [{'chunk': chunks[0], 'score': 1}]
        good = lambda s, u: json.dumps({'supported': True}) if s == VERIFY_SYSTEM else json.dumps({'status': 'answered', 'answer_text': '일시정지해야 해요.', 'speech_text': '멈춰요.',
                                        'missing_terms': [], 'quotes': [{'chunk_id': chunks[0]['chunk_id'],
                                                                         'quote': '모든 운전자는 가상 교차로에서 일시정지하여야 한다.'}]})
        r = self.ask(picks('search_law', query='교차로 일시정지'), good, retrieve)
        self.assertEqual(seen, [('가상 질문입니다 교차로 일시정지', {'kind': 'law'})])
        self.assertEqual(r['status'], 'answered')
        self.assertEqual(r['sources'], [{'title': '가상법', 'page': '제5조', 'url': LAW['source_url']}])
        refused = self.ask(picks('search_law', query='x'), lambda s, u: '{}', retrieve)
        self.assertEqual((refused['status'], refused['needs_review'], refused['sources']), ('not_found', True, []))

    def test_manual_search_needs_vehicle_and_filters_by_it(self):
        r = self.ask(picks('search_manual', query='경고등'))
        self.assertEqual((r['status'], r['missing_fields']), ('need_vehicle', ['vehicle']))
        seen = []
        r = self.ask(picks('search_manual', query='경고등'), lambda s, u: self.fail('no manual, no model call'),
                     lambda q, f: seen.append(f) or [], vehicle=VEHICLE)
        self.assertEqual(seen, [{'kind': 'manual', **CAR}])
        self.assertEqual((r['status'], r['handoff']), ('not_found', True))
        self.assertIn('아직 등록되지 않았어요', r['answer'])

    def test_tool_schemas_are_strict(self):
        for t in TOOLS:
            params = t['function']['parameters']
            self.assertFalse(params['additionalProperties'])
            self.assertEqual(set(params['required']), set(params['properties']))

    def test_seat_heater_slang_keeps_original_question_and_adds_manual_term(self):
        seen, asked = [], []
        self.ask(picks('search_manual', query='열선 시트'), lambda s, u: asked.append(u) or '{}',
                 lambda q, f: seen.append(q) or [{'chunk': {'chunk_id': 'x', 'text': 't', 'metadata': {}}, 'score': 1}],
                 question='엉따 어떻게 켜?\n추가 정보 — 좌석: 운전석', vehicle=VEHICLE)
        self.assertIn('열선 시트', seen[0])
        self.assertIn('엉따 = 열선 시트', asked[0])
        self.assertIn('좌석: 운전석', asked[0])

    def test_followup_uses_only_recent_session_turns_for_routing_and_grounding(self):
        chunks, _ = chunk_law_pages(LAW, ['제5조(가상 규칙) ① 가상 교차로에서는 일시정지하여야 한다.'], 'h')
        history = [{'role': 'user', 'content': f'이전 질문 {i}'} for i in range(8)]
        history[-1] = {'role': 'user', 'content': '가상 교차로의 규칙은?'}
        routed, retrieved, generated = [], [], []
        def choose(system, question, tools):
            routed.append(json.loads(question))
            return 'search_law', {'query': '가상 교차로 일시정지'}
        def generate(system, question):
            if system == VERIFY_SYSTEM:
                return json.dumps({'supported': True})
            generated.append(json.loads(question))
            return json.dumps({'status': 'answered', 'answer_text': '일시정지해야 해요.',
                               'speech_text': '가상 교차로에서는 일시정지해야 해요.', 'missing_terms': [],
                               'quotes': [{'chunk_id': chunks[0]['chunk_id'], 'quote': '가상 교차로에서는 일시정지하여야 한다.'}]})
        def retrieve(query, filters):
            retrieved.append(query)
            return [{'chunk': chunks[0], 'score': 1}]
        result = self.ask(choose, generate, retrieve,
                          question='그럼 뭘 해야 해?', vehicle=VEHICLE, history=history)
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(routed[0]['question'], '그럼 뭘 해야 해?')
        self.assertEqual(routed[0]['history'], history[-6:])
        self.assertEqual(routed[0]['selected_vehicle'], '기아 K5')
        self.assertEqual(retrieved, ['가상 교차로 일시정지'])
        self.assertEqual(generated[0]['history'], history[-6:])
        self.assertEqual(generated[0]['question'], '그럼 뭘 해야 해?')

    def test_session_history_cannot_supply_a_citation_or_override_selected_vehicle(self):
        history = [{'role': 'assistant', 'content': '예전 답변의 내용은 근거가 아니다.'}]
        seen = []
        self.ask(picks('search_manual', query='열선 시트'), lambda s, u: '{}',
                 lambda q, f: seen.append(f) or [], question='그건 어떻게 써?', vehicle=VEHICLE, history=history)
        self.assertEqual(seen, [{'kind': 'manual', **CAR}])
        chunks, _ = chunk_law_pages(LAW, ['제5조(가상 규칙) 가상 내용이다.'], 'h')
        fabricated = lambda s, u: json.dumps({'status': 'answered', 'answer_text': '과거 답', 'speech_text': '과거 답',
                                              'missing_terms': [], 'quotes': [{'chunk_id': 'from_history', 'quote': history[0]['content']}]})
        result = self.ask(picks('search_law', query='가상'), fabricated,
                          lambda q, f: [{'chunk': chunks[0], 'score': 1}], history=history)
        self.assertEqual(result['status'], 'not_found')
        self.assertEqual(result['sources'], [])

    def test_unclear_followup_requests_clarification_with_existing_response_fields(self):
        result = self.ask(picks('ask_missing_detail', missing_detail='symptom', question='어떤 부분이 궁금하신가요?'), question='뭐가 문제야?')
        self.assertEqual((result['status'], result['missing_fields']), ('need_clarification', ['question']))
        self.assertEqual(result['answer'], '어떤 부분이 궁금하신가요?')
        self.assertEqual(result['sources'], [])


if __name__ == '__main__':
    unittest.main()
