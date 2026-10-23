const unknownChoice = /모르|확인.*못|확인하지|정보 없이|건너뛰|안 보여/

// Screen labels and spoken choices share the same data. No option needs to be
// seen or tapped to answer a clarification, including the unknown option.
export function spokenReply(message) {
  if (!message) return ''
  const question = message.followup_question?.trim()
  if (!question) {
    const answer = message.recordSummary || message.speech_text || message.answer || ''
    const facts = (message.facts || []).filter(fact => !answer.includes(fact.value)).map(fact => `${fact.label}은 ${fact.value}입니다.`)
    return [answer, ...facts].filter(Boolean).join(' ')
  }
  const options = [...new Set((message.suggestions || []).filter(Boolean))]
  const known = options.filter(option => !unknownChoice.test(option))
  const unknown = options.some(option => unknownChoice.test(option))
  const support = message.answer?.trim()
  const intro = support && support !== question ? support : ''
  let prompt = question
  if (message.status === 'need_vehicle') {
    return [intro, question, '등록한 차의 별명이나 차종을 말씀해 주세요. 차량 정보를 모르시면 “차량 정보 없이 계속”이라고 말씀하셔도 돼요.'].filter(Boolean).join(' ')
  }
  if (message.clarificationField === 'color') {
    const colors = known.filter(option => /색$/.test(option))
    prompt = colors.length ? `불빛이 ${colors.map(color => `${color}인가요`).join(', ')}?` : question
    if (known.some(option => /다른 색/.test(option))) prompt += ' 다른 색이면 그 색을 말씀해 주세요.'
  } else if (known.length) {
    prompt += ` ${known.map(option => `“${option}”`).join(', ')} 중에서 답해 주세요.`
  }
  if (unknown) prompt += ' 잘 모르시겠다면 “모르겠어요”라고 말씀해 주세요. 괜찮아요.'
  return [intro, prompt].filter(Boolean).join(' ')
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
