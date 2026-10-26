import catalog from './preparedGuides.json' with { type: 'json' }

// Only explicit menu choices may use these reviewed answers. Free-form turns
// (including a recognised word inside a longer question) always use RAG.
export function resolvePreparedGuide(flow, vehicle, now = new Date()) {
  if (!flow.preparedEligible || flow.serverFollowup || flow.followups?.length) return null
  const entry = catalog.entries.find(entry => {
    if (entry.category !== flow.category || entry.topicId !== flow.topicId) return false
    if (entry.review_after && now.getTime() >= Date.parse(`${entry.review_after}T00:00:00+09:00`)) return false
    if (entry.vehicle) {
      const expected = entry.vehicle
      if (!vehicle || vehicle.id !== flow.vehicleId || vehicle.manufacturer !== expected.manufacturer
        || !expected.models.includes(vehicle.model) || String(vehicle.model_year) !== expected.model_year
        || vehicle.powertrain !== expected.powertrain) return false
    }
    return Object.entries(entry.match).every(([key, value]) => Array.isArray(value) ? value.includes(flow.details?.[key]) : flow.details?.[key] === value)
  })
  if (!entry) return null
  return {
    status: entry.status || 'answered', title: entry.title || '확인한 내용', answer: entry.answer,
    needs_review: Boolean(entry.needs_review),
    speech_text: entry.speech_text, sources: entry.sources.map(source => ({ ...source })),
    action: { type: 'none' }, evidenceLabel: '매뉴얼 기반 안내',
    details: [`안내 검토일: ${entry.reviewed_at}`, ...(entry.category === 'rules' ? ['선택한 상황의 일반 규칙 안내이며, 현장의 진행 가능 여부를 판단하지 않습니다.'] : [])],
    answerMode: 'prepared',
    ...(entry.category === 'rules' ? { evidenceLabel: '법규 기반 안내' } : {}),
  }
}

export function keepPreparedEligibility(flow, prompt, reply) {
  return Boolean(flow.preparedEligible && prompt?.suggestions?.includes(reply))
}
