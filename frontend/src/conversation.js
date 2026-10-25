import { findGuideTopic, maintenanceCatalog } from './guidance.js'

// Local preview of the clarification contract. Identification and grounded advice
// must move to the server once verified vehicle manuals are connected.
export const UNKNOWN = '확인하지 못함'
const SKIP = /모르|확인.*못|잘 안|정보 없이|건너뛰/

export function classifyQuestion(text) {
  if (
    /비보호|우회전|좌회전|주정차|보호구역|교차로|차선|도로.*규칙|횡단보도|노면.*표시|황색선/.test(
      text,
    )
  )
    return 'rules'
  if (
    /주유\s*(등|경고)|기름.*(남|부족|없|떨어)|연료.*(남|부족|거리|경고)|주행\s*가능\s*거리/.test(
      text,
    )
  )
    return 'fuel'
  if (
    /경고등|계기판|온도계|(모양|빨간|노란|빨강|노랑).*(불|표시)|(불|표시).*(켜|켰|떴|뜨|들어)/.test(
      text,
    )
  )
    return 'warning'
  if (
    /정비|교환|교체|교체주기|엔진\s*오일.*(언제|갈|주기)|(타이어|브레이크|배터리|필터|냉각수|와이퍼).*(언제|갈|주기|점검)/.test(
      text,
    )
  )
    return 'maintenance'
  if (
    /열선|엉따|김.?서|뿌옇|크루즈|버튼|시트|히터|에어컨|와이퍼|비상등|오토홀드|전조등|상향등|사이드미러/.test(
      text,
    )
  )
    return 'controls'
  if (/시동.*(안|않|못|늦)|소리|진동|연기|냄새|바닥.*액체/.test(text))
    return 'symptom'
  return 'general'
}

export function questionTopic(text, intent = classifyQuestion(text)) {
  if (intent === 'fuel') return '연료 부족과 남은 거리'
  if (intent === 'warning') return '계기판 경고 표시'
  if (intent === 'maintenance') return '차량 정비'
  if (intent === 'rules') return '도로 규칙'
  if (/엉따|열선/.test(text)) return '열선 시트'
  if (/김.?서|뿌옇/.test(text)) return '김서림 제거'
  if (/크루즈/.test(text)) return '크루즈 컨트롤'
  return intent === 'controls' ? '차량 내부 조작' : '질문'
}

function detailsFrom(text, intent) {
  const details = {}
  const color = text.match(
    /빨간색?|빨강|붉은색?|노란색?|노랑|주황색?|초록색?|녹색|파란색?|파랑|흰색|하얀색?/,
  )
  if (color) details.color = color[0]
  const shape = text.match(
    /엔진|온도계|주전자|오일|느낌표|배터리|타이어|말발굽/,
  )
  if (shape) details.shape = `${shape[0]} 모양`
  if (/안\s*깜빡|깜빡이지\s*않|계속\s*(켜|들어)|깜빡임\s*없/.test(text))
    details.blink = '계속 켜져 있음'
  else if (/깜빡|점멸/.test(text)) details.blink = '깜빡임'
  if (/운전석/.test(text)) details.seat = '운전석'
  else if (/조수석/.test(text)) details.seat = '조수석'
  else if (/뒷좌석|뒷자리/.test(text)) details.seat = '뒷좌석'
  if (/아직 안|교환.*안|교환.*없/.test(text))
    details.recordStatus = '기록 이후 교환하지 않음'
  else if (/교환했|교환 했|교체했/.test(text))
    details.recordStatus = '기록 이후 교환함'
  if (/거의 없|해당 없/.test(text)) details.condition = '일반 조건'
  else if (/짧은 거리|정체/.test(text) && /잦|반복|자주/.test(text))
    details.condition = '짧은 거리·정체가 잦음'
  const range =
    text.match(
      /(?:계기판|잔여|남은|남았|표시)[^\n.]{0,20}?(\d+(?:\.\d+)?)\s*(?:km|킬로|키로)/i,
    ) ||
    text.match(
      /(\d+(?:\.\d+)?)\s*(?:km|킬로|키로)\s*(?:라고|로|가|남|떠|표시|나와)/i,
    )
  if (range) details.range = `${range[1]} km로 표시됨 (사용자 입력)`
  const relevant =
    {
      warning: ['color', 'shape', 'blink'],
      controls: ['seat'],
      fuel: ['range'],
      maintenance: ['recordStatus', 'condition'],
    }[intent] || []
  return Object.fromEntries(
    Object.entries(details).filter(([key]) => relevant.includes(key)),
  )
}

