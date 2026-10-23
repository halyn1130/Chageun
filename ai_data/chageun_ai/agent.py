"""Question routing by tool calling, returning the /rag-query response contract.

Chageun answers three things for beginner drivers: traffic law, the car's owner's manual and
the car's maintenance record. Navigation and place search are out of scope. Only the two
document tools run here; the maintenance tool comes back as an `action` for the frontend.
"""
from __future__ import annotations
import re
import uuid
from .core import answer_from_hits

MAINTENANCE_ITEMS = ['engine_oil', 'air_filter', 'tire', 'brake_pad', 'coolant', 'battery', 'wiper', 'other']
# Everyday words drivers say that the documents spell differently; added to the retrieval query only.
TERMS = {'오토홀드': '자동 정차 기능 AUTO HOLD', '깜빡': '점멸'}
# Manual icons are images, so the text only has each light's name. Drivers describe the icon instead.
# Read off the K5 icon table (사용 설명서 요약본 9. 경고등 및 표시등); the team confirmed 아반떼 uses the same icons.
WARNING_LIGHTS = {
    '엔진 오일 압력 경고등': ('주전자', '오일캔', '오일경고등', '엔진오일경고등'),
    '충전 경고등': ('배터리', '충전경고등'),
    '엔진 경고등': ('엔진모양', '엔진경고등'),
    '브레이크 경고등': ('원안에느낌표', '동그라미안에느낌표', 'BRAKE', '브레이크경고등'),
    'ABS 경고등': ('ABS',),
    '에어백 경고등': ('에어백',),
    '안전벨트 미착용 경고등': ('안전벨트', '벨트'),
    '전동식 파워스티어링 경고등': ('핸들', '스티어링'),
    '저압 타이어 경고등': ('말굽', '타이어', 'TPMS'),
    '통합 경고등': ('삼각형',),
    '연료 부족 경고등': ('주유기', '연료', '기름'),
    '전자식 파킹 브레이크 (EPB) 경고등': ('EPB', '파킹브레이크'),
    '전방 안전 경고등': ('차두대', '충돌'),
    '도어 열림 경고등': ('도어', '문열림', '문이열'),
    '부주의 운전 경고등': ('커피', '찻잔'),
    'LED 전조등 고장 표시등': ('전구',),
    '차체자세제어장치(ESC) 작동 표시등': ('ESC', '미끄러지', '구불구불'),
}
WARNING_QUESTION = re.compile(r'경고등|표시등|경고\s?불|불[이도]?\s*(?:들어|켜|깜빡|떴|떠|나왔)')
# Words that say nothing about which light it is: colour, place, or a question word.
VAGUE = re.compile(r'(?:빨간|빨강|노란|노랑|주황|초록|녹색|파란|하얀|흰|적|황|청)색?|계기판|클러스터|무슨|어떤|이상한|웬|이|그|저|이런|저런')


def tool(name, description, **properties):
    return {'type': 'function', 'function': {
        'name': name, 'description': description,
        'parameters': {'type': 'object', 'properties': properties, 'required': list(properties),
                       'additionalProperties': False}}}


TOOLS = [
    tool('search_law', '도로교통법·시행령·시행규칙에서 교통 규칙, 통행 방법, 금지 행위, 범칙 기준을 찾는다.',
         query={'type': 'string', 'description': '질문을 법령 용어로 바꾼 검색어. 예: 주정차 → 정차 및 주차의 금지 장소'}),
    tool('search_manual', '선택한 차량의 취급설명서에서 기능 사용법, 계기판 경고등·표시등의 의미와 조치, 점검·교환 주기와 방법을 찾는다. '
         '"지금 계기판에 불이 들어왔어"처럼 경고등을 묻는 질문과 "이 차에 ○○ 기능 있어?"처럼 기능 유무를 묻는 질문도 여기다.',
         query={'type': 'string', 'description': '질문의 상황과 목적을 모두 담은 검색어. 기능 이름은 설명서 표기를 함께 쓴다. '
                                  '예: 스마트키 배터리 방전 시 시동 거는 방법, 오토홀드 → 오토 홀드 AUTO HOLD'}),
    tool('open_maintenance', '내 차의 정비 기록에서 "마지막으로 언제 갈았지?"처럼 실제로 교환·점검한 시점을 확인한다. '
         '일반적인 교환 주기나 방법은 search_manual이다.',
         item={'type': 'string', 'enum': MAINTENANCE_ITEMS}),
    tool('decline', '답할 수 없는 질문. realtime: 지금 차선 변경·주차 가능 여부처럼 현재 도로 상황을 봐야 하는 판단 '
         '(계기판 경고등은 해당하지 않는다). navigation: 길 안내, 경로, 소요 시간, 주변 주차장·주유소·카페 찾기. '
         'unrelated: 운전·차량과 무관한 질문.',
         kind={'type': 'string', 'enum': ['realtime', 'navigation', 'unrelated']}),
]

