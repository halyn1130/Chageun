import test from 'node:test'
import assert from 'node:assert/strict'
import { personalRecommendation } from '../src/guidance.js'
import { buildRagRequest, resolveRagResponse } from '../src/ragConversation.js'
import {
  startQuestion,
  clarificationFor,
  continueQuestion,
} from '../src/conversation.js'

const vehicle = {
  id: 3,
  manufacturer: '기아',
  model: 'K5',
  model_year: '2024',
  powertrain: '가솔린 1.6T',
  mileage_km: 36200,
}
const records = [
  { item: 'engine_oil', performed_at: '2024-01-10', mileage_km: 35000 },
  { item: 'engine_oil', performed_at: '2023-01-10', mileage_km: 25000 },
  { item: 'tire', performed_at: '2023-07-10', mileage_km: 30000 },
]
const rawMock = {
  status: 'answered',
  conversation_id: 'c_mock',
  answer: '목업 답변',
}
function answer(flow, text) {
  return continueQuestion(
    { ...flow, awaiting: clarificationFor(flow).field },
    text,
  )
}
function oilFlow() {
  return {
    ...startQuestion('내 차 엔진오일 언제 갈아?', 3),
    category: 'maintenance',
    topicId: 'oil',
    lastOil: records[0],
  }
}

test('recommendation changes with the latest record and never assigns K5 deadlines to other cars', () => {
  assert.match(
    personalRecommendation(vehicle, records, { now: '2026-10-23' }).title,
    /교환 기록/,
  )
  assert.match(
    personalRecommendation(
      vehicle,
      [{ item: 'engine_oil', performed_at: '2026-10-20', mileage_km: 36000 }],
      { now: '2026-10-23' },
    ).title,
    /다음/,
  )
  const other = personalRecommendation(
    { ...vehicle, model: '아반떼', manufacturer: '현대' },
    records,
  )
  assert.equal(other.topic, undefined)
  assert.match(other.title, /아반떼 정비 기록/)
  assert.equal(personalRecommendation(null, []).category, null)
})

test('oil guidance confirms whether the stored record is current before asking driving habits', () => {
  let flow = oilFlow()
  assert.equal(clarificationFor(flow).field, 'recordStatus')
  flow = answer(flow, '아직 안 했어요')
  assert.equal(clarificationFor(flow).field, 'condition')
  flow = answer(flow, '짧은 거리·정체가 잦아요')
  assert.equal(clarificationFor(flow), null)
  const result = resolveRagResponse(flow, rawMock, {
    vehicle,
    records,
    now: '2026-10-23',
  })
  assert.equal(result.facts[0].value, '40,000 km')
  assert.equal(result.facts[1].value, '2024.07.10')
  assert.equal(result.demo, true)
})

test('a newer unrecorded oil change or unknown conditions cannot produce a stale due date', () => {
  const changed = answer(oilFlow(), '교환했어요')
  assert.equal(clarificationFor(changed), null)
  assert.equal(
    resolveRagResponse(changed, rawMock, { vehicle, records }).facts,
    undefined,
  )
  let unknown = answer(oilFlow(), '아직 안 했어요')
  unknown = answer(unknown, '잘 모르겠어요')
  assert.equal(clarificationFor(unknown), null)
  assert.equal(
    resolveRagResponse(unknown, rawMock, { vehicle, records }).facts,
    undefined,
  )
})

test('RAG payload preserves original intent, user confirmations, exact vehicle and latest records', () => {
  let flow = answer(oilFlow(), '아직 안 했어요')
  flow = answer(flow, '거의 없어요')
  const request = buildRagRequest(flow, {
    vehicle,
    records,
    conversationId: 'real-123',
  })
  assert.equal(request.vehicle_id, 3)
  assert.equal(request.conversation_id, 'real-123')
  assert.match(request.question, /^내 차 엔진오일 언제 갈아\?/)
  assert.equal(request.context.vehicle.powertrain, '가솔린 1.6T')
  assert.equal(request.context.collected_answers.condition, '일반 조건')
  assert.equal(request.context.maintenance_records.length, 2)
  assert.equal(
    request.context.maintenance_records[0].performed_at,
    '2024-01-10',
  )
  assert.equal(request.context.entry_point, 'maintenance')
})

test('real RAG evidence takes precedence over the local demo answer', () => {
  const result = {
    conversation_id: 'real-42',
    status: 'answered',
    answer: '문서 검색 결과',
    sources: [{ title: '공식 문서', url: 'https://ownersmanual.kia.com/' }],
  }
  assert.equal(
    resolveRagResponse(oilFlow(), result, { vehicle, records }),
    result,
  )
  const missing = {
    conversation_id: 'real-43',
    status: 'not_found',
    answer: '근거 없음',
  }
  assert.equal(
    resolveRagResponse(oilFlow(), missing, { vehicle, records }),
    missing,
  )
})

test('real RAG opens each selected consumable history without replacing the server answer', () => {
  for (const item of ['oil_filter', 'cabin_filter', 'brake_fluid', 'wiper']) {
    const flow = { ...startQuestion('마지막으로 언제 갈았어?', 3), intent: 'maintenance', recordItem: item }
    const result = {
      conversation_id: 'real-history',
      status: 'tool_result',
      answer: '정비 이력을 열어 드릴게요.',
      action: { type: 'open_my_car', vehicle_id: 3, item },
    }
    assert.equal(resolveRagResponse(flow, result, { vehicle, records }), result)
    assert.equal(resolveRagResponse({ ...flow, vehicleId: null }, result).action, undefined)
  }
})

test('server follow-up retains its original question and accumulated answers without local re-questioning', () => {
  const flow = {
    ...oilFlow(),
    serverFollowup: true,
    awaiting: 'server',
    serverQuestion: '최근에도 교환했나요?',
  }
  const next = continueQuestion(flow, '어제 교환했어요')
  assert.equal(clarificationFor(next), null)
  const request = buildRagRequest(next, { vehicle, records })
  assert.equal(request.context.original_question, flow.original)
  assert.deepEqual(request.context.followups, [
    { question: '최근에도 교환했나요?', answer: '어제 교환했어요' },
  ])
})

test('unavailable records and unsupported vehicles never inherit a made-up maintenance date', () => {
  let flow = answer(oilFlow(), '아직 안 했어요')
  flow = answer(flow, '거의 없어요')
  assert.equal(resolveRagResponse(flow, rawMock, { vehicle }).facts, undefined)
  assert.equal(
    resolveRagResponse(flow, rawMock, {
      vehicle: { ...vehicle, model_year: '2025' },
      records,
    }).facts,
    undefined,
  )
})