export function startQuestion(text, vehicleId = null) {
  const intent = classifyQuestion(text)
  const compact = text.replace(/\s/g, '')
  const matched =
    intent === 'maintenance'
      ? [...maintenanceCatalog]
          .sort((a, b) => b.label.length - a.label.length)
          .find(
            (item) =>
              compact.includes(item.label.replace(/\s/g, '')) ||
              (item.id === 'oil-filter' && /오일필터/.test(compact)) ||
              (item.id === 'air-filter' && /에어필터/.test(compact)),
          )
      : null
  return {
    ...(matched
      ? {
          category: 'maintenance',
          topicId: matched.id,
          recordItem: matched.recordId,
        }
      : {}),
    original: text,
    intent,
    topic: questionTopic(text, intent),
    details: detailsFrom(text, intent),
    vehicleId,
    vehicleResolved: vehicleId != null,
    awaiting: null,
  }
}

export function clarificationFor(flow) {
  const { intent, details } = flow
  // A live RAG follow-up is owned by the server; do not repeat local questions.
  if (flow.serverFollowup) return null
  if (
    ['controls', 'warning', 'fuel', 'maintenance', 'symptom'].includes(
      intent,
    ) &&
    !flow.vehicleResolved
  ) {
    return {
      field: 'vehicle',
      status: 'need_vehicle',
      answer: '차종과 연식에 따라 조작 방법과 기준이 달라요.',
      question: '어떤 차량인가요?',
      suggestions: ['차량 정보 없이 계속'],
    }
  }
  if (
    intent === 'controls' &&
    /엉따|열선.*시트/.test(flow.original) &&
    !details.seat
  ) {
    return {
      field: 'seat',
      answer: '',
      question: '어느 좌석의 열선을 켜고 싶으세요?',
      suggestions: ['운전석', '조수석', '뒷좌석', '잘 모르겠어요'],
    }
  }
  if (intent === 'fuel' && !details.range) {
    return {
      field: 'range',
      answer:
        '안전하게 확인할 수 있을 때 숫자를 알려 주세요. 예: 35 km. 주유등만으로 남은 거리를 정할 수는 없어요.',
      question: '계기판에 주행 가능 거리가 보이나요?',
      suggestions: ['숫자가 안 보여요', '아직 확인하지 못했어요'],
    }
  }
  if (
    intent === 'maintenance' &&
    (flow.recordItem === 'engine_oil' ||
      (!flow.recordItem && /엔진\s*오일(?!\s*필터)/.test(flow.original)))
  ) {
    if (flow.lastOil && !details.recordStatus)
      return {
        field: 'recordStatus',
        answer: `마지막 교환 기록은 ${flow.lastOil.performed_at.replaceAll('-', '.')} · ${new Intl.NumberFormat('ko-KR').format(flow.lastOil.mileage_km)} km예요.`,
        question: '이 기록 이후에도 교환한 적 있나요?',
        suggestions: ['아직 안 했어요', '교환했어요', '잘 모르겠어요'],
      }
    if (
      !details.condition &&
      (!details.recordStatus ||
        details.recordStatus === '기록 이후 교환하지 않음')
    )
      return {
        field: 'condition',
        answer: '운행 습관에 따라 교환 기준이 달라져요.',
        question: '짧은 거리나 정체가 잦나요?',
        suggestions: [
          '짧은 거리·정체가 잦아요',
          '거의 없어요',
          '잘 모르겠어요',
        ],
      }
  }
  const guide = findGuideTopic(flow.topicId, flow.category)
  if (
    intent === 'maintenance' &&
    guide?.recordId &&
    guide.recordId !== 'engine_oil'
  ) {
    if (flow.lastService && !details.recordStatus)
      return {
        field: 'recordStatus',
        answer: `마지막 ${guide.label} 기록은 ${flow.lastService.performed_at.replaceAll('-', '.')} · ${new Intl.NumberFormat('ko-KR').format(flow.lastService.mileage_km)} km예요.`,
        question: '이 기록 이후에도 교환한 적 있나요?',
        suggestions: ['아직 안 했어요', '교환했어요', '잘 모르겠어요'],
      }
    if (!flow.lastService && !details.serviceHistory)
      return {
        field: 'serviceHistory',
        answer: `${guide.label}의 교환 기록이 아직 없어요.`,
        question: '마지막으로 교환한 때를 알고 있나요?',
        suggestions: [
          '교환한 적 없어요',
          '교환했지만 날짜는 몰라요',
          '잘 모르겠어요',
        ],
      }
    if (!details.concern)
      return {
        field: 'concern',
        answer: '',
        question: guide.concern,
        suggestions: guide.choices,
      }
  }
  const prompts = {
    symptom: [
      'symptom',
      '언제 소리나 진동이 나나요?',
      ['시동을 걸 때', '브레이크를 밟을 때', '달리는 중에', '잘 모르겠어요'],
    ],
    starting: [
      'symptom',
      '시동을 걸면 어떤 반응이 있나요?',
      [
        '아무 반응이 없어요',
        '딸깍 소리만 나요',
        '엔진은 도는데 안 걸려요',
        '잘 모르겠어요',
      ],
    ],
    smell: [
      'symptom',
      '냄새나 연기가 어디서 나나요?',
      [
        '실내에서 나요',
        '엔진룸 쪽이에요',
        '바퀴 쪽이에요',
        '위치를 모르겠어요',
      ],
    ],
    leak: [
      'symptom',
      '액체가 어느 쪽에 보이나요?',
      ['차 앞쪽 아래', '차 가운데 아래', '바퀴 주변', '잘 모르겠어요'],
    ],
    defrost: [
      'window',
      '어느 유리에 김이 서렸나요?',
      ['앞유리', '뒷유리', '잘 모르겠어요'],
    ],
    ac: [
      'operation',
      '어떤 조작을 하고 싶으세요?',
      [
        '시원하게 하고 싶어요',
        '따뜻하게 하고 싶어요',
        '자동 온도 조절이 궁금해요',
      ],
    ],
    wipers: [
      'operation',
      '어떤 사용법이 궁금하세요?',
      ['와이퍼 속도 조절', '워셔액 뿌리기', '자동 와이퍼 모드'],
    ],
    lights: [
      'operation',
      '어떤 조명 기능인가요?',
      ['전조등 켜기', '상향등 전환', '자동 모드'],
    ],
    mirrors: [
      'operation',
      '사이드미러를 어떻게 하고 싶으세요?',
      ['각도 조절하기', '접거나 펼치기'],
    ],
    cruise: [
      'operation',
      '크루즈의 어떤 부분이 궁금하세요?',
      ['사용 조건', '켜고 속도 설정하기', '해제하는 방법'],
    ],
    autohold: [
      'operation',
      '오토홀드의 어떤 부분인가요?',
      ['켜고 끄는 방법', '작동하는 조건'],
    ],
    'parking-brake': [
      'operation',
      '어떤 조작이 궁금하세요?',
      ['주차 브레이크 걸기', '주차 브레이크 해제'],
    ],
    ventilation: [
      'seat',
      '어느 좌석인가요?',
      ['운전석', '조수석', '잘 모르겠어요'],
    ],
    'right-turn': [
      'scenario',
      '어떤 상황의 우회전 규칙인가요?',
      [
        '차량 신호가 빨간 상황',
        '차량 신호가 초록인 상황',
        '우회전 신호등이 있는 곳',
        '전반적인 조건',
      ],
    ],
    unprotected: [
      'scenario',
      '어떤 점이 헷갈리세요?',
      ['신호 색과 진행 조건', '맞은편 차량과 우선순위', '보행자가 있는 경우'],
    ],
    lane: [
      'scenario',
      '어떤 차선의 규칙인가요?',
      ['흰색 실선', '흰색 점선', '황색선', '표시를 모르겠어요'],
    ],
    parking: [
      'scenario',
      '어떤 장소의 기준이 궁금하세요?',
      ['교차로 주변', '소화전 주변', '버스 정류장 주변', '일반적인 금지 구역'],
    ],
    crosswalk: [
      'scenario',
      '어떤 상황을 알아볼까요?',
      [
        '보행자가 건너는 경우',
        '건너려는 사람이 있는 경우',
        '신호등이 없는 횡단보도',
      ],
    ],
  }
  const next = prompts[flow.topicId]
  if (next && !details[next[0]])
    return {
      field: next[0],
      answer: '',
      question: next[1],
      suggestions: next[2],
    }
  if (intent === 'warning') {
    if (!details.color)
      return {
        field: 'color',
        answer: '',
        question: '불빛이 어떤 색인가요?',
        suggestions: ['빨간색', '노란색', '다른 색이에요', '잘 모르겠어요'],
      }
    if (!details.shape)
      return {
        field: 'shape',
        answer: '',
        question: '어떤 모양처럼 보이나요?',
        suggestions: /빨|붉/.test(details.color)
          ? ['주전자 모양', '배터리 모양', '느낌표 모양', '잘 모르겠어요']
          : ['엔진 모양', '말발굽 모양', 'ABS 글자', '잘 모르겠어요'],
      }
    if (!details.blink)
      return {
        field: 'blink',
        answer: '',
        question: '계속 켜져 있나요, 깜빡이나요?',
        suggestions: ['계속 켜져 있어요', '깜빡여요', '잘 모르겠어요'],
      }
  }
  return null
}

