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
        # Arguments outside the enums, unknown tools and no tool call are never passed to the UI.
        self.assertEqual(self.ask(picks('open_maintenance', item='hospital'), vehicle=VEHICLE)['status'], 'not_found')
        self.assertEqual(self.ask(picks('find_places', category='parking'))['status'], 'not_found')
        self.assertEqual(self.ask(lambda *a: None)['status'], 'not_found')

    def test_warning_light_is_asked_one_question_at_a_time(self):
        manual = picks('search_manual', query='경고등')
        ask = lambda question, history=(): self.ask(manual, question=question, vehicle=VEHICLE, history=list(history))
        # A colour alone names no light: ask the shape, without a list of examples.
        for question in ('지금 계기판에 빨간 불 들어왔어', '이상해 무슨 불이 켜졌어'):
            r = ask(question)
            self.assertEqual((r['status'], r['missing_fields'], r['answer']),
                             ('need_clarification', ['warning_light'], '어떤 경고등인지 알 수 있게 어떤 모양인지 알려 주세요.'))
        # The decline tool is overridden for a lit light ("지금" made the router think of a road judgement).
        self.assertEqual(self.ask(picks('decline', kind='realtime'), question='지금 계기판에 빨간 불 들어왔어',
                                  vehicle=VEHICLE)['status'], 'need_clarification')
        # Shape given: ask the colour next, unless it was already said.
        history = [{'role': 'user', 'content': '이상해 무슨 불이 켜졌어'},
                   {'role': 'assistant', 'content': ask('이상해 무슨 불이 켜졌어')['answer']}]
        r = ask('주전자 모양이야', history)
        self.assertEqual((r['status'], r['missing_fields']), ('need_clarification', ['warning_light_color']))
        history += [{'role': 'user', 'content': '주전자 모양이야'}, {'role': 'assistant', 'content': r['answer']}]
        # Colour given: the whole exchange is answered as the light itself.
        seen, asked = [], []
        hit = [{'chunk': {'chunk_id': 'x', 'text': 't', 'metadata': {}}, 'score': 1}]
        self.ask(manual, lambda s, u: asked.append(u) or '{}', lambda q, f: seen.append(q) or hit,
                 question='빨간색이야', vehicle=VEHICLE, history=history)
        self.assertTrue(seen[0].startswith('이상해 무슨 불이 켜졌어 주전자 모양이야 빨간색이야'))
        self.assertIn('엔진 오일 압력 경고등', seen[0])
        self.assertTrue(json.loads(asked[0])['question'].startswith('엔진 오일 압력 경고등이 빨간색으로 켜졌어요.'))
        # Colour said up front, or "모르겠어": no colour question.
        self.ask(manual, lambda s, u: '{}', lambda q, f: seen.append(q) or [], question='주전자 모양 빨간 불이 켜졌어',
                 vehicle=VEHICLE)
        self.ask(manual, lambda s, u: '{}', lambda q, f: seen.append(q) or [], question='모르겠어', vehicle=VEHICLE,
                 history=history)
        self.assertEqual(len(seen), 3)
        # A named light is answered at once; so is one outside the icon table.
        self.ask(manual, lambda s, u: '{}', lambda q, f: seen.append(q) or [], question='엔진 경고등이 켜졌어',
                 vehicle=VEHICLE)
        self.ask(manual, lambda s, u: '{}', lambda q, f: seen.append(q) or [], question='냉각수 경고등이 켜지면?',
                 vehicle=VEHICLE)
        self.assertEqual(len(seen), 5)

    def test_colour_unlike_the_legal_colour_adds_a_note(self):
        chunk = {'chunk_id': 'x', 'text': '엔진 오일 압력 경고등은 엔진 오일이 부족하면 켜집니다.',
                 'metadata': {'title': '설명서', 'section': '경고등', 'source_url': 'u'}}
        answer = lambda s, u: json.dumps({'supported': True}) if s == VERIFY_SYSTEM else json.dumps(
            {'status': 'answered', 'answer_text': '무슨 뜻: 오일이 부족해요.', 'speech_text': '오일을 확인하세요.',
             'missing_terms': [], 'quotes': [{'chunk_id': 'x', 'quote': '엔진 오일 압력 경고등은 엔진 오일이 부족하면 켜집니다.'}]})
        r = self.ask(picks('search_manual', query='경고등'), answer, lambda q, f: [{'chunk': chunk, 'score': 1}],
                     question='주전자 모양 노란 불이 켜졌어', vehicle=VEHICLE)
        self.assertIn('법에서 빨간색으로 정한 경고등', r['answer'])
        self.assertEqual(r['sources'][-1]['page'], '별표 2')

    def test_signal_rows_not_asked_about_are_left_out(self):
        from chageun_ai.agent import focus_signal_rows
        row = lambda title: {'chunk': {'chunk_id': title, 'text': title,
                                       'metadata': {'doc_id': 'road-traffic-act-rule-appendix-2', 'article_title': title}}}
        hits = [row('차량신호등 황색의등화'), row('차량신호등 황색등화의점멸'), row('차량신호등 황색화살표등화의점멸'),
                row('버스신호등 황색등화의점멸'), {'chunk': {'chunk_id': 'law', 'text': '', 'metadata': {'doc_id': 'act'}}}]
        ids = lambda question: [h['chunk']['chunk_id'] for h in focus_signal_rows(question, hits)]
        self.assertEqual(ids('황색 신호가 깜빡이면? 점멸'), ['차량신호등 황색등화의점멸', 'law'])
        self.assertEqual(ids('노란불이면 어떻게 해? 황색의 등화'), ['차량신호등 황색의등화', 'law'])
        self.assertEqual(ids('녹색 화살표면?'), [h['chunk']['chunk_id'] for h in hits])  # nothing fits: unchanged

    def test_follow_up_question_is_routed_with_the_previous_one(self):
        routed = []
        choose = lambda system, question, tools: routed.append(question) or ('decline', {'kind': 'unrelated'})
        self.ask(choose, question='그럼 가혹조건은 뭐야?', history=[
            {'role': 'user', 'content': '엔진오일 교환 기준 알려줘'}, {'role': 'assistant', 'content': '기준이 달라요.'}])
        self.assertIn('[이전 질문: 엔진오일 교환 기준 알려줘]', routed[0])

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


if __name__ == '__main__':
    unittest.main()
