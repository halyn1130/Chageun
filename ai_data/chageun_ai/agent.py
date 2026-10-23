"""Question routing by tool calling, returning the /rag-query response contract.

Chageun answers three things for beginner drivers: traffic law, the car's owner's manual and
the car's maintenance record. Navigation and place search are out of scope. Only the two
document tools run here; the maintenance tool comes back as an `action` for the frontend.
"""
from __future__ import annotations
import re
import uuid
from .core import answer_from_hits, load_warning_lights, read_json, WARNING_LIGHTS_PATH

MAINTENANCE_ITEMS = ['engine_oil', 'air_filter', 'tire', 'brake_pad', 'coolant', 'battery', 'wiper', 'other']
# Everyday words drivers say that the documents spell differently; added to the retrieval query only.
TERMS = {'오토홀드': '자동 정차 기능 AUTO HOLD', '깜빡': '점멸', '버스정류장': '버스여객자동차의 정류지', '교환': '교체',
         '소화전': '소방용수시설 비상소화장치', '멈춰': '일시정지', '멈추': '일시정지'}
# Signal colours as drivers say them; law only (a "빨간 불" on the dashboard is a warning light).
LAW_TERMS = {'빨간불': '적색의 등화', '적색신호': '적색의 등화', '빨간신호': '적색의 등화',
             '노란불': '황색의 등화', '황색신호': '황색의 등화', '노란신호': '황색의 등화',
             '초록불': '녹색의 등화', '녹색신호': '녹색의 등화', '파란불': '녹색의 등화'}
# Retrieval-only hints: a "what is the difference" question needs the definitions article.
QUERY_HINTS = {'차이': '정의 용어의 뜻', '달라': '정의 용어의 뜻',
               # Turning right is mostly about pedestrians (제27조), which the question rarely says.
               '우회전': '보행자의 보호 횡단보도 앞 일시정지'}
# Manual icons are images, so the text only has each light's name. Drivers describe the icon instead.
# Shapes were read off the K5 icon table; 아반떼 uses the same icons (icons compared side by side).
# The list lives in data/warning_lights.json together with every manual's spelling of each light.
LIGHTS = load_warning_lights()
WARNING_LIGHTS = {light['name']: tuple(light['shapes']) for light in LIGHTS if light['shapes']}
# Legal colours come from 자동차규칙 [별표 2]. A car may differ (manuals say colours follow the cluster theme),
# so a colour only narrows the candidates; the light itself is named only from its shape or name.
LEGAL_SOURCE = read_json(WARNING_LIGHTS_PATH)['legal_source']
COLORS = {'적색': re.compile(r'빨간|빨강|적색|붉은'), '황색': re.compile(r'노란|노랑|황색|주황|오렌지'),
          '녹색': re.compile(r'초록|녹색'), '청색': re.compile(r'파란|파랑|청색'), '백색': re.compile(r'흰|하얀|백색')}
COLOR_WORDS = {'적색': '빨간색', '황색': '노란색', '녹색': '초록색', '청색': '파란색', '백색': '흰색'}
UNKNOWN = re.compile(r'모르|몰라|잘\s?안\s?보|기억')
SHAPE_TALK = re.compile(r'모양|그림|처럼|생겼|생긴')
# A driver describing a problem wants what it means, why it matters and what to do now.
PROBLEM = re.compile(r'경고등|표시등|불[이도]?\s*(?:들어|켜|깜빡|떴|떠|나왔)|고장|이상해|소리가|냄새|연기|떨려|떨림|진동|'
                     r'방전|펑크|과열|시동이\s?안|안\s?걸려')
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
    # One question per turn, as people answer only what they are asked: the shape first, then the colour.
    'ask_shape': ('어떤 경고등인지 알 수 있게 어떤 모양인지 알려 주세요.', '어떤 모양인지 알려 주세요.'),
    'ask_color': ('어떤 색으로 켜져 있나요? 잘 모르겠으면 모르겠다고 해 주세요.', '어떤 색으로 켜져 있나요?'),
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


def color_in(text):
    return next((color for color, pattern in COLORS.items() if pattern.search(text)), None)


def clarified_turns(history):
    """The user's earlier words in a clarification exchange ("무슨 불이 켜졌어" → "주전자 모양이야"), oldest first."""
    asks = (MESSAGES['ask_shape'][0], MESSAGES['ask_color'][0])
    turns, i = [], len(history) - 1
    while (i >= 1 and len(turns) < 3 and history[i].get('role') == 'assistant'
           and history[i].get('content') in asks and history[i - 1].get('role') == 'user'):
        turns.insert(0, history[i - 1]['content'])
        i -= 2
    return turns


def color_mismatch(light, color):
    """A note when the colour the driver saw is not the light's legal colour: perhaps it is another light."""
    legal = next((l.get('legal') for l in LIGHTS if l['name'] == light), None)
    if not legal or not color or color in legal['colors']:
        return None
    colors = '이나 '.join(COLOR_WORDS[c] for c in legal['colors'])
    return (f'참고: {light}은 법에서 {colors}으로 정한 경고등이에요. 말씀하신 {COLOR_WORDS[color]}과 다르면 '
            f'다른 경고등일 수 있으니 모양을 한 번 더 확인해 주세요.')


MISSING = {'need_vehicle': ['vehicle']}
VEHICLE_KEYS = ('manufacturer', 'model', 'model_year', 'powertrain')