export function continueQuestion(flow, text) {
  const extracted = detailsFrom(text, flow.intent)
  const next = {
    ...flow,
    details: { ...flow.details, ...extracted },
    awaiting: null,
  }
  if (flow.awaiting === 'vehicle') {
    next.vehicleResolved = true
    next.vehicleNote = text
  } else if (flow.awaiting === 'server') {
    next.followups = [
      ...(flow.followups || []),
      { question: flow.serverQuestion, answer: text },
    ]
  } else if (flow.awaiting) {
    // Unknown is an explicit answer, so a user can always finish the flow.
    next.details[flow.awaiting] =
      SKIP.test(text) || /숫자가 안/.test(text)
        ? UNKNOWN
        : extracted[flow.awaiting] || text
  }
  return next
}

// Only pick a registered car when the spoken name identifies exactly one.
export function findSpokenVehicle(text, vehicles) {
  const flat = value => String(value || '').toLowerCase().replace(/[\s\p{P}]/gu, '')
  const reply = flat(text)
  if (/아니|말고/.test(reply)) return null
  const named = vehicles.filter(car => flat(car.nickname).length >= 2 && reply.includes(flat(car.nickname)))
  if (named.length) return named.length === 1 ? named[0] : null
  const year = text.match(/20\d{2}/)?.[0]
  const models = vehicles.filter(car => flat(car.model).length >= 2 && reply.includes(flat(car.model)) && (!year || String(car.model_year) === year))
  return models.length === 1 ? models[0] : null
}

