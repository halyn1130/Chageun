<script setup>
import { computed, ref, watch } from 'vue'
import {
  ArrowLeft,
  ArrowUpRight,
  ChevronRight,
  BookOpen,
  Mic,
  Square,
  Keyboard,
  ArrowUp,
  Volume2,
  Plus,
  History,
  RotateCcw,
  Check,
  ArrowRight,
  MessageCircle,
} from 'lucide-vue-next'
import VehicleStructure from './VehicleStructure.vue'
import GuideIcon from './GuideIcon.vue'
import RoadContext from './RoadContext.vue'
import MaintenanceUsage from './MaintenanceUsage.vue'
import MaintenanceCard from './MaintenanceCard.vue'
import { maintenanceUsage, maintenancePriorities, usageState, vehicleMaintenanceTones } from '../maintenanceUsage.js'
import {
  guidanceCategories,
  maintenanceCatalog,
  maintenanceItems,
  maintenanceOverview,
} from '../guidance.js'

const props = defineProps({
  vehicle: Object,
  records: { type: Array, default: () => [] },
  loading: Boolean,
  error: String,
  entry: Object,
  message: Object,
  asking: Boolean,
  voiceState: Object,
  vehicles: Array,
  intro: Boolean,
})
const emit = defineEmits([
  'consult',
  'reply',
  'voice',
  'stop',
  'source',
  'vehicle',
  'choose-vehicle',
  'retry',
  'speak',
  'reset',
  'add-record',
  'reload-records',
  'introduced',
  'context',
  'question',
  'mode',
])
const categoryId = ref(props.entry?.category || 'maintenance')
const category = computed(
  () =>
    guidanceCategories.find((item) => item.id === categoryId.value) ||
    guidanceCategories[0],
)
const itemId = ref(props.entry?.topic || null)
const initialItem = category.value.topics.find(
  (item) => item.id === itemId.value,
)
const groupId = ref(initialItem?.group || null)
const mode = ref(
  props.entry?.answer
    ? 'conversation'
    : props.entry?.view === 'history'
      ? 'history'
      : initialItem?.recordId
        ? 'item'
        : 'browse',
)
const historyFilter = ref(props.entry?.recordFilter || 'all')
const keyboard = ref(false)
const typed = ref('')
const messageFloor = ref(0)
const group = computed(() =>
  category.value.groups?.find((item) => item.id === groupId.value),
)
const item = computed(() =>
  category.value.topics.find((topic) => topic.id === itemId.value),
)
const message = computed(() =>
  mode.value === 'conversation' && props.message?.id > messageFloor.value
    ? props.message
    : null,
)
const activeItem = computed(() =>
  !message.value ||
  !message.value.topicId ||
  message.value.topicId === item.value?.id
    ? item.value
    : null,
)
const focus = computed(() =>
  mode.value === 'history'
    ? null
    : message.value?.warningId ||
      activeItem.value?.component ||
      group.value?.component ||
      (categoryId.value === 'controls' ? 'cabin' : null),
)
const visibleTopics = computed(() =>
  category.value.topics.filter(
    (item) => !groupId.value || item.group === groupId.value,
  ),
)
const overview = computed(() => maintenanceOverview(props.records))
const selectedRecord = computed(
  () => overview.value.find((topic) => topic.id === itemId.value)?.record,
)
const isCareOverview = computed(() => categoryId.value === 'maintenance' && mode.value === 'browse' && !group.value)
const hasCareTabs = computed(() => categoryId.value === 'maintenance' && (isCareOverview.value || mode.value === 'history'))
const careList = ref(null)
const workspace = ref(null)
let careScroll = 0
let overviewScroll = 0
const priorities = computed(() => maintenancePriorities(props.vehicle, props.records, props))
const urgentParts = computed(() => priorities.value.filter(usage => usage.priorityRatio >= .9))
const vehicleTones = computed(() => vehicleMaintenanceTones(priorities.value))
const itemReturnMode = ref('browse')
const itemReturnGroup = ref(null)
const condition = ref('normal')
const selectedUsage = computed(() => maintenanceUsage(props.vehicle, props.records, item.value, { ...props, condition: condition.value, demo: true }))
const isConclusion = computed(() => mode.value === 'conversation' && message.value && !props.asking && !message.value.followup_question && !['need_vehicle', 'need_details', 'error'].includes(message.value.status))
const history = computed(() =>
  [...props.records]
    .filter(
      (record) =>
        historyFilter.value === 'all' || record.item === historyFilter.value,
    )
    .sort(
      (a, b) =>
        b.performed_at.localeCompare(a.performed_at) ||
        b.mileage_km - a.mileage_km,
    ),
)
const header = computed(() =>
  mode.value === 'history'
    ? '정비·교환 기록'
    : mode.value === 'conversation'
      ? activeItem.value?.label || '차근과 이야기하기'
      : mode.value === 'item'
        ? item.value.label
        : group.value?.label ||
          {
            maintenance: '소모품 관리',
            warning: '어떤 변화가 생겼나요?',
            controls: '내 차와 친해지기',
            rules: '어떤 상황이 궁금하세요?',
          }[categoryId.value],
)
const stageKey = computed(
  () => `${categoryId.value}-${groupId.value}-${itemId.value}-${mode.value}`,
)
watch(mode, value => emit('mode', value), { immediate: true })
const hasBack = computed(() => groupId.value || mode.value !== 'browse')
const voiceActive = computed(
  () => props.voiceState.active || props.voiceState.phase === 'speaking',
)
const voiceLabel = computed(() =>
  props.voiceState.phase === 'listening'
    ? '듣고 있어요'
    : props.voiceState.phase === 'thinking'
      ? '확인하고 있어요'
      : voiceActive.value
        ? '음성 대화 종료'
        : mode.value === 'conversation'
          ? '말로 답하기'
          : '말로 물어보기',
)
const number = (value) => new Intl.NumberFormat('ko-KR').format(value)
const date = (value) => value?.replaceAll('-', '.') || '날짜 미입력'
const recordName = (record) =>
  maintenanceItems.find((item) => item.id === record.item)?.label ||
  record.item_label ||
  record.item
