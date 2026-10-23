export const WARNING_SOURCE = {
  title: '기아 K5 2024 사용 설명서 · 경고등',
  page: '경고등 및 표시등',
  url: 'https://ownersmanual.kia.com/full_webhelp/DL3/2024/ko_KR/topics/t00548.html',
}
export const MAINTENANCE_SOURCE = {
  title: '기아 K5 2024 사용 설명서 · 정기 점검',
  page: '스마트스트림 G1.6 T-GDi',
  url: 'https://ownersmanual.kia.com/full_webhelp/DL3/2024/ko_KR/topics/t01048.html',
}
export const COOLANT_SOURCE = {
  title: '기아 K5 2024 사용 설명서 · 냉각수 점검',
  url: 'https://ownersmanual.kia.com/full_webhelp/DL3/2024/ko_KR/topics/t01052.html',
}

// User-selected symbols, never telemetry or a diagnosis of a failed part.
export const warningLights = [
  {
    id: 'engine',
    label: '엔진',
    fullName: '엔진 경고등',
    color: 'amber',
    component: 'engine',
    meaning: '엔진 제어·배출가스 계통 등의 점검이 필요해요.',
    action: '계속 켜지거나 깜빡이면 빠르게 정비를 받으세요.',
    urgency: '점검 필요',
    note: '표시만으로 고장 부품을 확정할 수 없어요.',
  },
  {
    id: 'oil',
    label: '오일 압력',
    fullName: '엔진오일 압력 경고등',
    color: 'red',
    component: 'engine',
    meaning: '엔진을 보호하는 오일 압력이 낮을 수 있어요.',
    action:
      '안전한 곳에 정차해 오일량을 확인하고, 계속 켜지면 정비를 요청하세요.',
    urgency: '안전하게 정차',
    note: '교환 주기 알림과는 다른 경고예요.',
  },
  {
    id: 'battery',
    label: '충전',
    fullName: '충전 경고등',
    color: 'red',
    component: 'battery',
    meaning: '배터리·벨트·충전 계통을 점검해야 해요.',
    action: '계속 주행하면 방전이나 과열이 생길 수 있어 정비가 필요해요.',
    urgency: '충전 계통 점검',
    note: '배터리 자체의 고장으로 단정하지 않아요.',
  },
  {
    id: 'brake',
    label: '브레이크',
    fullName: '브레이크 경고등',
    color: 'red',
    component: 'brakes',
    meaning: '주차 브레이크 작동 또는 브레이크액 부족 표시예요.',
    action:
      '주차 브레이크를 풀어도 켜져 있거나 주행 중 켜지면 안전하게 정차하세요.',
    urgency: '해제 후에도 켜지면 정차',
    note: '강조된 디스크는 제동 계통의 위치 예시예요.',
  },
  {
    id: 'tire',
    label: '공기압',
    fullName: '타이어 공기압 경고등',
    color: 'amber',
    component: 'tires',
    meaning: '공기압 부족 또는 TPMS 이상일 수 있어요.',
    action:
      '공기압을 점검하세요. 약 1분 깜빡인 뒤 계속 켜지면 TPMS 점검이 필요해요.',
    urgency: '공기압 확인',
    note: '어느 바퀴인지는 이 표시만으로 알 수 없어요.',
  },
  {
    id: 'fuel',
    label: '연료',
    fullName: '연료 부족 경고등',
    color: 'amber',
    component: 'fuel',
    meaning: '남은 연료가 적다는 뜻이에요.',
    action:
      '가능한 빨리 주유하세요. 경고등만으로 남은 거리를 보장할 수 없어요.',
    urgency: '주유 필요',
    note: '연료량과 주행 가능 거리는 연결되지 않았어요.',
  },
  {
    id: 'abs',
    label: 'ABS',
    fullName: 'ABS 경고등',
    color: 'amber',
    component: 'brakes',
    meaning: '시동 후에도 계속 켜지면 ABS 점검이 필요해요.',
    action: '정비를 받으세요. 브레이크 경고등도 함께 켜졌는지 확인하세요.',
    urgency: '제동 계통 점검',
    note: 'ABS는 바퀴 잠김을 줄이는 제동 보조 장치예요.',
  },
  {
    id: 'airbag',
    label: '에어백',
    fullName: '에어백 경고등',
    color: 'red',
    component: 'cabin',
    meaning: '시동 초기 점등 후에도 남아 있으면 점검이 필요해요.',
    action: '주행 중 켜지거나 계속 켜지면 정비를 받으세요.',
    urgency: '보호 장치 점검',
    note: '에어백의 위치는 차종과 사양에 따라 달라요.',
  },
]

