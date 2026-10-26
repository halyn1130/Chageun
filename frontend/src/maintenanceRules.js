import rules from '../../ai_data/chageun_ai/maintenance_rules.json' with { type: 'json' }

export function manualRule(vehicle, item, condition = 'normal') {
  const model = vehicle?.model === '디 올 뉴 아반떼' ? '더 뉴 아반떼' : vehicle?.model
  const car = rules.find(r => r.manufacturer === vehicle?.manufacturer && r.model === model && r.model_year === String(vehicle?.model_year) && r.powertrain === vehicle?.powertrain)
  return car?.items[item]?.[condition] || null
}
export function remainingLabel(usage) {
  if (usage.status !== 'recorded' || !usage.interval) return ''
  const parts = []
  if (usage.remainingKm != null) parts.push(usage.remainingKm < 0 ? `${(-usage.remainingKm).toLocaleString('ko-KR')}km 초과` : usage.remainingKm === 0 ? '거리 기준 도달' : `${usage.remainingKm.toLocaleString('ko-KR')}km 남음`)
  if (usage.remainingDays != null) parts.push(usage.remainingDays < 0 ? `${-usage.remainingDays}일 경과` : usage.remainingDays === 0 ? '오늘 날짜 기준 도달' : usage.remainingMonths > 0 ? `${usage.remainingMonths}개월 남음` : `${usage.remainingDays}일 남음`)
  return parts.join(' · ')
}