function selectGroup(value) {
  emit('stop')
  emit('reset')
  groupId.value = value.id
  itemId.value = null
  mode.value = 'browse'
  keyboard.value = false
}
function selectItem(value) {
  rememberCareScroll()
  itemReturnMode.value = mode.value === 'history' ? 'history' : 'browse'
  itemReturnGroup.value = mode.value === 'browse' ? groupId.value : null
  itemId.value = value.id
  condition.value = 'normal'
  if (value.recordId) {
    groupId.value = value.group
    mode.value = 'item'
  } else consult(value)
}
function showOverview() {
  emit('stop')
  emit('reset')
  groupId.value = null
  itemId.value = null
  mode.value = 'browse'
  keyboard.value = false
}
function consult(value = item.value) {
  emit('stop')
  emit('reset')
  messageFloor.value = props.message?.id || 0
  mode.value = 'conversation'
  keyboard.value = false
  emit('consult', { ...value, category: categoryId.value })
}
function openHistory(filter = 'all') {
  rememberCareScroll()
  emit('stop')
  emit('reset')
  categoryId.value = 'maintenance'
  mode.value = 'history'
  historyFilter.value = filter
  keyboard.value = false
}
function rememberCareScroll() {
  if (!isCareOverview.value) return
  careScroll = careList.value?.scrollTop || 0
  overviewScroll = workspace.value?.scrollTop || 0
}
function restoreCareScroll() {
  if (isCareOverview.value && careList.value) careList.value.scrollTop = careScroll
  if (workspace.value) workspace.value.scrollTop = isCareOverview.value ? overviewScroll : 0
}
function returnToQuestion() {
  emit('stop')
  const original = message.value?.originalQuestion || item.value?.question || ''
  messageFloor.value = props.message?.id || 0
  emit('reset')
  typed.value = original
  keyboard.value = true
}
function viewRecord(record) {
  const value = maintenanceCatalog.find((item) => item.recordId === record.item)
  if (value) selectItem(value)
}
function back() {
  emit('stop')
  emit('reset')
  keyboard.value = false
  typed.value = ''
  if (mode.value === 'conversation')
    mode.value = item.value?.recordId ? 'item' : 'browse'
  else if (mode.value === 'history')
    mode.value = item.value?.recordId ? 'item' : 'browse'
  else if (mode.value === 'item') {
    mode.value = itemReturnMode.value
    groupId.value = itemReturnGroup.value
    itemId.value = null
  } else {
    groupId.value = null
    itemId.value = null
  }
}
function startFreeConversation() {
  if (mode.value !== 'conversation') {
    emit('reset')
    messageFloor.value = props.message?.id || 0
    mode.value = 'conversation'
  }
}
function toggleVoice() {
  keyboard.value = false
  startFreeConversation()
  emit('voice')
}
function toggleKeyboard() {
  emit('stop')
  keyboard.value = !keyboard.value
}
function send() {
  if (!typed.value.trim() || props.asking) return
  startFreeConversation()
  emit('question', typed.value.trim())
  typed.value = ''
  keyboard.value = false
}
function onEnter(event) {
  if (!event.isComposing) {
    event.preventDefault()
    send()
  }
}
watch(
  [categoryId, itemId],
  () =>
    emit(
      'context',
      item.value ? { ...item.value, category: categoryId.value } : null,
    ),
  { immediate: true },
)
watch(
  () => props.vehicle?.id,
  () => {
    if (props.message?.status === 'need_vehicle' || props.asking) return
    groupId.value = null
    itemId.value = null
    mode.value = 'browse'
    careScroll = 0
    overviewScroll = 0
    emit('reset')
  },
)
</script>
<template>
  <main
    ref="workspace"
    class="care-workspace"
    :class="{ 'is-care-overview': isCareOverview, 'is-conclusion': isConclusion }"
    :data-category="categoryId"
    :data-mode="mode"
    :data-focused="Boolean(focus)"
    aria-label="차량 안내"
  >
    <section v-if="categoryId !== 'controls'" class="vehicle-context">
      <div v-if="categoryId !== 'maintenance'" class="context-heading">
        <h1>
          {{
            categoryId === 'warning'
                ? '차가 보내는 신호'
                : categoryId === 'controls'
                  ? '내 차와 친해지기'
                  : '도로 위에서'
          }}
        </h1>
        <span>{{
          vehicle
            ? `${vehicle.nickname || vehicle.model} · ${vehicle.model_year}`
            : '차량을 선택해 주세요'
        }}</span>
      </div>
      <div v-else class="care-odometer"><span>주행거리</span><strong>{{ vehicle?.mileage_km == null ? '미입력' : number(vehicle.mileage_km) }}<small v-if="vehicle?.mileage_km != null">km</small></strong></div>
      <RoadContext v-if="categoryId === 'rules'" />
      <VehicleStructure
        v-else
        :focus="focus"
        :contextual="!message?.warningId"
        :intro="intro"
        :maintenance-tones="categoryId === 'maintenance' ? vehicleTones : undefined"
        :selected-tone="categoryId === 'maintenance' && activeItem?.recordId && mode !== 'history' ? usageState(selectedUsage).tone : undefined"
        @introduced="emit('introduced')"
      />
      <div v-if="categoryId === 'maintenance'" class="care-urgent-parts">
        <div class="care-urgent-heading">교환 임박<span v-if="urgentParts.length">{{ urgentParts.length }}</span></div>
        <div v-if="urgentParts.length" class="care-urgent-items"><button v-for="usage in urgentParts" :key="usage.item.id" :disabled="asking" @click="selectItem(usage.item)"><i />{{ usage.item.label }}</button></div>
        <span v-else class="care-urgent-empty">{{ loading ? '기록 확인 중' : error ? '기록을 불러오지 못했어요' : !records.length ? '교환 기록을 남겨 주세요' : '현재 교환 임박 항목이 없어요' }}</span>
      </div>
      <div v-else class="context-caption">
        <GuideIcon :name="category.icon" :size="21" /><span>{{
          category.subtitle
        }}</span>
      </div>
      <span v-if="categoryId !== 'maintenance' && activeItem && mode !== 'history'" class="context-selection">{{
        activeItem.label
      }}</span>
    </section>
    <section class="care-panel" :class="{ 'care-overview-panel': isCareOverview }" aria-label="단계별 맞춤 안내">
      <div v-if="hasCareTabs" class="care-section-bar">
        <nav class="care-section-tabs" aria-label="관리 화면 선택">
          <button :class="{ active: isCareOverview }" :aria-pressed="isCareOverview" @click="showOverview">소모품 관리</button>
          <button :class="{ active: mode === 'history' }" :aria-pressed="mode === 'history'" @click="openHistory()">정비 기록<span v-if="records.length">{{ records.length }}</span></button>
        </nav>
        <button v-if="vehicle" class="care-add-record" :disabled="loading || Boolean(error)" @click="emit('add-record', mode === 'history' && historyFilter !== 'all' ? historyFilter : undefined)"><Plus :size="17" />기록 추가</button>
        <button v-else class="care-add-record" @click="emit('vehicle')">내 차 선택</button>
      </div>
      <header v-else class="care-heading" :class="{ 'conclusion-heading': isConclusion }">
        <button
          v-if="hasBack && !isConclusion"
          class="guide-back"
          :disabled="asking"
          aria-label="이전 단계"
          @click="back"
        >
          <ArrowLeft :size="20" />
        </button>
        <div>
          <span v-if="group || mode === 'history'" class="care-breadcrumb"
            >{{ category.label
            }}<template v-if="mode === 'item' || mode === 'conversation'">
              / {{ group?.label || '상황 확인' }}</template
            ></span
          >
          <span v-if="isConclusion" class="care-breadcrumb">안내 결과</span>
          <h2>{{ header }}</h2>
        </div>
      </header>
      <Transition name="guide-stage" mode="out-in" @after-enter="restoreCareScroll">
        <div
          :key="stageKey"
          class="care-stage"
          :class="{ 'conversation-stage': mode === 'conversation', 'care-overview-stage': isCareOverview, 'item-stage': mode === 'item' }"
        >
          <template v-if="mode === 'history'">
            <div class="history-tools">
              <select v-model="historyFilter" aria-label="정비 이력 필터">
                <option value="all">전체 항목</option>
                <option
                  v-for="option in maintenanceItems"
                  :key="option.id"
                  :value="option.id"
                >
                  {{ option.label }}
                </option></select><span>{{ history.length }}건</span>
            </div>
            <div v-if="loading" class="stage-empty">
              정비 기록을 불러오고 있어요.
            </div>
            <div v-else-if="error" class="stage-empty">
              <p>{{ error }}</p>
              <button class="text-button" @click="emit('reload-records')">
                다시 불러오기
              </button>
            </div>
            <div v-else-if="!history.length" class="stage-empty">
              <History :size="30" />
              <p>아직 남긴 기록이 없어요.</p>
              <span>교환한 날짜와 주행거리를 남겨 주세요.</span>
            </div>
            <div v-else class="care-history-list">
              <article
                v-for="record in history"
                :key="record._key || record.id"
              >
                <time class="history-date">{{ date(record.performed_at) }}</time>
                <span class="history-entry-copy"><strong>{{ recordName(record) }}<span>{{ number(record.mileage_km) }} km</span></strong><small v-if="record.memo">{{ record.memo }}</small></span>
                <button v-if="maintenanceCatalog.some(part => part.recordId === record.item)" class="history-part-link" :aria-label="`${recordName(record)} 관리 보기`" @click="viewRecord(record)"><ArrowRight :size="20" /></button>
              </article>
            </div>
          </template>
          <template v-else-if="mode === 'item'">
            <div class="item-introduction">
              <span class="item-symbol"
                ><GuideIcon :name="item.icon" :size="27"
              /></span>
              <p>{{ item.description }}</p>
            </div>
            <div class="item-usage-card">
              <div v-if="selectedUsage.intervalSource === 'manual'" class="usage-conditions"><span>운행 기준 비교</span><button :class="{ selected: condition === 'normal' }" @click="condition = 'normal'">일반 운행</button><button :class="{ selected: condition === 'severe' }" @click="condition = 'severe'">가혹 운행</button></div>
              <div v-else-if="selectedUsage.intervalSource === 'demo'" class="usage-demo-label">시연 관리 기준</div>
              <MaintenanceUsage :usage="selectedUsage" />
              <div class="usage-record-note"><span>등록된 주행거리·교환 기록 기준</span><button v-if="selectedRecord" @click="openHistory(item.recordId)">교환 기록 보기<ChevronRight :size="13" /></button><button v-else-if="error" @click="emit('reload-records')">다시 불러오기</button></div>
            </div>
            <div class="item-actions">
              <button
                class="care-primary"
                :disabled="asking || loading"
                @click="consult()"
              >
                점검·교환 시기 알아보기<ArrowUpRight :size="20" /></button
              ><button
                class="care-secondary"
                :disabled="!vehicle || loading || Boolean(error)"
                @click="emit('add-record', item.recordId)"
              >
                <Plus :size="18" />교환 기록 남기기
              </button>
            </div>
          </template>
          <template v-else-if="mode === 'conversation'">
            <div v-if="asking" class="guide-thinking" role="status">
              <span class="thinking-dot" />차량 정보와 설명서를 확인하고 있어요
            </div>
            <div v-else-if="!message" class="conversation-invitation">
              <span class="listening-orb"><Mic :size="30" /></span>
              <h3>
                {{
                  voiceState.phase === 'listening'
                    ? '듣고 있어요'
                    : '어떤 상황인지 이야기해 주세요'
                }}
              </h3>
              <p>
                {{
                  voiceState.transcript || '정확한 부품 이름을 몰라도 괜찮아요.'
                }}
              </p>
            </div>
            <template v-else>
              <div class="answer-heading">
                <span v-if="message.evidenceLabel" class="guide-evidence">{{
                  message.evidenceLabel
                }}</span
                ><span v-else class="guide-evidence">{{
                  message.followup_question
                    ? '조금만 더 알려 주세요'
                    : '차근의 안내'
                }}</span
                ><button
                  v-if="message.speech_text || message.followup_question"
                  class="answer-listen"
                  :aria-label="message.followup_question ? '질문 듣기' : '답변 듣기'"
                  @click="emit('speak', message)"
                >
                  <Volume2 :size="19" />
                </button>
              </div>
              <h3>
                {{
                  message.followup_question || message.title || '확인한 내용'
                }}
              </h3>
              <p v-if="message.answer" class="guide-answer">
                {{ message.answer }}
              </p>
              <div v-if="message.facts?.length" class="guide-facts">
                <div v-for="fact in message.facts" :key="fact.label">
                  <span>{{ fact.label }}</span
                  ><strong>{{ fact.value }}</strong>
                </div>
              </div>
              <div
                v-if="message.status === 'need_vehicle'"
                class="guide-options"
              >
                <button
                  v-for="car in vehicles"
                  :key="car.id"
                  @click="emit('choose-vehicle', car.id)"
                >
                  {{ car.nickname || car.model }} · {{ car.model_year
                  }}<ChevronRight :size="18" /></button
                ><button v-if="!vehicles?.length" @click="emit('vehicle')">
                  차량 선택<ChevronRight :size="18" />
                </button>
              </div>
              <div v-if="message.suggestions?.length" class="guide-options">
                <button
                  v-for="option in message.suggestions"
                  :key="option"
                  @click="emit('reply', option)"
                >
                  {{ option }}<ChevronRight :size="18" />
                </button>
              </div>
              <div
                v-if="!message.followup_question"
                class="guide-result-actions"
              >
                <button
                  v-if="message.sources?.length"
                  @click="emit('source', message)"
                >
                  <BookOpen :size="17" />근거·상세</button
                ><button
                  v-if="message.action?.type === 'open_my_car'"
                  @click="openHistory(message.action.item || 'all')"
                >
                  <History :size="17" />관련 정비 기록</button
                ><button
                  v-if="message.retryFlow"
                  @click="emit('retry', message)"
                >
                  <RotateCcw :size="17" />다시 시도
                </button>
              </div>
            </template>
          </template>
          <template v-else-if="group">
            <p class="stage-caption">{{ group.detail }}</p>
            <div class="care-topic-list">
              <button
                v-for="topic in visibleTopics"
                :key="topic.id"
                :disabled="asking"
                @click="selectItem(topic)"
              >
                <span class="topic-symbol"
                  ><GuideIcon
                    :name="topic.icon || group.icon"
                    :size="23" /></span
                ><span
                  ><strong>{{ topic.label }}</strong
                  ><small v-if="topic.recordId">{{
                    loading
                      ? '기록 확인 중'
                      : error
                        ? '기록 확인 필요'
                        : overview.find((item) => item.id === topic.id)?.record
                          ? `마지막 교환 ${date(overview.find((item) => item.id === topic.id).record.performed_at)}`
                          : '교환 기록 없음'
                  }}</small
                  ></span
                ><ChevronRight :size="19" />
              </button>
            </div>
          </template>
          <template v-else-if="categoryId === 'maintenance'">
            <div ref="careList" class="maintenance-list" aria-label="교환 우선순 소모품 목록">
              <MaintenanceCard v-for="usage in priorities" :key="usage.item.id" :usage="usage" :disabled="asking" @select="selectItem" />
            </div>
          </template>
          <template v-else-if="categoryId === 'warning'">
            <p class="stage-caption">
              눈에 보이거나 느껴지는 변화부터 골라 주세요.
            </p>
            <div class="symptom-grid">
              <button
                v-for="topic in category.topics"
                :key="topic.id"
                :disabled="asking"
                @click="selectItem(topic)"
              >
                <GuideIcon :name="topic.icon" :size="24" /><span
                  ><strong>{{ topic.label }}</strong
                  ><small>{{ topic.description }}</small></span
                ><ChevronRight :size="16" />
              </button>
            </div>
          </template>
          <template v-else-if="categoryId === 'controls'">
            <div class="controls-grid">
              <section
                v-for="entry in category.groups"
                :key="entry.id"
                class="control-family"
                :aria-label="entry.label"
              >
                <header><GuideIcon :name="entry.icon" :size="29" /><h3>{{ entry.label }}</h3></header>
                <button
                  v-for="topic in category.topics.filter(topic => topic.group === entry.id)"
                  :key="topic.id"
                  :disabled="asking"
                  @click="selectItem(topic)"
                ><span>{{ topic.label }}</span><ArrowRight :size="19" /></button>
              </section>
            </div>
          </template>
          <template v-else>
            <p class="stage-caption">
              상황을 고르면 적용되는 조건부터 확인해요.
            </p>
            <div class="road-scenarios">
              <button
                v-for="(entry, index) in category.groups"
                :key="entry.id"
                :disabled="asking"
                @click="selectGroup(entry)"
              >
                <span class="scenario-number">0{{ index + 1 }}</span
                ><GuideIcon :name="entry.icon" :size="23" /><span
                  ><strong>{{ entry.label }}</strong
                  ><small>{{ entry.detail }}</small></span
                ><ChevronRight :size="18" />
              </button>
            </div>
          </template>
        </div>
      </Transition>
      <footer v-if="isConclusion" class="conclusion-actions">
        <button class="conclusion-return" @click="returnToQuestion"><MessageCircle :size="18" />질문으로 돌아가기</button>
      </footer>
      <footer v-else-if="mode === 'conversation'" class="care-voice-bar">
        <form v-if="keyboard" class="guide-text-input" @submit.prevent="send">
          <input
            v-model="typed"
            maxlength="500"
            aria-label="추가 설명 입력"
            placeholder="궁금한 점이나 상황을 이야기해 주세요"
            @keydown.enter="onEnter"
          /><button
            :disabled="asking || !typed.trim()"
            aria-label="설명 보내기"
          >
            <ArrowUp :size="20" />
          </button>
        </form>
        <template v-else
          ><button
            class="guide-mic"
            :class="{ active: voiceActive }"
            :disabled="asking && !voiceActive"
            @click="toggleVoice"
          >
            <Square v-if="voiceActive" :size="16" /><Mic v-else :size="20" />{{
              voiceLabel
            }}</button
          ><span class="guide-transcript" role="status">{{
            voiceState.error || voiceState.transcript
          }}</span></template
        >
        <button
          class="guide-keyboard"
          :aria-label="keyboard ? '글 입력 닫기' : '글로 답하기'"
          @click="toggleKeyboard"
        >
          <Keyboard :size="20" />
        </button>
      </footer>
    </section>
  </main>
</template>