export const vehicleParts = [
  {
    id: 'engine',
    label: '엔진 · 오일',
    symbol: 'oil',
    warningId: 'oil',
    x: 25,
    y: 47,
  },
  {
    id: 'battery',
    label: '12V 배터리',
    symbol: 'battery',
    warningId: 'battery',
    x: 33,
    y: 57,
  },
  {
    id: 'brakes',
    label: '브레이크',
    symbol: 'brake',
    warningId: 'brake',
    x: 43,
    y: 79,
  },
  {
    id: 'tires',
    label: '타이어',
    symbol: 'tire',
    warningId: 'tire',
    x: 87,
    y: 61,
  },
  {
    id: 'fuel',
    label: '연료 탱크',
    symbol: 'fuel',
    warningId: 'fuel',
    x: 71,
    y: 52,
  },
  { id: 'coolant', label: '냉각 계통', x: 14, y: 67 },
  { id: 'cabin', label: '실내 안전장치', warningId: 'airbag', x: 59, y: 28 },
]

export function supportsOilSchedule(vehicle) {
  return (
    vehicle?.manufacturer === '기아' &&
    vehicle?.model === 'K5' &&
    Number(vehicle?.model_year) === 2024 &&
    /1\.6\s*(T|터보)/i.test(vehicle?.powertrain || '') &&
    !/하이브리드|디젤|LPG/i.test(vehicle?.powertrain || '')
  )
}

function parseDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null
  const date = new Date(`${value}T12:00:00Z`)
  return Number.isFinite(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
    ? date
    : null
}
function addMonths(value, months) {
  const date = parseDate(value)
  const day = date.getUTCDate()
  date.setUTCDate(1)
  date.setUTCMonth(date.getUTCMonth() + months)
  const last = new Date(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0),
  ).getUTCDate()
  date.setUTCDate(Math.min(day, last))
  return date.toISOString().slice(0, 10)
}

export function oilSchedule(
  vehicle,
  records,
  condition = 'normal',
  now = new Date().toISOString().slice(0, 10),
) {
  if (!supportsOilSchedule(vehicle)) return { status: 'unsupported' }
  const interval =
    condition === 'severe' ? { km: 5000, months: 6 } : { km: 10000, months: 12 }
  const candidates = records
    .filter((record) => record.item === 'engine_oil')
    .sort((a, b) =>
      String(b.performed_at).localeCompare(String(a.performed_at)),
    )
  const last = candidates[0]
  if (!last) return { status: 'no_record', interval }
  if (
    !parseDate(last.performed_at) ||
    last.performed_at > now ||
    !Number.isFinite(last.mileage_km) ||
    last.mileage_km < 0 ||
    (vehicle.mileage_km != null && vehicle.mileage_km < last.mileage_km)
  ) {
    return { status: 'invalid_record', interval }
  }
  const nextDate = addMonths(last.performed_at, interval.months)
  const nextKm = last.mileage_km + interval.km
  const dateDue = now >= nextDate
  const mileageDue =
    Number.isFinite(vehicle.mileage_km) && vehicle.mileage_km >= nextKm
  return {
    status: dateDue || mileageDue ? 'due' : 'upcoming',
    interval,
    last,
    nextDate,
    nextKm,
    dateDue,
    mileageDue,
  }
}

export function warningAnswer(id) {
  const light = warningLights.find((item) => item.id === id)
  if (!light) return null
  return {
    status: 'answered',
    warningId: id,
    answer: `${light.meaning}\n${light.action}\n\n${light.note}`,
    speech_text: `${light.fullName}. ${light.meaning} ${light.action}`,
    sources: [WARNING_SOURCE],
    details: ['K5 2024 사용 설명서 기준 · 선택한 표시의 일반 안내'],
  }
}

export function identifyWarning(text) {
  if (/오일|주전자/.test(text) && /경고|불|압력|표시/.test(text)) return 'oil'
  if (/배터리|충전/.test(text) && /경고|불|표시/.test(text)) return 'battery'
  if (/브레이크/.test(text) && /경고|불|표시/.test(text)) return 'brake'
  if (/ABS/i.test(text) && /경고|불|표시/.test(text)) return 'abs'
  if (/타이어|말발굽|공기압/.test(text) && /경고|불|표시/.test(text))
    return 'tire'
  if (/주유등|연료.*(부족|경고)|기름.*불/.test(text)) return 'fuel'
  if (/엔진/.test(text) && /경고|모양.*불/.test(text)) return 'engine'
  if (/에어백/.test(text) && /경고|불|표시/.test(text)) return 'airbag'
  return null
}

export function warningForFlow(flow) {
  if (!['warning', 'fuel'].includes(flow.intent)) return null
  const id = identifyWarning(`${flow.original} ${flow.details.shape || ''}`)
  const light = warningLights.find((item) => item.id === id)
  if (!light) return null
  const color = flow.details.color || ''
  if (light.color === 'amber' && /빨|붉/.test(color)) return null
  if (light.color === 'red' && /노|주황|초록|녹색|파란/.test(color)) return null
  return id
}
