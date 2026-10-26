import test from 'node:test'
import assert from 'node:assert/strict'
import { spokenReply, isHomeCommand } from '../src/spokenReply.js'
import { clarificationFor, startQuestion, continueQuestion } from '../src/conversation.js'

const promptMessage = flow => {
  const prompt = clarificationFor(flow)
  return { ...prompt, followup_question: prompt.question, clarificationField: prompt.field }
}

test('vehicle selection and maintenance history can be understood without touching a card', () => {
  const vehicle = spokenReply({ status: 'need_vehicle', followup_question: '어떤 차량인가요?', suggestions: ['차량 정보 없이 계속'] })
  assert.equal(vehicle, '차의 별명이나 차종을 알려 주세요.')
  assert.equal(spokenReply({ answer: '정비 이력을 열어 드릴게요.', recordSummary: '최근 와이퍼 기록은 2025년 10월 23일이에요.' }), '최근 와이퍼 기록은 2025년 10월 23일이에요.')
})

test('warning color speech asks only the short question while unknown answers remain accepted', () => {
  const flow = startQuestion('경고등이 켜졌어', 2)
  const message = promptMessage(flow)
  assert.equal(message.followup_question, '불빛이 어떤 색인가요?')
  const speech = spokenReply(message)
  assert.equal(speech, '불빛이 어떤 색인가요?')
  assert.equal(continueQuestion({ ...flow, awaiting: 'color' }, '잘 모르겠어요').details.color, '확인하지 못함')
})

test('shape and seat clarifications speak only the question', () => {
  for (const flow of [startQuestion('빨간 경고등이 켜졌어', 2), startQuestion('엉따 어떻게 켜?', 2)]) {
    const message = promptMessage(flow)
    const speech = spokenReply(message)
    assert.equal(speech, message.followup_question)
  }
})

test('server follow-up does not repeat identical question and answer', () => {
  const message = { followup_question: '어떤 모양인가요?', answer: '어떤 모양인가요?', suggestions: ['주전자', '배터리', '잘 모르겠어요'] }
  const speech = spokenReply(message)
  assert.equal(speech.split('어떤 모양인가요?').length - 1, 1)
  assert.equal(speech, '어떤 모양인가요?')
})

test('spoken result preserves conditions and all numeric facts', () => {
  const speech = spokenReply({
    answer: '시동 후 레버를 앞으로 미세요.', speech_text: '시동 상태에서 해당 좌석의 레버를 앞으로 밀어 주세요.',
    facts: [{ label: '주행거리 기준', value: '40,000 km' }, { label: '날짜 기준', value: '2027.01.23' }],
  })
  assert.ok(speech.includes('시동 상태'))
  assert.ok(speech.includes('40,000 km') && speech.includes('2027.01.23'))
})

test('explicit home requests end the session; questions mentioning a home button do not', () => {
  for (const text of ['홈으로 가줘', '홈으로 돌아가 주세요.', '대화 끝내줘', '그만할게']) assert.equal(isHomeCommand(text), true)
  for (const text of ['홈 버튼은 어디 있어?', '홈으로 가기 전에 질문 있어', '고마워', '그건 뭐야?']) assert.equal(isHomeCommand(text), false)
})
