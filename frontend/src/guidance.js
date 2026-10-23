import { oilSchedule } from './vehicleGuide.js'

// One catalogue drives exploration, conversation context and record forms.
// The product plan's filters and brake fluid are separate maintenance items.
export const maintenanceCatalog = [
  {
    id: 'oil',
    recordId: 'engine_oil',
    label: '엔진오일',
    group: 'engine',
    component: 'engine',
    icon: 'oil',
    description: '엔진을 부드럽게 움직이게 하는 오일',
    concern: '평소와 다른 점이 있나요?',
    choices: [
      '특별한 이상은 없어요',
      '오일이 줄어드는 것 같아요',
      '소리나 진동이 달라요',
    ],
  },
  {
    id: 'oil-filter',
    recordId: 'oil_filter',
    label: '엔진오일 필터',
    group: 'engine',
    component: 'engine',
    icon: 'oil-filter',
    description: '엔진오일 속 이물질을 거르는 필터',
    concern: '엔진오일을 갈 때 필터도 함께 교환했나요?',
    choices: ['함께 교환했어요', '오일만 교환했어요', '잘 모르겠어요'],
  },
  {
    id: 'air-filter',
    recordId: 'air_filter',
    label: '엔진 에어필터',
    group: 'engine',
    component: 'engine',
    icon: 'air-filter',
    description: '엔진으로 들어가는 공기를 거르는 필터',
    concern: '먼지가 많은 곳을 자주 다니나요?',
    choices: ['자주 다녀요', '거의 다니지 않아요', '잘 모르겠어요'],
  },
  {
    id: 'tire',
    recordId: 'tire',
    label: '타이어',
    group: 'driving',
    component: 'tires',
    icon: 'tire',
    description: '노면과 맞닿는 네 바퀴의 상태',
    concern: '타이어에서 무엇이 신경 쓰이나요?',
    choices: [
      '교체 시기가 궁금해요',
      '공기압 경고가 있어요',
      '마모가 보여요',
      '진동이 느껴져요',
    ],
  },
  {
    id: 'brake-pad',
    recordId: 'brake_pad',
    label: '브레이크 패드',
    group: 'driving',
    component: 'brakes',
    icon: 'brake',
    description: '속도를 줄일 때 마찰을 만드는 부품',
    concern: '브레이크를 밟을 때 어떤가요?',
    choices: [
      '특별한 이상은 없어요',
      '소리가 나요',
      '진동이 느껴져요',
      '제동감이 달라요',
    ],
  },
  {
    id: 'brake-fluid',
    recordId: 'brake_fluid',
    label: '브레이크액',
    group: 'driving',
    component: 'brakes',
    icon: 'drop',
    description: '브레이크에 힘을 전달하는 액체',
    concern: '브레이크 경고등이나 변화가 있나요?',
    choices: [
      '교환 시기만 궁금해요',
      '경고등이 켜졌어요',
      '페달 느낌이 달라요',
    ],
  },
  {
    id: 'cabin-filter',
    recordId: 'cabin_filter',
    label: '에어컨 필터',
    group: 'comfort',
    component: 'cabin-filter',
    icon: 'cabin-filter',
    description: '차 안으로 들어오는 공기를 거르는 필터',
    concern: '에어컨이나 히터를 켜면 어떤가요?',
    choices: ['특별한 이상은 없어요', '냄새가 나요', '바람이 약해요'],
  },
  {
    id: 'wiper',
    recordId: 'wiper',
    label: '와이퍼',
    group: 'comfort',
    component: 'wiper',
    icon: 'wiper',
    description: '비 오는 날 시야를 확보하는 고무날',
    concern: '유리가 어떻게 닦이나요?',
    choices: [
      '잘 닦여요',
      '줄무늬가 남아요',
      '소리가 나요',
      '잘 닦이지 않아요',
    ],
  },
  {
    id: 'battery',
    recordId: 'battery',
    label: '배터리',
    group: 'electric',
    component: 'battery',
    icon: 'battery',
    description: '시동과 차량 전기 장치에 전원을 공급해요',
    concern: '시동을 걸 때 어떤가요?',
    choices: [
      '평소와 같아요',
      '시동이 늦게 걸려요',
      '시동이 안 걸려요',
      '방전된 적 있어요',
    ],
  },
  {
    id: 'coolant',
    recordId: 'coolant',
    label: '냉각수',
    group: 'electric',
    component: 'coolant',
    icon: 'temp',
    description: '엔진의 열을 식히는 냉각 계통',
    concern: '냉각 계통에서 달라진 점이 있나요?',
    choices: [
      '교환 시기만 궁금해요',
      '온도 경고가 있어요',
      '냉각수가 줄어요',
      '바닥에 액체가 보여요',
    ],
  },
].map((item) => ({
  ...item,
  question: `내 차 ${item.label}의 점검·교환 시기를 어떻게 확인해?`,
}))
export const maintenanceItems = [
  ...maintenanceCatalog.map(({ recordId, label }) => ({ id: recordId, label })),
  { id: 'other', label: '기타 정비' },
]
export const maintenanceGroups = [
  {
    id: 'engine',
    label: '엔진·오일',
    icon: 'oil',
    detail: '엔진오일 · 오일필터 · 에어필터',
    component: 'engine',
  },
  {
    id: 'driving',
    label: '주행·제동',
    icon: 'tire',
    detail: '타이어 · 브레이크 패드 · 브레이크액',
    component: 'tires',
  },
  {
    id: 'comfort',
    label: '공기·시야',
    icon: 'wind',
    detail: '에어컨 필터 · 와이퍼',
    component: 'cabin-filter',
  },
  {
    id: 'electric',
    label: '전기·냉각',
    icon: 'battery',
    detail: '배터리 · 냉각수',
    component: 'battery',
  },
]
const topic = (id, label, question, component, extra = {}) => ({
  id,
  label,
  question,
  component,
  ...extra,
})
export const guidanceCategories = [
  {
    id: 'maintenance',
    label: '정비·소모품',
    icon: 'wrench',
    description: '교환 시기와 관리할 것',
    meta: '10가지 관리 항목',
    title: '내 차 관리',
    subtitle: '기록에서 시작하는 내 차 관리',
    groups: maintenanceGroups,
    topics: maintenanceCatalog,
  },
  {
    id: 'warning',
    label: '경고·이상',
    icon: 'alert',
    description: '차가 보내는 신호와 달라진 증상',
    meta: '증상부터 함께 확인',
    title: '어떤 변화가 생겼나요?',
    subtitle: '정확한 이름을 몰라도 괜찮아요',
    topics: [
      topic(
        'light',
        '계기판에 불이 켜졌어요',
        '계기판에 낯선 경고등이 켜졌어',
        null,
        {
          icon: 'alert',
          description: '색과 모양으로 알아보기',
          intent: 'warning',
        },
      ),
      topic(
        'symptom',
        '소리·진동이 달라요',
        '차에서 평소와 다른 소리나 진동이 나',
        null,
        {
          icon: 'audio',
          description: '언제, 어디서 생기는지',
          intent: 'symptom',
        },
      ),
      topic(
        'starting',
        '시동이 잘 안 걸려요',
        '시동이 잘 걸리지 않아',
        'battery',
        {
          icon: 'power',
          description: '시동 때 반응부터 확인',
          intent: 'symptom',
        },
      ),
      topic('smell', '냄새·연기가 나요', '차에서 낯선 냄새나 연기가 나', null, {
        icon: 'wind',
        description: '어디서 나는지 확인',
        intent: 'symptom',
      }),
      topic(
        'fuel',
        '주유등이 켜졌어요',
        '주유등이 켜졌어. 계기판에서 무엇을 확인해?',
        'fuel',
        { icon: 'fuel', description: '표시된 연료 정보 확인', intent: 'fuel' },
      ),
      topic(
        'leak',
        '바닥에 액체가 보여요',
        '차를 세워 둔 바닥에 액체가 보여',
        null,
        {
          icon: 'drop',
          description: '위치와 색을 설명하기',
          intent: 'symptom',
        },
      ),
    ],
  },
  {
    id: 'controls',
    label: '기능·조작',
    icon: 'sliders',
    description: '내 차의 버튼과 기능 사용법',
    meta: '기능별 사용 안내',
    title: '차 안 기능',
    subtitle: '내 차에 맞는 버튼과 사용법',
    groups: [
      {
        id: 'climate',
        label: '온도·공기',
        icon: 'wind',
        detail: '에어컨 · 히터 · 내기순환',
        component: 'cabin',
      },
      {
        id: 'visibility',
        label: '시야·조명',
        icon: 'sun',
        detail: '김서림 · 와이퍼 · 라이트',
        component: 'cabin',
      },
      {
        id: 'seating',
        label: '시트·편의',
        icon: 'seat',
        detail: '열선 · 통풍 · 거울',
        component: 'cabin',
      },
      {
        id: 'assistance',
        label: '주행 보조',
        icon: 'steer',
        detail: '크루즈 · 오토홀드 · 주차 브레이크',
        component: null,
      },
    ],
    topics: [
      topic(
        'ac',
        '에어컨·히터',
        '에어컨과 히터 온도는 어떻게 조절해?',
        'cabin',
        { group: 'climate' },
      ),
      topic(
        'air-mode',
        '내기·외기순환',
        '내기순환 버튼과 외기순환은 어떻게 달라?',
        'cabin',
        { group: 'climate' },
      ),
      topic(
        'defrost',
        '유리 김서림',
        '유리에 김이 서렸어. 김서림 어떻게 없애?',
        'cabin',
        { group: 'visibility' },
      ),
      topic(
        'wipers',
        '와이퍼·워셔액',
        '와이퍼와 워셔액 버튼 어떻게 써?',
        'wiper',
        { group: 'visibility' },
      ),
      topic(
        'lights',
        '전조등·상향등',
        '전조등과 상향등 버튼은 어떻게 써?',
        null,
        { group: 'visibility' },
      ),
      topic('seat', '열선 시트', '엉따 어떻게 켜?', 'cabin', {
        group: 'seating',
      }),
      topic('ventilation', '통풍 시트', '통풍 시트 버튼 어떻게 켜?', 'cabin', {
        group: 'seating',
      }),
      topic(
        'mirrors',
        '사이드미러',
        '사이드미러 조절 버튼 어떻게 써?',
        'cabin',
        { group: 'seating' },
      ),
      topic(
        'cruise',
        '크루즈 컨트롤',
        '크루즈 컨트롤 사용 방법과 조건을 알려줘',
        null,
        { group: 'assistance' },
      ),
      topic(
        'autohold',
        '오토홀드',
        '오토홀드 버튼 사용 방법을 알려줘',
        'brakes',
        { group: 'assistance' },
      ),
      topic(
        'parking-brake',
        '전자식 주차 브레이크',
        '전자식 주차 브레이크 버튼 사용 방법을 알려줘',
        'brakes',
        { group: 'assistance' },
      ),
    ],
  },
  {
    id: 'rules',
    label: '도로 규칙',
    icon: 'sign',
    description: '도로에서 헷갈리는 상황과 통행 규칙',
    meta: '법규의 근거까지',
    title: '도로 위에서',
    subtitle: '헷갈리는 규칙을 상황별로',
    groups: [
      {
        id: 'intersection',
        label: '교차로에서',
        icon: 'sign',
        detail: '우회전 · 비보호 좌회전 · 회전교차로',
      },
      {
        id: 'road-lines',
        label: '차선·표지',
        icon: 'route',
        detail: '차선 변경 · 노면 표시',
      },
      {
        id: 'parking',
        label: '주차·정차',
        icon: 'parking',
        detail: '주정차 금지 · 도로 가장자리',
      },
      {
        id: 'pedestrians',
        label: '보행자·보호구역',
        icon: 'walk',
        detail: '횡단보도 · 어린이보호구역',
      },
    ],
    topics: [
      topic(
        'right-turn',
        '교차로 우회전',
        '교차로 우회전의 법규상 조건을 알려줘',
        null,
        { group: 'intersection' },
      ),
      topic(
        'unprotected',
        '비보호 좌회전',
        '비보호 좌회전의 법규상 조건을 알려줘',
        null,
        { group: 'intersection' },
      ),
      topic(
        'roundabout',
        '회전교차로',
        '회전교차로의 통행 우선순위 규칙을 알려줘',
        null,
        { group: 'intersection' },
      ),
      topic(
        'lane',
        '차선 변경',
        '차선 변경과 관련된 일반적인 도로 규칙을 알려줘',
        null,
        { group: 'road-lines' },
      ),
      topic(
        'road-markings',
        '도로 위 선과 표지',
        '실선과 점선 같은 노면 표시의 의미를 알려줘',
        null,
        { group: 'road-lines' },
      ),
      topic(
        'parking',
        '주정차 금지 구역',
        '주정차 금지 구역의 법규상 조건을 알려줘',
        null,
        { group: 'parking' },
      ),
      topic(
        'curb',
        '도로 가장자리 표시',
        '도로 가장자리의 황색선과 주정차 표지 의미를 알려줘',
        null,
        { group: 'parking' },
      ),
      topic(
        'crosswalk',
        '횡단보도',
        '횡단보도에서 보행자를 보호하는 도로 규칙을 알려줘',
        null,
        { group: 'pedestrians' },
      ),
      topic(
        'school',
        '어린이보호구역',
        '어린이보호구역에서 주의할 도로 규칙을 알려줘',
        null,
        { group: 'pedestrians' },
      ),
    ],
  },
]