export function isNewQuestion(text, flow) {
  const intent = classifyQuestion(text)
  if (intent !== 'general' && intent !== flow.intent) return true
  return /어떻게|언제|알려\s*줘|방법|[?？]/.test(text) && intent !== 'general'
}

const DETAIL_LABELS = {
  seat: '좌석',
  color: '색',
  shape: '모양',
  blink: '점멸',
  range: '계기판 잔여 거리',
  recordStatus: '추가 교환 여부',
  condition: '운행 습관',
  symptom: '증상 발생 시점',
  window: '김서림 위치',
  serviceHistory: '이전 교환 정보',
  concern: '현재 상태',
  operation: '원하는 조작',
  scenario: '확인할 상황',
}
export function questionDetails(flow) {
  return Object.entries(flow.details)
    .filter(([key]) => DETAIL_LABELS[key])
    .map(([key, value]) => `${DETAIL_LABELS[key]}: ${value}`)
}

export function buildApiQuestion(flow) {
  const details = questionDetails(flow)
  if (flow.vehicleNote) details.unshift(`차량: ${flow.vehicleNote}`)
  if (flow.contextLabel) details.unshift(`선택한 항목: ${flow.contextLabel}`)
  const text = [
    flow.original,
    details.length ? `추가 정보 — ${details.join('; ')}` : '',
    ...(flow.followups || []).map(({ question, answer }) => `확인 질문: ${question}\n사용자 답변: ${answer}`),
  ]
    .filter(Boolean)
    .join('\n')
  if (text.length > 500)
    throw new Error(
      '질문과 추가 설명을 합쳐 500자를 넘었어요. 새 질문으로 조금 짧게 적어 주세요.',
    )
  return text
}

