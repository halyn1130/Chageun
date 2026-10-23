"""Question routing by tool calling, returning the /rag-query response contract.

Only the two document tools run here. Map and my-car tools come back as an `action`
for the frontend, which calls the api-server itself; the model never invents places.
"""
from __future__ import annotations
import uuid
from .core import answer_from_hits

MAINTENANCE_ITEMS = ['engine_oil', 'air_filter', 'tire', 'brake_pad', 'coolant', 'battery', 'wiper', 'other']
PLACE_CATEGORIES = ['parking', 'gas_station', 'cafe']
# Everyday words drivers say that the documents spell differently; added to the retrieval query only.
TERMS = {'오토홀드': '자동 정차 기능 AUTO HOLD', '깜빡': '점멸'}


def tool(name, description, **properties):
    return {'type': 'function', 'function': {
        'name': name, 'description': description,
        'parameters': {'type': 'object', 'properties': properties, 'required': list(properties),
                       'additionalProperties': False}}}


TOOLS = [
    tool('search_law', '도로교통법·시행령·시행규칙에서 교통 규칙, 통행 방법, 금지 행위, 범칙 기준을 찾는다.',
         query={'type': 'string', 'description': '질문을 법령 용어로 바꾼 검색어. 예: 주정차 → 정차 및 주차의 금지 장소'}),
    tool('search_manual', '선택한 차량의 취급설명서에서 기능 사용법, 경고등 의미, 점검·교환 주기와 방법을 찾는다.',
         query={'type': 'string', 'description': '질문의 상황과 목적을 모두 담은 검색어. 기능 이름은 설명서 표기를 함께 쓴다. '
                                  '예: 스마트키 배터리 방전 시 시동 거는 방법, 오토홀드 → 오토 홀드 AUTO HOLD'}),
    tool('find_places', '현재 위치나 경로 주변의 주차장·주유소·카페를 찾는다. "가는 길에 카페 들르면 얼마나 걸려?"처럼 '
         '들를 곳을 찾는 질문도 포함한다.',
         category={'type': 'string', 'enum': PLACE_CATEGORIES}),
    tool('show_route', '목적지까지 길 안내를 시작한다.',
         destination={'type': 'string', 'description': '목적지 이름 그대로'}),
    tool('open_maintenance', '내 차의 정비 기록에서 "마지막으로 언제 갈았지?"처럼 실제로 교환·점검한 시점을 확인한다. '
         '일반적인 교환 주기나 방법은 search_manual이다.',
         item={'type': 'string', 'enum': MAINTENANCE_ITEMS}),
    tool('decline', '답할 수 없는 질문. realtime: 지금 차선 변경·주차 가능 여부처럼 현재 도로 상황을 봐야 하는 판단. '
         'unrelated: 운전·차량·길 찾기와 무관한 질문.',
         kind={'type': 'string', 'enum': ['realtime', 'unrelated']}),
]

SYSTEM = ('너는 운전 도우미 차근의 질문 분류기다. 질문 하나에 도구 하나를 반드시 고른다. '
          '법규 질문은 search_law, 차량 기능·경고등·정비 기준은 search_manual, '
          '"내 차"의 마지막 정비나 교환 시점은 open_maintenance를 고른다. '
          '장소 검색·경로·소요 시간은 지도 도구가 처리하므로 decline하지 않는다. '
          '현재 도로 상황을 보고 판단해야 하는 질문과 운전과 무관한 질문만 decline을 고른다.')

MESSAGES = {
    'need_vehicle': ('어떤 차량 기준으로 알려드릴까요? 차량을 선택하거나 등록해 주세요.', '차량을 먼저 선택해 주세요.'),
    'need_location': ('주변을 찾으려면 현재 위치가 필요해요.', '위치 권한을 허용해 주세요.'),
    'out_of_scope': ('주행 중 실시간 판단은 도와드릴 수 없어요. 주변 상황을 직접 확인해 주세요.', '실시간 판단은 도와드릴 수 없어요.'),
    'unrelated': ('차근은 교통 규칙, 내 차, 길 찾기를 도와드려요. 그와 관련된 질문을 해 주세요.', '운전과 관련된 질문을 해 주세요.'),
    'show_places': ('주변 장소를 찾아볼게요.', '주변 장소를 찾아볼게요.'),
    'show_route': ('경로를 찾아볼게요.', '경로를 안내할게요.'),
    'open_my_car': ('정비 이력을 열어 드릴게요.', '정비 이력을 확인해 볼게요.'),
}


