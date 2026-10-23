import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createVoiceSession } from '../src/voiceSession.js'
import { spokenReply } from '../src/spokenReply.js'

function setup(onQuestion = async (text) => `답변: ${text}`) {
  const recognizers = [],
    spoken = [],
    states = []
  class Recognition {
    constructor() {
      recognizers.push(this)
    }
    start() {
      this.started = true
      this.onstart?.()
    }
    abort() {
      this.aborted = true
      this.onend?.()
    }
    result(text, final = true) {
      const item = [{ transcript: text }]
      item.isFinal = final
      return this.onresult?.({ results: [item] })
    }
  }
  class Utterance {
    constructor(text) {
      this.text = text
    }
  }
  const platform = {
    SpeechRecognition: Recognition,
    SpeechSynthesisUtterance: Utterance,
    speechSynthesis: {
      cancel() {},
      getVoices: () => [],
      speak: (value) => spoken.push(value),
    },
  }
  const session = createVoiceSession({
    platform,
    onChange: (state) => states.push(state),
    onQuestion,
  })
  return { session, platform, recognizers, spoken, states }
}
test('no microphone starts on creation; only start() opens recognition', () => {
  const { session, recognizers } = setup()
  assert.equal(recognizers.length, 0)
  session.start()
  assert.equal(recognizers.length, 1)
  assert.equal(recognizers[0].lang, 'ko-KR')
  assert.equal(session.getState().phase, 'listening')
})
test('interim text does not submit; final submits once and listens after speech ends', async () => {
  let calls = 0
  const { session, recognizers, spoken } = setup(async () => {
    calls += 1
    return '확인된 답변'
  })
  session.start()
  await recognizers[0].result('엔진', false)
  assert.equal(calls, 0)
  await recognizers[0].result('엔진 경고등')
  await recognizers[0].result('엔진 경고등')
  assert.equal(calls, 1)
  assert.equal(session.getState().phase, 'speaking')
  assert.equal(spoken[0].text, '확인된 답변')
  spoken[0].onend()
  assert.equal(recognizers.length, 2)
  assert.equal(session.getState().phase, 'listening')
})
test('stop during an outstanding answer blocks stale speech and restart', async () => {
  let resolve
  const { session, recognizers, spoken } = setup(
    () =>
      new Promise((done) => {
        resolve = done
      }),
  )
  session.start()
  const waiting = recognizers[0].result('오일 불이 켜졌어')
  session.stop()
  resolve('늦은 답변')
  await waiting
  assert.equal(spoken.length, 0)
  assert.equal(recognizers.length, 1)
  assert.equal(session.getState().active, false)
})
test('stop while listening aborts the microphone and ignores saved late callbacks', () => {
  const { session, recognizers } = setup()
  session.start()
  const late = recognizers[0].onend
  session.stop()
  late()
  assert.equal(recognizers[0].aborted, true)
  assert.equal(session.getState().phase, 'idle')
})
test('permission denial gives an actionable error without retrying the microphone', () => {
  const { session, recognizers } = setup()
  session.start()
  recognizers[0].onerror({ error: 'not-allowed' })
  assert.equal(session.getState().active, false)
  assert.match(session.getState().error, /권한/)
  assert.equal(recognizers.length, 1)
})
test('stopping playback prevents its end event from reopening the mic', async () => {
  const { session, recognizers, spoken } = setup()
  session.start()
  await recognizers[0].result('질문')
  session.stop()
  spoken[0].onend()
  assert.equal(recognizers.length, 1)
  assert.equal(session.getState().phase, 'idle')
})
test('read-only answer playback never starts recognition; unsupported browser has text fallback', () => {
  const { session, recognizers, spoken } = setup()
  session.read('답변 읽기')
  spoken[0].onend()
  assert.equal(recognizers.length, 0)
  const unsupported = createVoiceSession({
    platform: {},
    onChange() {},
    onQuestion() {},
  })
  unsupported.start()
  assert.equal(unsupported.getState().supported, false)
  assert.match(unsupported.getState().error, /글로/)
})

test('a voice clarification speaks the choices before reopening the microphone', async () => {
  const { session, recognizers, spoken } = setup(async () => spokenReply({
    followup_question: '불빛이 어떤 색인가요?', clarificationField: 'color',
    suggestions: ['빨간색', '노란색', '다른 색이에요', '잘 모르겠어요'],
  }))
  session.start()
  await recognizers[0].result('경고등이 켜졌어')
  assert.equal(recognizers.length, 1, 'do not listen while reading choices')
  for (const choice of ['빨간색인가요', '노란색인가요', '다른 색', '모르겠어요']) assert.ok(spoken[0].text.includes(choice))
  spoken[0].onend()
  assert.equal(recognizers.length, 2)
  assert.equal(session.getState().phase, 'listening')
})
