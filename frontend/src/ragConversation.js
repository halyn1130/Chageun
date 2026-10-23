import {
  buildApiQuestion,
  isMockResult,
  normalizeResult,
} from './conversation.js'
import { latestRecords, findGuideTopic, maintenanceItems } from './guidance.js'
import {
  warningForFlow,
  warningAnswer,
  warningLights,
  supportsOilSchedule,
  oilSchedule,
  MAINTENANCE_SOURCE,
} from './vehicleGuide.js'

const number = (value) => new Intl.NumberFormat('ko-KR').format(value)
const date = (value) => value.replaceAll('-', '.')

// Fulfil a history action in speech as well as through the existing history link.
// This uses the ownership-checked record snapshot already fetched for this turn.
export function describeRecordAction(result, { vehicle, records } = {}) {
  const action = result.action
  if (result.status !== 'tool_result' || action?.type !== 'open_my_car' || !vehicle || action.vehicle_id !== (vehicle._apiId ?? vehicle.id)) return ''
  const label = item => maintenanceItems.find(entry => entry.id === item)?.label || '정비'
  if (!records) return '정비 기록을 불러오지 못했어요. 잠시 후 다시 물어봐 주세요.'
  const matches = latestRecords(records).filter(record => !action.item || action.item === 'all' || record.item === action.item)
  if (!matches.length) return `아직 ${action.item && action.item !== 'all' ? label(action.item) + ' ' : ''}정비 기록이 없어요.`
  return matches.slice(0, 3).map(record => {
    const [year, month, day] = record.performed_at.split('-').map(Number)
    return `최근 ${label(record.item)} 기록은 ${year}년 ${month}월 ${day}일, 주행거리 ${number(record.mileage_km)}킬로미터예요.`
  }).join(' ')
}

export function buildRagRequest(
  flow,
  { vehicle, records, conversationId, vehicleId = flow.vehicleId },
) {
  return {
    question: buildApiQuestion(flow),
    vehicle_id: vehicleId ?? undefined,
    conversation_id: conversationId || undefined,
    context: {
      entry_point: flow.category || 'conversation',
      topic: flow.topicId || flow.topic,
      maintenance_item: flow.recordItem || null,
      original_question: flow.original,
      vehicle: vehicle
        ? {
            manufacturer: vehicle.manufacturer,
            model: vehicle.model,
            model_year: String(vehicle.model_year),
            powertrain: vehicle.powertrain,
            mileage_km: vehicle.mileage_km,
          }
        : null,
      maintenance_status: records ? 'available' : 'unavailable',
      maintenance_records: latestRecords(records || []),
      collected_answers: { ...flow.details },
      followups: flow.followups || [],
    },
  }
}

