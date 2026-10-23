import { latestRecords, maintenanceCatalog } from './guidance.js'
import { oilSchedule, supportsOilSchedule } from './vehicleGuide.js'

// UI demonstration targets, not manufacturer specifications or measured wear.
// Applied only to explicitly seeded demonstration vehicles and never sent to RAG.
export const demoMaintenanceIntervals = {
  oil_filter: { km: 10000, months: 12 },
  air_filter: { km: 30000, months: 24 },
  tire: { km: 40000, months: 48 },
  brake_pad: { km: 30000, months: 36 },
  brake_fluid: { km: 40000, months: 24 },
  cabin_filter: { km: 10000, months: 6 },
  wiper: { km: 15000, months: 12 },
  battery: { km: 60000, months: 36 },
  coolant: { km: 60000, months: 60 },
}

export function localToday() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}
const clamp = (ratio) => Math.max(0, Math.min(1, ratio))
function validDay(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null
  const day = new Date(`${value}T12:00:00Z`)
  return Number.isFinite(day.getTime()) && day.toISOString().slice(0, 10) === value ? day : null
}

function afterMonths(value, months) {
  const date = validDay(value)
  const day = date.getUTCDate()
  date.setUTCDate(1)
  date.setUTCMonth(date.getUTCMonth() + months)
  const lastDay = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate()
  date.setUTCDate(Math.min(day, lastDay))
  return date.toISOString().slice(0, 10)
}

// Progress toward an identified interval, never sensed oil level or part health.
export function maintenanceUsage(vehicle, records, item, { condition = 'normal', now = localToday(), loading = false, error = '', demo = false } = {}) {
  const base = { item, condition, distance: null, distanceRatio: null, timeRatio: null, interval: null, intervalSource: null, priorityRatio: null }
  if (loading) return { ...base, status: 'loading' }
  if (error) return { ...base, status: 'unavailable' }
  if (!vehicle) return { ...base, status: 'no_vehicle' }
  const last = latestRecords(records || []).find((record) => record.item === item?.recordId)
  const reviewed = item?.recordId === 'engine_oil' && supportsOilSchedule(vehicle)
  const schedule = reviewed ? oilSchedule(vehicle, records || [], condition, now) : null
  const demoInterval = demo && records?.some(record => record.memo?.startsWith('[차근 시연]')) ? demoMaintenanceIntervals[item?.recordId] : null
  base.interval = schedule?.interval || demoInterval || null
  base.intervalSource = schedule?.interval ? 'manual' : demoInterval ? 'demo' : null
  if (!last) return { ...base, status: 'no_record' }
  const start = validDay(last.performed_at), end = validDay(now)
  if (!start || !end || start > end || !Number.isFinite(last.mileage_km) || last.mileage_km < 0 ||
      (vehicle.mileage_km != null && (!Number.isFinite(vehicle.mileage_km) || vehicle.mileage_km < last.mileage_km))) {
    return { ...base, status: 'invalid_record' }
  }
  const distance = Number.isFinite(vehicle.mileage_km) ? vehicle.mileage_km - last.mileage_km : null
  const months = (end.getUTCFullYear() - start.getUTCFullYear()) * 12 + end.getUTCMonth() - start.getUTCMonth() - (end.getUTCDate() < start.getUTCDate() ? 1 : 0)
  const days = Math.floor((end - start) / 86400000)
  const nextDate = base.interval ? afterMonths(last.performed_at, base.interval.months) : null
  const distanceProgress = base.interval && distance != null ? distance / base.interval.km : null
  const timeProgress = nextDate ? (end - start) / (validDay(nextDate) - start) : null
  const dateDue = timeProgress != null && timeProgress >= 1
  const mileageDue = distanceProgress != null && distanceProgress >= 1
  return {
    ...base, status: 'recorded', last, distance, months, days,
    distanceRatio: distanceProgress == null ? null : clamp(distanceProgress),
    timeRatio: timeProgress == null ? null : clamp(timeProgress),
    priorityRatio: base.interval ? Math.max(distanceProgress || 0, timeProgress || 0) : null,
    dateDue, mileageDue, nextDate,
    nextKm: base.interval ? last.mileage_km + base.interval.km : null,
    needsConfirmation: dateDue || mileageDue,
  }
}

export function usageState(usage) {
  if (usage.priorityRatio == null) return { tone: 'unknown', label: usage.status === 'recorded' ? '기준 확인' : usage.status === 'no_record' ? '기록 필요' : '기록 확인' }
  if (usage.priorityRatio >= 1) return { tone: 'urgent', label: '교환 시점' }
  if (usage.priorityRatio >= .9) return { tone: 'urgent', label: '교환 임박' }
  if (usage.priorityRatio >= .7) return { tone: 'soon', label: '교환 준비' }
  return { tone: 'comfortable', label: '여유' }
}

export function maintenancePriorities(vehicle, records, options = {}) {
  return maintenanceCatalog
    .map(item => maintenanceUsage(vehicle, records, item, { ...options, demo: true }))
    .sort((a, b) => (b.priorityRatio ?? -1) - (a.priorityRatio ?? -1))
}

// Several maintenance items share one physical illustration. Keep the highest
// urgency visible there; an individual item still uses its own tone in detail.
export function vehicleMaintenanceTones(usages) {
  const ranks = { comfortable: 0, soon: 1, urgent: 2 }
  const tones = {}
  for (const usage of usages) {
    const tone = usageState(usage).tone
    if (tone === 'unknown') continue
    const component = usage.item.component
    const layer = component === 'oil' ? 'engine' : component === 'cabin-filter' ? 'coolant' : component
    if (tones[layer] == null || ranks[tone] > ranks[tones[layer]]) tones[layer] = tone
  }
  return tones
}
