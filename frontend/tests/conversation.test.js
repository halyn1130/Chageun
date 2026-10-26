import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildApiQuestion,
  clarificationFor,
  continueQuestion,
  isNewQuestion,
  findSpokenVehicle,
  localBoundary,
  normalizeResult,
  startQuestion,
} from '../src/conversation.js'

test('spoken vehicle choice resolves a unique registered car without guessing between duplicates', () => {
  const cars = [
    { id: 2, nickname: '붕붕이', model: 'K5', model_year: '2026' },
    { id: 3, nickname: '예전 차', model: 'K5', model_year: '2024' },
  ]
  assert.equal(findSpokenVehicle('붕붕이로 알려줘', cars).id, 2)
  assert.equal(findSpokenVehicle('2024년 K5', cars).id, 3)
  assert.equal(findSpokenVehicle('K5로 해 줘', cars), null)
  assert.equal(findSpokenVehicle('붕붕이 말고 다른 차', cars), null)
  assert.equal(findSpokenVehicle('없는 차', cars), null)
})

function reply(flow, text) {
  return continueQuestion(
    { ...flow, awaiting: clarificationFor(flow).field },
    text,
  )
}

test('rough warning description keeps the original question across several replies', () => {
  let flow = startQuestion('계기판에 이상한 불이 떴어', 3)
  assert.equal(clarificationFor(flow).field, 'color')
  flow = reply(flow, '노란색 엔진 모양이야')
  assert.equal(clarificationFor(flow).field, 'blink')
  flow = reply(flow, '계속 켜져 있어요')
  assert.equal(clarificationFor(flow), null)
  assert.equal(flow.vehicleId, 3)
  const question = buildApiQuestion(flow)
  assert.match(question, /^계기판에 이상한 불이 떴어/)
  assert.match(question, /색: 노란색/)
  assert.match(question, /모양: 엔진 모양/)
  assert.match(question, /점멸: 계속 켜져 있음/)
})

test('unknown answers finish the flow without asking the same question again', () => {
  let flow = startQuestion('경고등이 떴어')
  const fields = []
  for (let i = 0; i < 5 && clarificationFor(flow); i++) {
    fields.push(clarificationFor(flow).field)
    flow = reply(flow, '잘 모르겠어요')
  }
  assert.deepEqual(fields, ['vehicle', 'color', 'shape', 'blink'])
  assert.equal(clarificationFor(flow), null)
  assert.equal(flow.vehicleId, null)
  assert.match(buildApiQuestion(flow), /확인하지 못함/)
})

test('seat-heater slang leads to a seat question and keeps the chosen car', () => {
  let flow = startQuestion('엉따 어떻게 켜?', 4)
  assert.equal(flow.topic, '열선 시트')
  assert.equal(clarificationFor(flow).field, 'seat')
  flow = reply(flow, '조수석')
  assert.equal(clarificationFor(flow), null)
  assert.equal(flow.vehicleId, 4)
  assert.match(buildApiQuestion(flow), /좌석: 조수석/)
})

test('maintenance words are not collected as warning-light shapes', () => {
  const flow = startQuestion('내 차 엔진오일은 언제 교환해야 해?', 3)
  assert.equal(flow.intent, 'maintenance')
  assert.deepEqual(flow.details, {})
  assert.equal(buildApiQuestion(flow), flow.original)
})

test('hypothetical fuel range is not treated as a dashboard reading', () => {
  let flow = startQuestion('주유등 켜졌어. 50km는 갈 수 있어?', 3)
  assert.equal(clarificationFor(flow).field, 'range')
  flow = reply(flow, '35 km라고 표시돼')
  assert.equal(clarificationFor(flow), null)
  assert.match(buildApiQuestion(flow), /35 km로 표시됨 \(사용자 입력\)/)
})

test('a provided dashboard reading avoids asking for it again', () => {
  const flow = startQuestion('주유등이 켜졌고 계기판에는 35 km라고 나와', 3)
  assert.equal(clarificationFor(flow), null)
})

test('plain replies stay in the flow, while a new topic starts over', () => {
  const flow = startQuestion('경고등이 켜졌어', 3)
  assert.equal(isNewQuestion('노란색', flow), false)
  assert.equal(isNewQuestion('안 깜빡여', flow), false)
  assert.equal(isNewQuestion('엉따 어떻게 켜?', flow), true)
  assert.equal(isNewQuestion('엔진오일 언제 갈아?', flow), true)
})

