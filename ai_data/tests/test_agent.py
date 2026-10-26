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

    def test_fuel_focus_excludes_adjacent_warning_instructions(self):
        from chageun_ai.agent import focus_fuel_evidence
        fuel = '연료의 잔류량이 적을 때 경고등이 켜집니다. 경고등이 켜지면 바로 연료를 보충하십시오.'
        hit = {'score': 1, 'chunk': {'chunk_id': 'fuel', 'metadata': {'section': '클러스터 > 경고등 및 표시등'},
               'text': '제목\n엔진 오일 압력 경고등\n오일을 점검하세요.\n연료 부족 경고등\n' + fuel + '\nLPG 과충전 경고등\nLPG 점검 안내'}}
        focused = focus_fuel_evidence([hit])
        self.assertEqual(focused[0]['chunk']['text'], '연료 부족 경고등\n' + fuel)
        self.assertEqual(focused[0]['chunk']['chunk_id'], 'fuel')
        self.assertIn('LPG 점검 안내', hit['chunk']['text'])  # original corpus is untouched
        unrelated = {'score': 1, 'chunk': {'chunk_id': 'other', 'metadata': {}, 'text': '다른 항목'}}
        self.assertEqual(focus_fuel_evidence([unrelated]), [unrelated])

    def test_fuel_alias_reaches_answer_evidence(self):
        from unittest.mock import patch
        seen = []
        hit = {'chunk': {'chunk_id': 'fuel', 'text': '연료 부족 경고등', 'metadata': {}}, 'score': 1}
        with patch('chageun_ai.agent.answer_from_hits', return_value={
            'status': 'answered', 'answer_text': '안내', 'speech_text': '안내', 'sources': []
        }) as answer:
            r = self.ask(picks('search_manual', query='연료계 확인'),
                         retrieve=lambda q, f: seen.append((q, f)) or [hit],
                         question='주유등이 켜졌어. 계기판에서 무엇을 확인해?', vehicle=VEHICLE)
        self.assertEqual(r['status'], 'answered')
        self.assertIn('연료 부족 경고등', seen[0][0])
        self.assertIn('연료 부족 경고등이 켜졌어', answer.call_args.args[0])
        self.assertNotIn('주유등', answer.call_args.args[0])
        self.assertEqual(answer.call_args.args[4], 'solution')

    def test_contract_fields_and_conversation_id(self):
        r = self.ask(picks('decline', kind='unrelated'), conversation_id='c_1')
        self.assertEqual(set(r), {'request_id', 'conversation_id', 'status', 'answer', 'speech_text', 'sources',
                                  'needs_review', 'handoff', 'action', 'missing_fields'})
        self.assertEqual((r['status'], r['request_id'], r['conversation_id'], r['missing_fields']),
                         ('out_of_scope', 'req_1', 'c_1', []))
        self.assertTrue(self.ask(picks('decline', kind='unrelated'))['conversation_id'].startswith('c_'))
        with self.assertRaises(ValueError):
            self.ask(picks('decline'), question='가')

    def test_described_road_scene_is_answered_from_the_law_not_declined(self):
        """Planned behaviour: the driver describes the scene and gets the rule for it (router chose decline)."""
        from unittest.mock import patch
        hit = {'chunk': {'chunk_id': 'lane', 'text': '점선이 있는 쪽에서는 진로를 변경할 수 있다', 'metadata': {'article': '별표 6'}},
               'score': 1}
        searched = []
        with patch('chageun_ai.agent.answer_from_hits', return_value={
                'status': 'answered', 'answer_text': '점선이면 바꿀 수 있어요.', 'speech_text': '점선이면 바꿀 수 있어요.',
                'sources': [{'chunk_id': 'lane', 'article': '별표 6', 'title': '가상법', 'source_url': 'https://example.invalid/law'}]}):
            for question in ('차선이 점선인데 변경해도 돼?', '신호등이 노란불로 바뀌었는데 지나가도 돼?',
                             '터널 안에서 차선 바꿔도 돼?', '교차로가 막혀 있는데 들어가도 돼?'):
                r = self.ask(picks('decline', kind='realtime'), question=question,
                             retrieve=lambda q, f: searched.append(f) or [hit])
                self.assertEqual(r['status'], 'answered', question)
        self.assertTrue(all(f == {'kind': 'law'} for f in searched))

    def test_scene_without_description_asks_the_driver_to_describe_it(self):
        for question in ('지금 가도 돼?', '지금 우회전해도 괜찮아?'):  # a manoeuvre alone is not a scene
            r = self.ask(picks('decline', kind='realtime'), question=question)
            self.assertEqual((r['status'], r['missing_fields']), ('need_clarification', ['road_situation']), question)
        self.assertIn('알려 주세요', r['answer'])
        # The router may search such a question itself; with no scene there is nothing to apply the rule to.
        r = self.ask(picks('search_law', query='유턴'), question='여기서 유턴해도 돼?')
        self.assertEqual(r['status'], 'need_clarification')

    def test_everyday_law_words_reach_the_search_query_and_the_answer(self):
        from unittest.mock import patch
        hit = {'chunk': {'chunk_id': 'x', 'text': '근거', 'metadata': {'article': '제29조'}}, 'score': 1}
        cases = {'뒤에서 소방차가 사이렌 켜고 오면 어떻게 해?': ('긴급자동차의 우선 통행 진로 양보', '소방차 = 긴급자동차'),
                 '버스전용차로로 달려도 돼?': ('전용차로', '버스전용차로 = 전용차로'),
                 '신호등이 노란불로 바뀌었는데 지나가도 돼?': ('차량신호등', '노란불 = 황색의 등화')}
        for question, (in_query, in_asked) in cases.items():
            queries = []
            with patch('chageun_ai.agent.answer_from_hits', return_value={'status': 'insufficient_evidence'}) as answer:
                self.ask(picks('search_law', query=question), question=question,
                         retrieve=lambda q, f: queries.append(q) or [hit])
            self.assertIn(in_query, queries[0], question)
            self.assertIn(in_asked, answer.call_args.args[0], question)

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

    def test_frontend_clarified_question_is_answered_without_asking_again(self):
        manual = picks('search_manual', query='경고등')
        seen = []
        ask = lambda details: self.ask(manual, lambda s, u: '{}', lambda q, f: seen.append(q) or [],
                                       question=f'이상해 무슨 불이 켜졌어\n추가 정보 — {details}', vehicle=VEHICLE)
        # The frontend asks colour, shape and blinking itself, then sends one question.
        for details, light in (('색: 빨간색; 모양: 주전자 모양; 점멸: 계속 켜져 있음', '엔진 오일 압력 경고등'),
                               ('색: 노란색; 모양: 말발굽 모양; 점멸: 깜빡임', '저압 타이어 경고등'),
                               ('색: 빨간색; 모양: 느낌표 모양; 점멸: 깜빡임', '브레이크 경고등')):
            self.assertEqual(ask(details)['status'], 'not_found')  # searched (no hits in this fake), not asked
            self.assertIn(light, seen[-1])
        # A shape we have no entry for is searched as described, not asked for again.
        self.assertEqual(ask('색: 빨간색; 모양: 온도계 모양')['status'], 'not_found')
        # "다른 색이에요" answered the colour question; it is not asked again.
        r = self.ask(manual, lambda s, u: '{}', lambda q, f: seen.append(q) or [], vehicle=VEHICLE,
                     question='이상해 무슨 불이 켜졌어\n추가 정보 — 모양: 주전자 모양\n확인 질문: 불빛이 어떤 색인가요?\n사용자 답변: 다른 색이에요')
        self.assertEqual(r['status'], 'not_found')

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

    def test_only_the_retry_after_a_rejected_answer_uses_the_stronger_writer(self):
        from chageun_ai.core import answer_from_hits
        rule = '차마는 정지한 후 다른 차마의 교통을 방해하지 않고 우회전할 수 있다.'
        hits = [{'chunk': {'chunk_id': 'x', 'text': rule, 'metadata': {'title': '법', 'source_url': 'u'}}, 'score': 1}]
        answer = lambda text: json.dumps({'status': 'answered', 'answer_text': text, 'speech_text': text, 'missing_terms': [],
                                          'quotes': [{'chunk_id': 'x', 'quote': rule}]})
        writers = []
        def generate(system, user):
            if system == VERIFY_SYSTEM:  # the verifier stays the same model and rejects the wrong first answer
                return json.dumps({'supported': '할 수 있어요' in json.loads(user)['answer'], 'unsupported': ['우회전할 수 없어요.']})
            writers.append('first')
            return answer('우회전할 수 없어요.')
        def retry(system, user):
            writers.append('retry')
            return answer('정지한 뒤 방해하지 않으면 우회전할 수 있어요.')
        result = answer_from_hits('빨간불에 우회전해도 돼?', hits, generate, retry_generate=retry)
        self.assertEqual((result['status'], writers), ('answered', ['first', 'retry']))

    def test_a_crash_is_answered_with_what_to_do_now_not_asked_about(self):
        queries = []
        for choose, question in ((picks('ask_missing_detail', missing_detail='situation', question='어떤 사고였나요?'), '교통사고가 났어.'),
                                 (picks('search_law', query='횡단보도에서 보행자 보호 의무'), '내가 횡단보도를 건너는 사람을 쳤어')):
            r = self.ask(choose, lambda s, u: '{}', lambda q, f: queries.append((q, f)) or [], question=question)
            self.assertEqual(r['status'], 'not_found', question)  # searched (no hits in this fake), not asked back
        self.assertTrue(all('사고발생 시의 조치' in q and f == {'kind': 'law'} for q, f in queries))

    def test_a_cited_give_up_is_rechecked_only_by_the_stronger_writer(self):
        from chageun_ai.core import answer_from_hits
        rule = '교통사고가 난 경우 운전자는 즉시 정차하여 사상자를 구호하여야 한다.'
        hits = [{'chunk': {'chunk_id': 'x', 'text': rule, 'metadata': {'title': '법', 'source_url': 'u'}}, 'score': 1}]
        gave_up = json.dumps({'status': 'insufficient_evidence', 'answer_text': '', 'speech_text': '',
                              'missing_terms': ['상대방의 상태'], 'cites': ['c1.1']})
        fixed = json.dumps({'status': 'answered', 'answer_text': '즉시 정차하고 구호해야 해요.', 'speech_text': '정차하고 구호하세요.',
                            'missing_terms': [], 'quotes': [{'chunk_id': 'x', 'quote': rule}]})
        verify = lambda s, u: json.dumps({'supported': True}) if s == VERIFY_SYSTEM else gave_up
        self.assertEqual(answer_from_hits('그냥 가도 돼?', hits, verify)['status'], 'insufficient_evidence')
        result = answer_from_hits('그냥 가도 돼?', hits, verify, retry_generate=lambda s, u: fixed)
        self.assertEqual(result['status'], 'answered')

    def test_a_stopped_car_gets_the_first_step_and_the_manual_without_questions(self):
        seen = []
        ask_again = picks('ask_missing_detail', missing_detail='symptom', question='어떤 증상이 있었나요?')
        r = self.ask(ask_again, lambda s, u: '{}', lambda q, f: seen.append((q, f)) or [], question='방금 차가 멈췄어',
                     vehicle=VEHICLE)
        self.assertTrue(r['answer'].startswith('먼저 비상등을 켜고'))
        self.assertIn('주행 중 시동이 꺼졌을 때', seen[0][0])
        self.assertEqual(seen[0][1]['kind'], 'manual')
        crash = self.ask(picks('search_law', query='사고'), lambda s, u: '{}', lambda q, f: [], question='교통사고가 났어')
        self.assertIn('119', crash['answer'].split('\n')[0])  # said even though the lookup found nothing

    def test_the_router_asks_back_once_then_we_answer_with_what_we_have(self):
        ask_again = picks('ask_missing_detail', missing_detail='symptom', question='어떤 소리가 나나요?')
        self.assertEqual(self.ask(ask_again, question='차에서 이상한 느낌이 나', vehicle=VEHICLE)['status'], 'need_clarification')
        seen = []
        r = self.ask(ask_again, lambda s, u: '{}', lambda q, f: seen.append(q) or [], vehicle=VEHICLE,
                     question='차에서 이상한 느낌이 나\n확인 질문: 어떤 소리가 나나요?\n사용자 답변: 소리는 없고 떨려')
        self.assertNotEqual(r['status'], 'need_clarification')
        self.assertIn('사용자 답변: 소리는 없고 떨려', seen[0])

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
        sent = json.loads(routed[0])
        self.assertEqual((sent['question'], sent['history'][0]['content']), ('그럼 가혹조건은 뭐야?', '엔진오일 교환 기준 알려줘'))

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
            return 'search_law', {'query': '가상 교차로 일시정지', 'follow_up': True}
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
        self.assertEqual(retrieved, ['그럼 뭘 해야 해? 가상 교차로 일시정지'])  # the question's own words stay
        self.assertEqual(generated[0]['history'], history[-6:])
        self.assertEqual(generated[0]['question'], '그럼 뭘 해야 해?')

    def test_new_question_after_history_keeps_its_own_words_in_the_query(self):
        # The router shortened "우회전은 언제 할 수 있어?" to "우회전 시기", which missed 제25조.
        seen = []
        self.ask(picks('search_law', query='우회전 시기'), lambda s, u: '{}', lambda q, f: seen.append(q) or [],
                 question='우회전은 언제 할 수 있어?', history=[{'role': 'user', 'content': '오늘 점심은 뭐야?'}])
        self.assertTrue(seen[0].startswith('우회전은 언제 할 수 있어? 우회전 시기'))

    def test_new_question_is_answered_without_history_and_empty_replies_are_dropped(self):
        from unittest.mock import patch
        from chageun_ai.agent import MESSAGES
        history = [{'role': 'user', 'content': '비보호 좌회전 해도 돼?'},
                   {'role': 'assistant', 'content': MESSAGES['law_not_found'][0]}]
        routed = []
        choose = lambda system, question, tools: routed.append(json.loads(question)) or ('search_law', {'query': '우회전', 'follow_up': False})
        with patch('chageun_ai.agent.answer_from_hits', return_value={
            'status': 'answered', 'answer_text': '안내', 'speech_text': '안내', 'sources': []}) as answer:
            self.ask(choose, retrieve=lambda q, f: [{'chunk': {'metadata': {}}, 'score': 1}],
                     question='우회전은 언제 할 수 있어?', history=history)
        self.assertEqual(routed[0]['history'], history[:1])  # "근거를 찾지 못했어요" carries nothing
        self.assertIsNone(answer.call_args.kwargs['history'])

    def test_road_judgement_asks_the_situation_then_finds_the_rule(self):
        from unittest.mock import patch
        from chageun_ai.agent import MESSAGES, SITUATION_NOTE
        realtime = picks('decline', kind='realtime')
        r = self.ask(realtime, question='여기서 들어가도 돼?')
        self.assertEqual((r['status'], r['answer'], r['missing_fields']),
                         ('need_clarification', MESSAGES['ask_situation'][0], ['road_situation']))
        seen = []
        with patch('chageun_ai.agent.answer_from_hits', return_value={
            'status': 'answered', 'answer_text': '보행자를 방해하지 않으면 우회전할 수 있어요.',
            'speech_text': '우회전할 수 있어요.', 'sources': []}):
            # The frontend sends the answer with the question; the router still calls it a road judgement.
            frontend = self.ask(realtime, retrieve=lambda q, f: seen.append((q, f)) or [{'chunk': {'metadata': {}}, 'score': 1}],
                                question=f"여기서 들어가도 돼?\n확인 질문: {MESSAGES['ask_situation'][0]}\n사용자 답변: 빨간불이에요")
            voice = self.ask(realtime, retrieve=lambda q, f: seen.append((q, f)) or [{'chunk': {'metadata': {}}, 'score': 1}],
                             question='빨간불이에요', history=[{'role': 'user', 'content': '여기서 들어가도 돼?'},
                                                           {'role': 'assistant', 'content': MESSAGES['ask_situation'][0]}])
        for result in (frontend, voice):
            self.assertEqual(result['status'], 'answered')
            self.assertTrue(result['answer'].endswith(SITUATION_NOTE))
        self.assertEqual(seen[0][1], {'kind': 'law'})
        self.assertTrue(seen[1][0].startswith('여기서 들어가도 돼? 빨간불이에요'))

    def test_a_bare_light_asks_signal_or_dashboard_before_routing(self):
        from chageun_ai.agent import MESSAGES
        ask = MESSAGES['ask_light_kind'][0]
        for question in ('빨간불', '노란불 깜빡이면 어떻게 해?', '빨간불 깜빡여'):
            r = self.ask(lambda *a: self.fail('must not route'), question=question)
            self.assertEqual((r['status'], r['answer'], r['missing_fields']),
                             ('need_clarification', ask, ['light_kind']), question)
            self.assertEqual(r['suggestions'], ['신호등이에요', '계기판 불이에요'])
        routed = []
        choose = lambda s, q, t: routed.append(q) or ('decline', {'kind': 'unrelated'})
        # The place is already said, or our question was answered (frontend lines, or voice history)
        for question in ('빨간불에 직진해도 돼?', '계기판에 빨간 불이 켜졌어', '노란불일 때 교차로 진입해도 돼?',
                         f'빨간불\n확인 질문: {ask}\n사용자 답변: 계기판 불이에요'):
            self.assertNotEqual(self.ask(choose, question=question)['answer'], ask, question)
        self.ask(choose, question='신호등이에요', history=[{'role': 'user', 'content': '빨간불'},
                                                        {'role': 'assistant', 'content': ask}])
        self.assertNotIn(ask, routed[-2])
        self.assertEqual(routed[-1], '빨간불 신호등이에요')

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