SYSTEM = ('너는 초보 운전자를 돕는 차근의 질문 분류기다. 질문 하나에 도구 하나를 반드시 고른다. '
          '법규 질문은 search_law, 차량 기능·계기판 경고등·정비 기준은 search_manual, '
          '"내 차"의 마지막 정비나 교환 시점은 open_maintenance를 고른다. '
          '길 안내와 주변 장소 찾기는 지원하지 않으므로 decline(navigation)을 고른다. '
          '현재 도로 상황을 보고 판단해야 하는 질문과 운전·차량과 무관한 질문도 decline을 고른다.')

MESSAGES = {
    'need_vehicle': ('어떤 차량 기준으로 알려드릴까요? 차량을 선택하거나 등록해 주세요.', '차량을 먼저 선택해 주세요.'),
    'need_clarification': ('어떤 경고등인지 모양을 알려 주세요. 예: 주전자 모양(엔진 오일 압력), 배터리 모양(충전), '
                           '엔진 모양(엔진 경고등), 원 안에 느낌표(브레이크), 삼각형 안에 느낌표(통합 경고등), '
                           '말굽 안에 느낌표(저압 타이어).', '어떤 모양의 경고등인지 알려 주세요.'),
    'out_of_scope': ('주행 중 실시간 판단은 도와드릴 수 없어요. 주변 상황을 직접 확인해 주세요.', '실시간 판단은 도와드릴 수 없어요.'),
    'navigation': ('차근은 길 안내와 주변 장소 찾기는 하지 않아요. 내비게이션 앱을 이용해 주세요.', '길 안내는 내비게이션 앱을 이용해 주세요.'),
    'unrelated': ('차근은 교통 법규, 내 차 설명서, 정비 기록을 도와드려요. 그와 관련된 질문을 해 주세요.', '운전과 관련된 질문을 해 주세요.'),
    'open_my_car': ('정비 이력을 열어 드릴게요.', '정비 이력을 확인해 볼게요.'),
}


def lights_in(question):
    """Warning light names the question identifies by name or icon shape."""
    if not WARNING_QUESTION.search(question):  # "타이어 교체" or "배터리 방전" is not about a lit icon
        return []
    flat = question.replace(' ', '')
    return [name for name, shapes in WARNING_LIGHTS.items()
            if name.replace(' ', '') in flat or any(shape.upper() in flat.upper() for shape in shapes)]


def vague_warning(question):
    # "빨간 불 들어왔어" names no light; "냉각수 경고등" does, even though it is not in the icon table.
    if not WARNING_QUESTION.search(question) or lights_in(question):
        return False
    words = re.findall(r'([가-힣A-Za-z0-9]+)\s*(?:경고등|표시등|경고\s?불|불)', question)
    return all(VAGUE.fullmatch(w) for w in words)


MISSING = {'need_vehicle': ['vehicle'], 'need_clarification': ['warning_light']}
VEHICLE_KEYS = ('manufacturer', 'model', 'model_year', 'powertrain')


def respond(request_id, conversation_id, status, answer, speech, sources=(), action=None, needs_review=False,
            handoff=False):
    return {'request_id': request_id, 'conversation_id': conversation_id, 'status': status, 'answer': answer,
            'speech_text': speech, 'sources': list(sources), 'needs_review': needs_review, 'handoff': handoff,
            'action': action, 'missing_fields': MISSING.get(status, [])}


def cite(source):
    # Statutes cite the article; manuals cite the printed page when known, else the section path.
    printed = source.get('printed_page')
    page = source.get('article') or (printed and f'p.{printed}') or source.get('section') or f"PDF p.{source['pdf_page']}"
    if page.startswith('별표') and source.get('article_title'):
        page += f" ({source['article_title']})"
    return {'title': source['title'], 'page': page, 'url': source['source_url']}