def respond(request_id, conversation_id, status, answer, speech, sources=(), action=None, needs_review=False,
            handoff=False):
    missing = MISSING.get(status, [])
    if status in ('ask_shape', 'ask_color'):  # both are the contract's need_clarification
        status, missing = 'need_clarification', ['warning_light' if status == 'ask_shape' else 'warning_light_color']
    return {'request_id': request_id, 'conversation_id': conversation_id, 'status': status, 'answer': answer,
            'speech_text': speech, 'sources': list(sources), 'needs_review': needs_review, 'handoff': handoff,
            'action': action, 'missing_fields': missing}


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
    history = request.get('history') or []
    # Replies to our own clarification ("주전자 모양이야") are read together with what they answer.
    # Earlier answers are never evidence; other history only helps the router read a follow-up.
    earlier = clarified_turns(history)
    question = ' '.join([*earlier, question]) if earlier else question
    previous = next((m['content'] for m in reversed(history) if m.get('role') == 'user'), None) if not earlier else None
    cid = request.get('conversation_id') or f'c_{uuid.uuid4().hex[:12]}'
    vehicle = request.get('vehicle')
    vehicle_id = (vehicle or {}).get('id')
    reply = lambda status, *args, **kw: respond(request.get('request_id'), cid, status,
                                                *(args or MESSAGES[status]), **kw)

    # Voice questions rarely name the car ("엔진오일 언제 갈아?"); telling the router one is selected keeps them in scope.
    car_note = ' '.join(str(vehicle.get(k, '')) for k in ('manufacturer', 'model')) if vehicle else ''
    routed = question + (f' [선택한 차량: {car_note}]' if car_note else '') + (f' [이전 질문: {previous}]' if previous else '')
    picked = choose(SYSTEM, routed, TOOLS)
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
    named, color = lights_in(question), color_in(question)
    by_shape = len(named) == 1 and named[0].replace(' ', '') not in question.replace(' ', '')
    if name == 'search_manual' and vague_warning(question):
        return reply('ask_shape')  # guessing one light from a colour would cite the wrong one
    # Only when the driver described the icon ("주전자 모양이야"); "타이어 공기압 경고등" already names it.
    described = bool(earlier) or bool(SHAPE_TALK.search(question))
    if name == 'search_manual' and by_shape and described and not color and not UNKNOWN.search(question):
        return reply('ask_color')  # some lights mean different things by colour (AUTO HOLD 흰색·녹색·황색)
    if name == 'search_manual':
        if not vehicle or not all(vehicle.get(k) for k in VEHICLE_KEYS):
            return reply('need_vehicle')
        filters = {'kind': 'manual', **{k: vehicle[k] for k in VEHICLE_KEYS}}
        car = ' '.join(vehicle[k] for k in VEHICLE_KEYS)
    # The rewritten query only steers retrieval and never replaces the user's words, which a bad rewrite
    # could drop; the answer is checked against the original question.
    query = args.get('query', '').strip()
    query = f'{question} {query}' if query and query != question else question
    glossary = {**TERMS, **(LAW_TERMS if name == 'search_law' else {})}
    known = {word: term for word, term in glossary.items() if word in question.replace(' ', '')}
    known.update({shape: light for light in lights_in(question) for shape in WARNING_LIGHTS[light]
                  if shape.upper() in question.replace(' ', '').upper()})
    query += ''.join(f' {term}' for term in known.values())
    query += ''.join(f' {hint}' for word, hint in QUERY_HINTS.items() if name == 'search_law' and word in question)
    if previous and re.match(r'(?:그럼|그러면|그건|그거|그때|그리고|또)\b', question):
        query += f' {previous}'  # "그럼 가혹조건은?" is about what was asked before
    hits = retrieve(query, filters)
    if not hits and name == 'search_manual':  # retrieval filters first, so no hits means no manual for this car
        return reply('not_found', f'{car} 설명서는 아직 등록되지 않았어요. 정비소나 고객센터에 문의해 주세요.',
                     '이 차량 설명서는 아직 없어요.', handoff=True)
    # Only our own curated glossary is added to the question, never the model's rewrite.
    if by_shape:
        # Identified from the icon or a clarification exchange: ask about the light itself, so the answer and its
        # check are not thrown by "무슨 불 … 주전자 모양이야", which no manual sentence says.
        seen = f'{COLOR_WORDS[color]}으로 ' if color else ''
        asked = f'{named[0]}이 {seen}켜졌어요. 무슨 뜻이고 어떻게 해야 하나요? (사용자 표현: {question})'
    else:
        asked = question + (f" (용어: {', '.join(f'{w} = {t}' for w, t in known.items())})" if known else '')
    asked += f' (이전 질문: {previous} — 지금 질문을 이해하는 데만 참고)' if previous else ''
    style = 'solution' if name == 'search_manual' and PROBLEM.search(question) else None
    result = answer_from_hits(asked, hits, generate, car, style)
    if result['status'] != 'answered':
        if name == 'search_manual':
            return reply('not_found', '설명서에서 근거를 찾지 못했어요. 정비소나 고객센터에 문의해 주세요.',
                         '설명서에서 찾지 못했어요.', handoff=True)
        return reply('not_found', '법령에서 근거를 찾지 못했어요. 공식 자료로 한 번 더 확인해 주세요.',
                     '법령에서 찾지 못했어요.', needs_review=True)
    # Parts of one long article share a citation, so show it once.
    sources = list({tuple(c.items()): c for c in map(cite, result['sources'])}.values())
    note = color_mismatch(named[0], color) if by_shape else None
    if note:
        sources.append({k: LEGAL_SOURCE[k] for k in ('title', 'page', 'url')})
    answer = result['answer_text'] + (f'\n{note}' if note else '')
    return reply('answered', answer, result['speech_text'], sources=sources)
