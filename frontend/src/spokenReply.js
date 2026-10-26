// Read the question without reciting screen choices or instructions for answering.
export function spokenReply(message) {
  if (!message) return ''
  const question = message.followup_question?.trim()
  if (!question) {
    const answer = message.recordSummary || message.speech_text || message.answer || ''
    const facts = (message.facts || []).filter(fact => !answer.includes(fact.value)).map(fact => `${fact.label}은 ${fact.value}입니다.`)
    return [answer, ...facts].filter(Boolean).join(' ')
  }
  if (message.clarificationField === 'color') return '불빛이 어떤 색인가요?'
  if (message.status === 'need_vehicle') return '차의 별명이나 차종을 알려 주세요.'
  // Keep context needed to understand “this record” and any safety conditions.
  const support = message.answer?.trim()
  const intro = support && support !== question ? support : ''
  return [intro, question].filter(Boolean).join(' ')
}

const homeCommands = new Set([
  '홈', '홈으로', '홈으로가', '홈으로가줘', '홈으로가주세요',
  '홈으로돌아가', '홈으로돌아가줘', '홈으로돌아가주세요',
  '대화끝', '대화끝내줘', '대화를끝내줘', '대화를마칠게',
  '대화종료', '대화종료해줘', '그만할게', '여기까지할게',
])

export function isHomeCommand(text) {
  return homeCommands.has(text.replace(/[\s.!?。！？]/g, ''))
}
