import test from 'node:test'
import assert from 'node:assert/strict'
import {
  maintenanceCatalog,
  maintenanceItems,
  maintenanceOverview,
  guidanceCategories,
} from '../src/guidance.js'
import {
  startQuestion,
  clarificationFor,
  continueQuestion,
  contextualOptions,
} from '../src/conversation.js'
import { buildRagRequest, resolveRagResponse, describeRecordAction } from '../src/ragConversation.js'
const car = {
  id: 3,
  manufacturer: '기아',
  model: 'K5',
  model_year: '2024',
  powertrain: '가솔린 1.6T',
  mileage_km: 36200,
}
const mock = {
  status: 'answered',
  answer: '목업 답변',
  conversation_id: 'c_mock',
}

test('history action speaks the latest matching server record for the selected car', () => {
  const result = { status: 'tool_result', action: { type: 'open_my_car', vehicle_id: 3, item: 'engine_oil' } }
  const records = [
    { item: 'engine_oil', performed_at: '2025-01-03', mileage_km: 12000 },
    { item: 'wiper', performed_at: '2026-08-04', mileage_km: 35000 },
    { item: 'engine_oil', performed_at: '2026-02-09', mileage_km: 27000 },
  ]
  const summary = describeRecordAction(result, { vehicle: car, records })
  assert.match(summary, /엔진오일/)
  assert.match(summary, /2026년 2월 9일/)
  assert.match(summary, /27,000킬로미터/)
  assert.doesNotMatch(summary, /와이퍼|2025년/)
  assert.equal(describeRecordAction(result, { vehicle: { ...car, id: 99 }, records }), '')
  assert.equal(describeRecordAction({ ...result, status: 'answered' }, { vehicle: car, records }), '')
})

test('spoken record lookup distinguishes unavailable records from an empty history', () => {
  const result = { status: 'tool_result', action: { type: 'open_my_car', vehicle_id: 3, item: 'engine_oil' } }
  assert.match(describeRecordAction(result, { vehicle: car }), /불러오지 못했어요/)
  assert.match(describeRecordAction(result, { vehicle: car, records: [] }), /정비 기록이 없어요/)
})
function complete(flow) {
  const asked = []
  for (let i = 0; i < 8; i++) {
    const prompt = clarificationFor(flow)
    if (!prompt) return { flow, asked }
    assert.ok(
      !asked.includes(prompt.field),
      `repeated question: ${prompt.field}`,
    )
    asked.push(prompt.field)
    flow = continueQuestion(
      { ...flow, awaiting: prompt.field },
      '잘 모르겠어요',
    )
  }
  assert.fail('clarification did not finish')
}
test('every planned maintenance item can reach RAG with its own record identifier and unknown answers', () => {
  const ids = [
    'engine_oil',
    'oil_filter',
    'air_filter',
    'cabin_filter',
    'tire',
    'brake_pad',
    'brake_fluid',
    'coolant',
    'battery',
    'wiper',
  ]
  assert.deepEqual(
    maintenanceCatalog.map((item) => item.recordId).sort(),
    ids.sort(),
  )
  for (const item of maintenanceCatalog) {
    assert.ok(maintenanceItems.some((option) => option.id === item.recordId))
    const { flow, asked } = complete({
      ...startQuestion(item.question, 3),
      category: 'maintenance',
      topicId: item.id,
      recordItem: item.recordId,
      intent: 'maintenance',
    })
    assert.ok(asked.length > 0)
    const body = buildRagRequest(flow, { vehicle: car, records: [] })
    assert.equal(body.context.maintenance_item, item.recordId)
    assert.equal(body.context.topic, item.id)
    assert.ok(body.question.includes(item.label))
    if (item.recordId !== 'engine_oil') {
      const result = resolveRagResponse(flow, mock, {
        vehicle: car,
        records: [],
      })
      assert.equal(
        result.facts,
        undefined,
        'do not invent an oil deadline for another item',
      )
      assert.equal(result.action.item, item.recordId)
    }
  }
})
test('oil, oil filter and cabin filter never reuse each other’s record or maintenance schedule', () => {
  const records = [
    { item: 'engine_oil', performed_at: '2026-01-01', mileage_km: 34000 },
    { item: 'air_filter', performed_at: '2025-01-01', mileage_km: 30000 },
  ]
  const rows = maintenanceOverview(records)
  assert.equal(rows.find((row) => row.id === 'oil-filter').record, null)
  assert.equal(rows.find((row) => row.id === 'cabin-filter').record, null)
  assert.equal(
    rows.find((row) => row.id === 'air-filter').record.item,
    'air_filter',
  )
  const flow = startQuestion('엔진오일 필터 교환 시기를 알려줘', 3)
  assert.equal(flow.recordItem, 'oil_filter')
  const result = resolveRagResponse(flow, mock, { vehicle: car, records })
  assert.equal(result.facts, undefined)
  assert.equal(result.action.item, 'oil_filter')
})
test('each controls and road-rule topic is reachable through its group and has a distinct question', () => {
  for (const category of guidanceCategories.filter((category) =>
    ['controls', 'rules'].includes(category.id),
  )) {
    assert.equal(
      new Set(category.topics.map((topic) => topic.question)).size,
      category.topics.length,
    )
    for (const item of category.topics) {
      assert.ok(category.groups.some((group) => group.id === item.group))
      const { flow } = complete({
        ...startQuestion(item.question, 3),
        intent: category.id,
        category: category.id,
        topicId: item.id,
      })
      assert.equal(
        buildRagRequest(flow, { vehicle: car, records: [] }).context.topic,
        item.id,
      )
    }
  }
})
test('unavailable records remain unavailable instead of becoming an empty known history', () => {
  const flow = startQuestion('엔진오일 언제 갈아?', 3)
  assert.equal(
    buildRagRequest(flow, { vehicle: car }).context.maintenance_status,
    'unavailable',
  )
  assert.equal(
    buildRagRequest(flow, { vehicle: car, records: [] }).context
      .maintenance_status,
    'available',
  )
})

test('short speech keeps the selected maintenance item while a new topic can leave it', () => {
  const selected = {
    ...maintenanceCatalog.find((item) => item.id === 'brake-fluid'),
    category: 'maintenance',
  }
  const options = contextualOptions('언제 갈아?', selected)
  assert.equal(options.recordItem, 'brake_fluid')
  assert.equal(options.intent, 'maintenance')
  const flow = { ...startQuestion('언제 갈아?', 3), ...options }
  const body = buildRagRequest(flow, { vehicle: car, records: [] })
  assert.equal(body.context.original_question, '언제 갈아?')
  assert.match(body.question, /선택한 항목: 브레이크액/)
  assert.deepEqual(contextualOptions('엉따 어떻게 켜?', selected), {})
  assert.deepEqual(contextualOptions('엔진오일 언제 갈아?', selected), {})
})

test('a car without reviewed intervals still opens the requested item, never the mock engine-oil record', () => {
  const item = maintenanceCatalog.find((item) => item.id === 'brake-fluid')
  const flow = {
    ...startQuestion(item.question, 4),
    category: 'maintenance',
    topicId: item.id,
    recordItem: item.recordId,
  }
  const raw = {
    ...mock,
    action: { type: 'open_my_car', vehicle_id: 3, item: 'engine_oil' },
  }
  const result = resolveRagResponse(flow, raw, {
    vehicle: { ...car, id: 4, model: '아반떼' },
    records: [],
  })
  assert.equal(result.action.item, 'brake_fluid')
  assert.equal(result.action.vehicle_id, 4)
  assert.equal(result.facts, undefined)
})