def rag_query(request, choose, retrieve, generate):
    """request: the api-server body {request_id, conversation_id, question, vehicle, maintenance, history,
    location, destination}; vehicle is already ownership-checked by the api-server. location and
    destination are accepted for compatibility but unused since navigation was dropped.

    choose(system, question, tools) -> (tool name, args) or None
    retrieve(query, filters) -> hits; generate(system, user) -> raw model text
    """
    question = (request.get('question') or '').strip()
    if not 2 <= len(question) <= 500:
        raise ValueError('question must be 2..500 characters')
    cid = request.get('conversation_id') or f'c_{uuid.uuid4().hex[:12]}'
    vehicle = request.get('vehicle')
    vehicle_id = (vehicle or {}).get('id')
    reply = lambda status, *args, **kw: respond(request.get('request_id'), cid, status,
                                                *(args or MESSAGES[status]), **kw)

    picked = choose(SYSTEM, question, TOOLS)
    name, args = picked if picked else (None, {})
    if name == 'decline' and WARNING_QUESTION.search(question):
        name, args = 'search_manual', {}  # a lit warning light is a manual question, not a road judgement
    if name == 'decline':
        kind = args.get('kind')
        return reply('out_of_scope', *MESSAGES[kind if kind in ('navigation', 'unrelated') else 'out_of_scope'])
    if name == 'open_maintenance' and args.get('item') in MAINTENANCE_ITEMS:
        if vehicle_id is None:
            return reply('need_vehicle')
        return reply('tool_result', *MESSAGES['open_my_car'],
                     action={'type': 'open_my_car', 'vehicle_id': vehicle_id, 'item': args['item']})
    if name not in ('search_law', 'search_manual'):
        return reply('not_found', '질문을 이해하지 못했어요. 조금 다르게 물어봐 주세요.', '다시 한 번 말씀해 주세요.')

    filters, car = {'kind': 'law'}, None
    if name == 'search_manual' and vague_warning(question):
        return reply('need_clarification')  # guessing one light would cite the wrong one
    if name == 'search_manual':
        if not vehicle or not all(vehicle.get(k) for k in VEHICLE_KEYS):
            return reply('need_vehicle')
        filters = {'kind': 'manual', **{k: vehicle[k] for k in VEHICLE_KEYS}}
        car = ' '.join(vehicle[k] for k in VEHICLE_KEYS)
    # The rewritten query only steers retrieval and never replaces the user's words, which a bad rewrite
    # could drop; the answer is checked against the original question.
    query = args.get('query', '').strip()
    query = f'{question} {query}' if query and query != question else question
    known = {word: term for word, term in TERMS.items() if word in question.replace(' ', '')}
    known.update({shape: light for light in lights_in(question) for shape in WARNING_LIGHTS[light]
                  if shape.upper() in question.replace(' ', '').upper()})
    query += ''.join(f' {term}' for term in known.values())
    hits = retrieve(query, filters)
    if not hits and name == 'search_manual':  # retrieval filters first, so no hits means no manual for this car
        return reply('not_found', f'{car} 설명서는 아직 등록되지 않았어요. 정비소나 고객센터에 문의해 주세요.',
                     '이 차량 설명서는 아직 없어요.', handoff=True)
    # Only our own curated glossary is added to the question, never the model's rewrite.
    asked = question + (f" (용어: {', '.join(f'{w} = {t}' for w, t in known.items())})" if known else '')
    result = answer_from_hits(asked, hits, generate, car)
    if result['status'] != 'answered':
        if name == 'search_manual':
            return reply('not_found', '설명서에서 근거를 찾지 못했어요. 정비소나 고객센터에 문의해 주세요.',
                         '설명서에서 찾지 못했어요.', handoff=True)
        return reply('not_found', '법령에서 근거를 찾지 못했어요. 공식 자료로 한 번 더 확인해 주세요.',
                     '법령에서 찾지 못했어요.', needs_review=True)
    # Parts of one long article share a citation, so show it once.
    sources = list({tuple(c.items()): c for c in map(cite, result['sources'])}.values())
    return reply('answered', result['answer_text'], result['speech_text'], sources=sources)