export function findGuideTopic(id, category) {
  return guidanceCategories
    .filter((item) => !category || item.id === category)
    .flatMap((item) => item.topics)
    .find((item) => item.id === id)
}
export function latestRecords(records = []) {
  const byItem = new Map()
  for (const record of [...records].sort(
    (a, b) =>
      String(b.performed_at).localeCompare(String(a.performed_at)) ||
      b.mileage_km - a.mileage_km,
  )) {
    if (!byItem.has(record.item))
      byItem.set(record.item, {
        item: record.item,
        performed_at: record.performed_at,
        mileage_km: record.mileage_km,
      })
  }
  return [...byItem.values()]
}
export function maintenanceOverview(records = []) {
  const latest = latestRecords(records)
  return maintenanceCatalog.map((item) => ({
    ...item,
    record: latest.find((record) => record.item === item.recordId) || null,
  }))
}
export function personalRecommendation(
  vehicle,
  records = [],
  { loading = false, error = '', now } = {},
) {
  if (!vehicle)
    return {
      title: '내 차부터 선택해요',
      reason: '차종에 맞는 안내를 준비할게요.',
      category: null,
    }
  if (loading)
    return {
      title: '정비 기록을 확인하고 있어요',
      reason: vehicle.model,
      category: 'maintenance',
    }
  if (error)
    return {
      title: '정비 기록을 다시 확인해요',
      reason: '기록을 불러오지 못했어요.',
      category: 'maintenance',
    }
  const schedule = oilSchedule(vehicle, records, 'normal', now)
  if (schedule.status === 'due')
    return {
      title: '엔진오일, 교환 기록을 확인해요',
      reason: `마지막 기록 ${schedule.last.performed_at.replaceAll('-', '.')} · 이후 교환 여부 확인`,
      category: 'maintenance',
      topic: 'oil',
      tone: 'attention',
    }
  if (schedule.status === 'upcoming')
    return {
      title: '다음 엔진오일 교환을 준비해요',
      reason: `마지막 교환 ${new Intl.NumberFormat('ko-KR').format(schedule.last.mileage_km)} km`,
      category: 'maintenance',
      topic: 'oil',
    }
  return {
    title: `${vehicle.model} 정비 기록부터 확인해요`,
    reason:
      schedule.status === 'invalid_record'
        ? '기록의 날짜와 주행거리를 확인해 주세요.'
        : '무엇을 관리해야 할지 하나씩 알아봐요.',
    category: 'maintenance',
  }
}