export function localBoundary(text) {
  const immediate =
    /(?:지금|바로|여기|현재).*(?:가도|가면|가\s*[?？]|들어가도|진입해도|출발해도|바꿔도|바꾸면|세워도|주차해도|지나가도)/.test(
      text,
    ) || /(?:계속|더)\s*(?:가도|달려도|운전해도)/.test(text)
  if (immediate) {
    const intent = classifyQuestion(text)
    const suggestion =
      intent === 'fuel'
        ? '주유등이 켜졌어. 계기판에서 무엇을 확인해?'
        : intent === 'warning'
          ? '경고등이 켜졌어. 어떤 정보를 확인해야 해?'
          : /주차|주정차|세워/.test(text)
            ? '주정차 여부를 판단할 때 어떤 표지와 조건을 봐야 해?'
            : /차선/.test(text)
              ? '차선 변경에 관한 일반적인 도로 규칙을 알려줘'
              : /우회전/.test(text)
                ? '우회전할 때의 법규상 조건을 알려줘'
                : /비보호|좌회전/.test(text)
                  ? '비보호 좌회전의 법규상 조건을 알려줘'
                  : null
    return {
      status: 'out_of_scope',
      title: '지금 상황은 직접 확인해 주세요.',
      answer:
        '현재 차량 상태나 주변 교통 상황을 볼 수 없어 지금 진행해도 되는지는 판단할 수 없어요. 안전하게 상황을 확인해 주세요. 대신 설명서에서 확인할 내용이나 일반적인 도로 규칙을 함께 살펴볼 수 있어요.',
      suggestions: suggestion ? [suggestion] : [],
    }
  }
  if (
    /(카페.*(들르|경유)|목적지|길\s*안내|경로|얼마나 걸려|(?:주차장|주유소).*찾아|(?:공업소|공업사|정비소|카센터).*(?:찾|어디|가까|추천)|(?:가까운|주변).*(?:공업소|공업사|정비소|카센터))/.test(
      text,
    )
  ) {
    return {
      status: 'out_of_scope',
      title: '차량 사용에 관한 질문을 도와드려요.',
      answer:
        '차근에서는 차 안 조작, 경고등, 소모품 관리와 도로 규칙을 도와드려요. 장소 검색은 지원하지 않아요.',
      suggestions: ['엔진오일 교환 시기를 확인하고 싶어'],
    }
  }
  return null
}

export function isMockResult(result) {
  const placeholder = /목업 답변/.test(result.answer || '')
  return Boolean(
    result.conversation_id === 'c_mock' ||
    placeholder ||
    result.sources?.some((source) => /example\.com/.test(source.url || '')),
  )
}

export function normalizeResult(flow, result) {
  const mock = isMockResult(result)
  if (!mock && result.status === 'need_clarification') {
    return {
      ...result,
      status: 'need_details',
      answer: result.followup_question ? result.answer : '',
      followup_question: result.followup_question || result.answer,
    }
  }
  const wrongCarAction =
    result.action?.type === 'open_my_car' &&
    !(
      flow.intent === 'maintenance' &&
      flow.vehicleId != null &&
      result.action.vehicle_id === flow.vehicleId
    )
  if (!mock && !wrongCarAction) return result
  const unavailable = (answer) => ({
    status: 'not_found',
    answer,
    sources: [],
    demo: true,
  })
  if (flow.intent === 'controls')
    return unavailable(
      `${flow.topic}에 관한 질문과 차량 정보를 정리했어요. 차량별 설명서는 아직 준비 중이라 버튼 위치와 조작 순서를 확인할 수 없어요. 차종·연식·옵션에 맞는 자료가 연결되면 출처와 함께 안내할게요.`,
    )
  if (flow.intent === 'fuel')
    return unavailable(
      '알려 주신 연료 정보를 확인했어요. 계기판에 표시된 숫자는 입력한 정보로만 보관하며, 더 달려도 된다는 뜻으로 안내하지 않아요. 현재 차량의 설명서가 연결되지 않아 확인 방법과 남은 주행 거리를 안내할 수 없어요.',
    )
  if (flow.intent === 'warning')
    return unavailable(
      '말씀해 주신 색·모양·점멸 상태를 정리했어요. 차량별 설명서가 아직 연결되지 않아 어떤 경고인지 확정할 수 없어요. 안전한 장소에서 해당 차량의 설명서를 확인하거나 정비 전문가에게 문의해 주세요.',
    )
  if (
    flow.intent === 'maintenance' &&
    result.action?.type === 'open_my_car' &&
    flow.vehicleId != null
  ) {
    return {
      ...unavailable(
        '교환 시점을 계산할 설명서 기준은 준비 중이에요. 먼저 선택한 차량의 정비 기록을 확인해 보세요.',
      ),
      action: { ...result.action, vehicle_id: flow.vehicleId },
    }
  }
  return unavailable(
    '관련 공식 자료가 아직 준비 중이라 정확한 기준을 안내할 수 없어요. 자료가 연결되면 근거와 출처를 함께 보여드릴게요.',
  )
}

// Short speech such as “언제 갈아?” keeps the selected item. An explicitly
// different topic can still replace it instead of being trapped in a menu.
export function contextualOptions(text, selected) {
  if (!selected?.id) return {}
  const inferred = startQuestion(text)
  const intent = selected.intent || selected.category
  if (inferred.intent !== 'general' && inferred.intent !== intent) return {}
  if (inferred.topicId && inferred.topicId !== selected.id) return {}
  return {
    category: selected.category,
    topicId: selected.id,
    recordItem: selected.recordId,
    contextLabel: selected.label,
    intent,
  }
}