test('a reply to the server question stays in the flow even when it looks like another topic', () => {
  const flow = { ...startQuestion('지금 우회전해도 괜찮아?', 3), awaiting: 'server', serverFollowup: true }
  assert.equal(isNewQuestion('지금 빨간불이고, 보행자는 파란불이야', flow), false)
  assert.equal(isNewQuestion('엔진오일 언제 갈아?', flow), true)
})

test('a traffic signal question is a road rule, while a dashboard light stays a warning', () => {
  assert.equal(startQuestion('빨간불에 직진해도 괜찮아?', 3).intent, 'rules')
  assert.equal(startQuestion('노란불일 때 교차로 진입해도 돼?', 3).intent, 'rules')
  assert.equal(startQuestion('빨간불에 유턴 돼?', 3).intent, 'rules')
  assert.equal(clarificationFor(startQuestion('빨간불에 직진해도 괜찮아?', 3)), null)
  assert.equal(startQuestion('빨간 불이 켜졌어', 3).intent, 'warning')
  assert.equal(startQuestion('계기판에 노란 불이 떴어', 3).intent, 'warning')
})

test('a bare light goes to the server, which asks whether it is a signal or the dashboard', () => {
  for (const text of ['빨간불', '노란불 깜빡이면 어떻게 해?', '빨간불 깜빡여']) {
    const flow = startQuestion(text, 3)
    assert.equal(flow.intent, 'general', text)
    assert.equal(clarificationFor(flow), null, text)
  }
  const flow = { ...startQuestion('빨간불', 3), awaiting: 'server', serverFollowup: true }
  assert.equal(isNewQuestion('신호등이에요', flow), false)
  assert.equal(isNewQuestion('계기판 불이에요', flow), false)
})

test('negated blinking is not classified as blinking', () => {
  const flow = startQuestion('노란색 엔진 경고등인데 깜빡이지 않아', 3)
  assert.equal(flow.details.blink, '계속 켜져 있음')
  assert.equal(clarificationFor(flow), null)
})

test('overlong combined question is rejected instead of silently losing details', () => {
  const flow = startQuestion('경고등' + '설명'.repeat(245), 3)
  flow.details.shape = '엔진 모양'
  flow.details.blink = '계속 켜져 있음'
  assert.throws(() => buildApiQuestion(flow), /500자/)
})

test('immediate driving decisions offer a relevant general follow-up', () => {
  assert.match(
    localBoundary('비보호라는데 지금 가면 돼?').suggestions[0],
    /비보호/,
  )
  assert.match(
    localBoundary('우회전인데 지금 가도 돼?').suggestions[0],
    /우회전/,
  )
  assert.match(localBoundary('여기 주차해도 돼?').suggestions[0], /주정차/)
  assert.match(
    localBoundary('주유등 켜졌는데 더 가도 돼?').suggestions[0],
    /주유등/,
  )
  assert.equal(localBoundary('비보호 좌회전의 법규상 조건을 알려줘'), null)
})

test('mock oil answers and wrong maintenance actions cannot become warning/control advice', () => {
  const warning = normalizeResult(startQuestion('노란색 엔진 경고등', 3), {
    status: 'answered',
    answer: '엔진오일 (목업 답변)',
    speech_text: '가짜 답변',
    sources: [{ url: 'https://example.com/manual' }],
  })
  assert.equal(warning.status, 'not_found')
  assert.equal(warning.speech_text, undefined)
  assert.deepEqual(warning.sources, [])
  const control = normalizeResult(startQuestion('내 차 엉따 어떻게 켜?', 3), {
    status: 'tool_result',
    answer: '정비 기록',
    action: { type: 'open_my_car', item: 'engine_oil' },
  })
  assert.equal(control.action, undefined)
  assert.match(control.answer, /열선 시트/)
})

test('skipping vehicle never opens the mock default car', () => {
  const flow = reply(
    startQuestion('내 차 엔진오일 언제 갈아?'),
    '차량 정보 없이 계속',
  )
  const result = normalizeResult(flow, {
    conversation_id: 'c_mock',
    status: 'tool_result',
    action: { type: 'open_my_car', vehicle_id: 3, item: 'engine_oil' },
  })
  assert.equal(result.action, undefined)
})

test('a future non-mock answer keeps its evidence and structured follow-up', () => {
  const result = {
    conversation_id: 'real-123',
    status: 'need_details',
    answer: '추가 확인이 필요해요.',
    followup_question: '어떤 옵션인가요?',
    suggestions: ['기본형', '확인 필요'],
    sources: [],
  }
  assert.equal(
    normalizeResult(startQuestion('엉따 어떻게 켜?', 3), result),
    result,
  )
})