def respond(conversation_id, status, answer, speech, sources=(), action=None, needs_review=False, handoff=False):
    return {'status': status, 'answer': answer, 'speech_text': speech, 'sources': list(sources),
            'needs_review': needs_review, 'handoff': handoff, 'action': action,
            'conversation_id': conversation_id}


def cite(source):
    # Statutes cite the article; manuals cite the printed page when known, else the section path.
    printed = source.get('printed_page')
    page = source.get('article') or (printed and f'p.{printed}') or source.get('section') or f"PDF p.{source['pdf_page']}"
    if page.startswith('별표') and source.get('article_title'):
        page += f" ({source['article_title']})"
    return {'title': source['title'], 'page': page, 'url': source['source_url']}


def rag_query(request, choose, retrieve, generate, get_vehicle=lambda vehicle_id: None):
    """request: {question, vehicle_id?, conversation_id?, location?}

    choose(system, question, tools) -> (tool name, args) or None
    retrieve(query, filters) -> hits; generate(system, user) -> raw model text
    get_vehicle(vehicle_id) -> {manufacturer, model, model_year, powertrain} or None
    """
    question = (request.get('question') or '').strip()
    if not 2 <= len(question) <= 500:
        raise ValueError('question must be 2..500 characters')
    cid = request.get('conversation_id') or f'c_{uuid.uuid4().hex[:12]}'
    vehicle_id, location = request.get('vehicle_id'), request.get('location')
    reply = lambda status, *args, **kw: respond(cid, status, *(args or MESSAGES[status]), **kw)

    picked = choose(SYSTEM, question, TOOLS)
    name, args = picked if picked else (None, {})
    if name == 'decline':
        return reply('out_of_scope', *MESSAGES['unrelated' if args.get('kind') == 'unrelated' else 'out_of_scope'])
    if name == 'find_places' and args.get('category') in PLACE_CATEGORIES:
        if not location:
            return reply('need_location')
        return reply('tool_result', *MESSAGES['show_places'], action={'type': 'show_places', 'category': args['category']})
    if name == 'show_route' and args.get('destination'):
        return reply('tool_result', *MESSAGES['show_route'], action={'type': 'show_route', 'query': args['destination']})
    if name == 'open_maintenance' and args.get('item') in MAINTENANCE_ITEMS:
        if vehicle_id is None:
            return reply('need_vehicle')
        return reply('tool_result', *MESSAGES['open_my_car'],
                     action={'type': 'open_my_car', 'vehicle_id': vehicle_id, 'item': args['item']})
    if name not in ('search_law', 'search_manual'):
        return reply('not_found', '질문을 이해하지 못했어요. 조금 다르게 물어봐 주세요.', '다시 한 번 말씀해 주세요.')

    filters, car = {'kind': 'law'}, None
    if name == 'search_manual':
        vehicle = get_vehicle(vehicle_id) if vehicle_id is not None else None
        if not vehicle:
            return reply('need_vehicle')
        filters = {'kind': 'manual', **{k: vehicle[k] for k in ('manufacturer', 'model', 'model_year', 'powertrain')}}
        car = ' '.join(vehicle[k] for k in ('manufacturer', 'model', 'model_year', 'powertrain'))
    # The rewritten query only steers retrieval and never replaces the user's words, which a bad rewrite
    # could drop; the answer is checked against the original question.
    query = args.get('query', '').strip()
    query = f'{question} {query}' if query and query != question else question
    known = {word: term for word, term in TERMS.items() if word in question.replace(' ', '')}
    query += ''.join(f' {term}' for term in known.values())
    hits = retrieve(query, filters)
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
