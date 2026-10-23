import test from 'node:test'
import assert from 'node:assert/strict'
import { createRenderer, h, nextTick } from 'vue'
import { contextualOptions } from '../src/conversation.js'
import { maintenanceCatalog } from '../src/guidance.js'
import { useChageun } from '../src/composables/useChageun.js'

// Exercise the actual composable, including HTTP calls, rather than only the
// request builder. The host has no browser microphone or user-facing effects.
test('guided oil and warning flows call RAG; real server follow-ups retain context', async () => {
  const vehicle = {
    id: 3,
    is_primary: true,
    manufacturer: '기아',
    model: 'K5',
    model_year: '2024',
    powertrain: '가솔린 1.6T',
    mileage_km: 36200,
  }
  const records = [
    { item: 'engine_oil', performed_at: '2024-01-10', mileage_km: 35000 },
  ]
  const requests = []
  let response = {
    status: 'answered',
    conversation_id: 'c_mock',
    answer: '목업 답변',
  }
  const old = Object.fromEntries(
    ['window', 'localStorage', 'fetch'].map((key) => [
      key,
      Object.getOwnPropertyDescriptor(globalThis, key),
    ]),
  )
  globalThis.localStorage = {
    getItem: () => null,
    setItem() {},
    removeItem() {},
  }
  globalThis.window = {
    location: { origin: 'http://localhost' },
    addEventListener() {},
    removeEventListener() {},
  }
  globalThis.fetch = async (url, options) => {
    const path = new URL(url, 'http://localhost').pathname
    let data = null
    if (path === '/api/vehicles') data = [vehicle]
    if (path === '/api/vehicles/catalog') data = [vehicle]
    if (path.endsWith('/maintenance')) data = records
    if (path === '/api/health') data = { status: 'ok' }
    if (path === '/api/rag-query') {
      requests.push(JSON.parse(options.body))
      data = typeof response === 'function' ? await response(options.signal) : response
    }
    return new Response(JSON.stringify(data), {
      headers: { 'Content-Type': 'application/json' },
    })
  }
  const renderer = createRenderer({
    createElement: () => ({}),
    createText: () => ({}),
    createComment: () => ({}),
    setText() {},
    setElementText() {},
    patchProp() {},
    insert() {},
    remove() {},
    parentNode: () => null,
    nextSibling: () => null,
  })
  let state
  const app = renderer.createApp({
    setup() {
      state = useChageun()
      return () => h('div')
    },
  })
  try {
    app.mount({})
    await new Promise((resolve) => setImmediate(resolve))
    await nextTick()
    assert.equal(state.chatVehicleId.value, 3)
    state.go('diagnostics')
    await state.ask('내 차 엔진오일 언제 갈아?', {
      newQuestion: true,
      category: 'maintenance',
      topicId: 'oil',
    })
    assert.equal(state.pendingQuestion.value.awaiting, 'recordStatus')
    await state.replyTo(state.currentMessage.value, '아직 안 했어요')
    await state.replyTo(state.currentMessage.value, '짧은 거리·정체가 잦아요')
    assert.equal(state.screen.value, 'diagnostics')
    assert.equal(requests.length, 1, 'oil guidance must not bypass RAG')
    assert.equal(requests[0].context.maintenance_records[0].mileage_km, 35000)
    assert.equal(
      requests[0].context.collected_answers.condition,
      '짧은 거리·정체가 잦음',
    )
    assert.equal(state.currentMessage.value.facts[0].value, '40,000 km')

    await state.ask('빨간 주전자 모양 경고등이 계속 켜져 있어', {
      newQuestion: true,
      category: 'warning',
    })
    assert.equal(requests.length, 2, 'warning guidance must not bypass RAG')
    assert.equal(state.currentMessage.value.warningId, 'oil')

    response = {
      status: 'need_clarification',
      conversation_id: 'real-1',
      suggestions: ['기본형'],
      answer: '어떤 옵션인가요?',
    }
    await state.ask('운전석 엉따 어떻게 켜?', {
      newQuestion: true,
      category: 'controls',
      topicId: 'seat',
    })
    assert.equal(state.currentMessage.value.serverFlow, true)
    assert.equal(state.currentMessage.value.followup_question, '어떤 옵션인가요?')
    response = {
      status: 'answered',
      conversation_id: 'real-1',
      answer: '서버의 문서 검색 결과',
      sources: [{ title: '공식 설명서', url: 'https://ownersmanual.kia.com/' }],
    }
    await state.replyTo(state.currentMessage.value, '기본형')
    assert.equal(requests.at(-1).conversation_id, 'real-1')
    assert.equal(requests.at(-1).context.followups[0].answer, '기본형')
    assert.match(requests.at(-1).question, /사용자 답변: 기본형/)
    assert.equal(
      requests.at(-1).context.original_question,
      '운전석 엉따 어떻게 켜?',
    )
    assert.equal(state.currentMessage.value.answer, '서버의 문서 검색 결과')

    response = {
      status: 'answered',
      conversation_id: 'c_mock',
      answer: '목업 답변',
    }
    const selected = {
      ...maintenanceCatalog.find((item) => item.id === 'brake-fluid'),
      category: 'maintenance',
    }
    await state.ask('언제 갈아?', {
      newQuestion: true,
      ...contextualOptions('언제 갈아?', selected),
    })
    assert.equal(state.pendingQuestion.value.awaiting, 'serviceHistory')
    await state.replyTo(state.currentMessage.value, '교환한 적 없어요')
    assert.equal(state.pendingQuestion.value.awaiting, 'concern')
    await state.replyTo(state.currentMessage.value, '경고등이 켜졌어요')
    assert.equal(state.pendingQuestion.value, null)
    assert.equal(requests.at(-1).context.maintenance_item, 'brake_fluid')
    assert.equal(
      requests.at(-1).context.collected_answers.concern,
      '경고등이 켜졌어요',
    )
    assert.match(requests.at(-1).question, /선택한 항목: 브레이크액/)
    assert.equal(state.currentMessage.value.action.item, 'brake_fluid')

    // Home ends this conversation; another question on the same screen keeps
    // its conversation ID until that explicit navigation action.
    state.returnHome()
    response = { status: 'answered', conversation_id: 'session-a', answer: '첫 번째 안내' }
    await state.ask('운전석 열선 시트 어떻게 켜?')
    assert.equal(requests.at(-1).conversation_id, undefined)
    await state.ask('그럼 끄려면?')
    assert.equal(requests.at(-1).conversation_id, 'session-a')
    state.question.value = '보내지 않은 글'
    state.returnHome()
    assert.equal(state.screen.value, 'assistant')
    assert.equal(state.hasConversation.value, false)
    assert.equal(state.pendingQuestion.value, null)
    assert.equal(state.question.value, '')
    assert.equal(state.chatVehicleId.value, 3)
    await state.ask('운전석 열선 시트 어떻게 켜?')
    assert.equal(requests.at(-1).conversation_id, undefined)

    // A late reply must not resurrect a closed chat or overwrite a newer one,
    // even if the transport cannot cancel an already completed server request.
    let resolveLate, cancelledSignal
    response = signal => {
      cancelledSignal = signal
      return new Promise(resolve => { resolveLate = resolve })
    }
    const late = state.ask('그럼 끄려면?')
    await new Promise(resolve => setImmediate(resolve))
    assert.equal(state.asking.value, true)
    state.returnHome()
    assert.equal(cancelledSignal.aborted, true)
    assert.equal(state.asking.value, false)
    response = { status: 'answered', conversation_id: 'session-b', answer: '새 상담의 안내' }
    await state.ask('전조등 버튼은 어떻게 써?')
    assert.equal(requests.at(-1).conversation_id, undefined)
    resolveLate({ status: 'answered', conversation_id: 'session-a', answer: '끝낸 상담의 늦은 답변' })
    await late
    assert.equal(state.currentMessage.value.answer, '새 상담의 안내')
    assert.equal(state.messages.value.some(message => message.answer === '끝낸 상담의 늦은 답변'), false)
    state.returnHome()

    // A spoken car name continues the original question with a real owned ID.
    await state.chooseChatVehicle(null)
    await state.ask('운전석 열선 시트 어떻게 켜?')
    assert.equal(state.pendingQuestion.value.awaiting, 'vehicle')
    await state.ask('K5로 알려줘')
    assert.equal(state.chatVehicleId.value, 3)
    assert.equal(requests.at(-1).vehicle_id, 3)
    assert.match(requests.at(-1).question, /운전석 열선 시트 어떻게 켜/)
    assert.equal(state.pendingQuestion.value, null)
    state.returnHome()
  } finally {
    app.unmount()
    for (const [key, descriptor] of Object.entries(old)) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor)
      else delete globalThis[key]
    }
  }
})