// Keep compatibility with explicit demo fixtures. Live RAG answers, including
// missing evidence, always take precedence over the reviewed local reference set.
export function resolveRagResponse(flow, raw, { vehicle, records, now } = {}) {
  if (!isMockResult(raw)) return normalizeResult(flow, raw)
  const guide = findGuideTopic(flow.topicId, flow.category)
  const isOil =
    flow.recordItem === 'engine_oil' ||
    (!flow.recordItem && /엔진\s*오일(?!\s*필터)/.test(flow.original))
  if (flow.intent === 'maintenance' && guide?.recordId && !isOil) {
    const last = records?.find((record) => record.item === guide.recordId)
    return {
      status: 'not_found',
      title: `${guide.label}, 확인할 내용을 정리했어요`,
      answer: `현재 상태와 교환 이력을 함께 전달했어요. ${guide.label}의 차량별 점검 기준은 아직 연결 중이라 교환 시기를 확정할 수 없어요.`,
      details: [
        last
          ? `마지막 ${guide.label} 기록: ${date(last.performed_at)} · ${number(last.mileage_km)} km`
          : `${guide.label} 교환 기록 없음`,
        ...Object.values(flow.details),
      ],
      sources: [],
      demo: true,
      action:
        flow.vehicleId != null
          ? {
              type: 'open_my_car',
              vehicle_id: flow.vehicleId,
              item: guide.recordId,
            }
          : undefined,
    }
  }
  if (!supportsOilSchedule(vehicle)) return normalizeResult(flow, raw)
  const warningId = warningForFlow(flow)
  if (warningId) {
    const light = warningLights.find((item) => item.id === warningId)
    return {
      ...warningAnswer(warningId),
      demo: true,
      title: light.urgency,
      summary: light.action,
      answer: `${light.meaning}\n${light.action}`,
      evidenceLabel: '설명서 기준',
      details: [light.note],
    }
  }
  if (flow.intent !== 'maintenance' || !isOil) return normalizeResult(flow, raw)
  const action = {
    type: 'open_my_car',
    vehicle_id: flow.vehicleId,
    item: 'engine_oil',
  }
  const common = {
    status: 'answered',
    sources: [MAINTENANCE_SOURCE],
    demo: true,
    evidenceLabel: '설명서·정비 기록 기준',
    action,
  }
  if (
    flow.details.recordStatus &&
    flow.details.recordStatus !== '기록 이후 교환하지 않음'
  ) {
    return {
      ...common,
      title: '최근 교환 기록이 필요해요',
      answer:
        '최근 교환 날짜와 당시 주행거리를 추가하면 다음 시기를 확인할 수 있어요.',
      speech_text: '최근 교환 기록을 먼저 확인해 주세요.',
      details: [
        '추가 교환 여부가 확인되지 않아 과거 기록으로 시기를 확정하지 않았어요.',
      ],
    }
  }
  const condition =
    flow.details.condition === '짧은 거리·정체가 잦음' ? 'severe' : 'normal'
  const schedule = oilSchedule(vehicle, records || [], condition, now)
  if (!records || !schedule.nextDate)
    return {
      ...common,
      title: '교환 기록부터 확인해요',
      answer: !records
        ? '정비 기록을 불러오지 못했어요. 기록을 확인한 뒤 다시 물어봐 주세요.'
        : schedule.status === 'invalid_record'
          ? '마지막 교환 날짜나 주행거리가 맞는지 확인해 주세요.'
          : '마지막 교환 날짜와 당시 주행거리가 필요해요.',
      speech_text: '마지막 엔진오일 교환 기록을 확인해 주세요.',
    }
  if (flow.details.condition !== '일반 조건' && condition !== 'severe')
    return {
      ...common,
      title: '운행 조건을 먼저 확인해요',
      answer:
        '짧은 거리 반복·잦은 정체 등은 더 짧은 교환 주기를 적용해요. 설명서에서 평소 운행에 해당하는 조건을 확인해 주세요.',
      speech_text:
        '운행 조건에 따라 교환 시기가 달라요. 설명서 기준을 먼저 확인해 주세요.',
      details: [
        '일반: 10,000 km 또는 12개월',
        '가혹 조건: 5,000 km 또는 6개월',
      ],
    }
  const due = schedule.status === 'due'
  const answer = due
    ? '입력한 기록 기준으로 교환 시기가 지났어요. 정비 일정을 확인해 주세요.'
    : '거리와 날짜 중 먼저 도달하는 시점에 교환하세요.'
  return {
    ...common,
    title: due ? '엔진오일 교환을 확인해요' : '다음 엔진오일 교환 시기',
    answer,
    speech_text: `${answer} ${number(schedule.nextKm)} 킬로미터 또는 ${date(schedule.nextDate)} 기준이에요.`,
    facts: [
      { label: '주행거리 기준', value: `${number(schedule.nextKm)} km` },
      { label: '날짜 기준', value: date(schedule.nextDate) },
    ],
    details: [
      `마지막 교환: ${date(schedule.last.performed_at)} · ${number(schedule.last.mileage_km)} km`,
      `${condition === 'severe' ? '가혹' : '일반'} 조건: ${number(schedule.interval.km)} km 또는 ${schedule.interval.months}개월`,
      '사용자 입력 기록 기준이며 현재 차량 상태를 측정한 결과가 아니에요.',
    ],
  }
}
