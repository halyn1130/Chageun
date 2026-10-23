<script setup>
import { computed, nextTick, ref, watch, onBeforeUnmount } from 'vue'
import {
  ArrowRight,
  ArrowUp,
  BookOpen,
  CarFront,
  Check,
  ChevronDown,
  CircleAlert,
  ExternalLink,
  House,
  LogIn,
  LogOut,
  Moon,
  Mic,
  Plus,
  RotateCcw,
  Sun,
  Square,
  Volume2,
  Wrench,
} from 'lucide-vue-next'
import DialogSheet from './components/DialogSheet.vue'
import VoiceControl from './components/VoiceControl.vue'
import VoiceOrb from './components/VoiceOrb.vue'
import DiagnosticView from './components/DiagnosticView.vue'
import WarningSymbol from './components/WarningSymbol.vue'
import GuidanceMenu from './components/GuidanceMenu.vue'
import BrandLogo from './components/BrandLogo.vue'
import { createVoiceSession } from './voiceSession.js'
import { spokenReply, isHomeCommand } from './spokenReply.js'
import { contextualOptions } from './conversation.js'
import { useChageun } from './composables/useChageun.js'

const {
  screen,
  panel,
  theme,
  apiHealth,
  user,
  authOpen,
  authMode,
  authBusy,
  authError,
  authForm,
  toastText,
  vehicles,
  catalog,
  selectedVehicleId,
  chatVehicleId,
  maintenance,
  maintenanceFilter,
  carFormOpen,
  maintenanceFormOpen,
  carForm,
  maintenanceForm,
  formBusy,
  messages,
  question,
  asking,
  pendingQuestion,
  activePromptId,
  chatBody,
  maintenanceItems,
  selectedVehicle,
  chatVehicle,
  visibleMaintenance,
  lastOil,
  currentMessage,
  hasConversation,
  maintenanceLoading,
  maintenanceError,
  loadMaintenance,
  askMaintenance,
  today,
  formatNumber,
  dateLabel,
  itemLabel,
  isMockSource,
  go,
  toggleTheme,
  returnHome,
  cancelQuestion,
  selectVehicle,
  saveCar,
  deleteCar,
  openMaintenanceForm,
  openCarFromAnswer,
  saveMaintenance,
  vehicleLabel,
  chooseChatVehicle,
  replyTo: continueReply,
  ask,
  retryQuestion,
  submitAuth,
  signOut,
} = useChageun()

const keyboardOpen = ref(false)
const questionInput = ref(null)
const mobileQuery = window.matchMedia('(max-width: 700px)')
const isMobile = ref(mobileQuery.matches)
function updateMobile(event) { isMobile.value = event.matches }
mobileQuery.addEventListener('change', updateMobile)
const headerVehicle = computed(() =>
  screen.value === 'assistant' ? chatVehicle.value : selectedVehicle.value,
)
const diagnosticEntry = ref({})
const diagnosticMode = ref('browse')
const diagnosticVersion = ref(0)
const vehicleIntroShown = ref(false)
const guidedContext = ref(null)
const voiceState = ref({
  phase: 'idle',
  active: false,
  transcript: '',
  error: '',
})
const composerVisible = computed(() => keyboardOpen.value || (hasConversation.value && (isMobile.value || !voiceState.value.active)))
const voice = createVoiceSession({
  platform: window,
  onChange: (state) => {
    voiceState.value = state
  },
  onQuestion: async (text) => {
    if (isHomeCommand(text)) {
      goHome()
      await nextTick()
      voice.read('대화를 마치고 홈으로 돌아왔어요.')
      return ''
    }
    const before = currentMessage.value?.id
    await askInContext(text)
    if (currentMessage.value?.id === before)
      return '질문을 조금 더 설명해 주세요.'
    return spokenReply(currentMessage.value)
  },
})
async function askInContext(text) {
  const context =
    screen.value === 'diagnostics' && !pendingQuestion.value
      ? contextualOptions(text, guidedContext.value)
      : {}
  await ask(text, context)
}
function toggleVoice() {
  keyboardOpen.value = false
  if (voiceState.value.active || voiceState.value.phase === 'speaking')
    voice.stop()
  else voice.start()
}
async function toggleKeyboard() {
  voice.stop()
  keyboardOpen.value = !keyboardOpen.value
  if (isMobile.value && keyboardOpen.value) {
    await nextTick()
    questionInput.value?.focus()
  }
}
async function replyTo(message, text) {
  voice.stop()
  await continueReply(message, text)
}
function goHome() {
  voice.stop()
  keyboardOpen.value = false
  guidedContext.value = null
  diagnosticEntry.value = {}
  diagnosticVersion.value++
  returnHome()
}
function navigate(next) {
  if (next === 'diagnostics') {
    diagnosticEntry.value = { category: 'maintenance' }
    diagnosticVersion.value++
  }
  voice.stop()
  keyboardOpen.value = false
  go(next)
}
function openDiagnostic() {
  navigate('diagnostics')
  diagnosticEntry.value = {
    category:
      currentMessage.value?.category ||
      (currentMessage.value?.warningId ? 'warning' : 'maintenance'),
    topic: currentMessage.value?.topicId,
    answer: true,
  }
}
function openGuidance(selection) {
  if (asking.value) return
  const entry =
    typeof selection === 'string' ? { category: selection } : selection
  cancelQuestion()
  navigate('diagnostics')
  diagnosticEntry.value = entry
}
function showRecords(message) {
  openGuidance({
    category: 'maintenance',
    view: 'history',
    recordFilter: message?.action?.item || 'all',
  })
}
function addRecord(itemId) {
  voice.stop()
  openMaintenanceForm()
  if (itemId) maintenanceForm.value.item = itemId
}
function openLogin() {
  panel.value = null
  authOpen.value = true
}
async function beginConsultation(item) {
  voice.stop()
  cancelQuestion()
  chatVehicleId.value = selectedVehicleId.value
  await ask(item.question, {
    newQuestion: true,
    surface: isMobile.value ? 'assistant' : undefined,
    category: item.category,
    topicId: item.id,
    intent:
      item.intent ||
      (item.category === 'maintenance'
        ? 'maintenance'
        : item.category === 'controls'
          ? 'controls'
          : item.category === 'rules'
            ? 'rules'
            : undefined),
    recordItem: item.recordId,
  })
}
async function guidedReply(text) {
  voice.stop()
  if (currentMessage.value) await continueReply(currentMessage.value, text)
  else await ask(text)
}
function resetGuidance() {
  voice.stop()
  if (!asking.value) cancelQuestion()
}
function showSources(message) {
  panel.value = { sourceId: message.id }
}
function playSpeech(message) {
  voice.read(spokenReply(message))
}
async function sendTyped() {
  voice.stop()
  if (isHomeCommand(question.value)) {
    goHome()
    return
  }
  await ask()
}
watch(screen, (next) => {
  voice.stop()
})
watch(isMobile, mobile => {
  if (mobile && screen.value === 'diagnostics' && diagnosticMode.value === 'conversation') go('assistant')
})
watch([panel, carFormOpen, maintenanceFormOpen, authOpen], (values) => {
  if (values.some(Boolean)) voice.stop()
})
function pauseOnHide() {
  if (document.hidden) voice.stop()
}
document.addEventListener('visibilitychange', pauseOnHide)
onBeforeUnmount(() => {
  mobileQuery.removeEventListener('change', updateMobile)
  voice.stop()
  document.removeEventListener('visibilitychange', pauseOnHide)
})
const sourceMessage = computed(
  () =>
    messages.value.find((message) => message.id === panel.value?.sourceId) ||
    currentMessage.value,
)
function onEnter(event) {
  if (!event.isComposing && !event.shiftKey) {
    event.preventDefault()
    sendTyped()
  }
}
async function pickCar(id) {
  voice.stop()
  panel.value = null
  await chooseChatVehicle(id)
}
function openCarRegistration() {
  panel.value = null
  carFormOpen.value = true
}
function switchAuthMode() {
  authMode.value = authMode.value === 'login' ? 'signup' : 'login'
  authError.value = ''
}
</script>

<template>
  <div class="chageun" :data-theme="theme">
    <header class="app-header">
      <BrandLogo />
      <div class="header-actions">
        <button
          class="vehicle-button"
          :disabled="asking"
          @click="panel = 'vehicles'"
        >
          <CarFront :size="19" /><span>{{ headerVehicle ? headerVehicle.nickname || headerVehicle.model : '차량 선택' }}</span><ChevronDown :size="14" />
        </button>
        <button
          class="icon-button theme-button"
          :aria-label="
            theme === 'dark' ? '밝은 화면으로 전환' : '어두운 화면으로 전환'
          "
          @click="toggleTheme"
        >
          <Sun v-if="theme === 'dark'" :size="21" /><Moon v-else :size="20" />
        </button>
      </div>
    </header>

    <template v-if="screen === 'assistant'">
      <main
        class="voice-workspace"
        :class="{
          'is-conversation': hasConversation,
          'keyboard-open': composerVisible,
        }"
      >
        <VoiceControl
          :state="voiceState"
          :compact="hasConversation"
          :keyboard-open="composerVisible"
          :busy="asking"
          @toggle="toggleVoice"
          @keyboard="toggleKeyboard"
        />
        <section v-if="!hasConversation" class="home-tools">
          <GuidanceMenu
            :busy="asking"
            @select="openGuidance"
          />
        </section>
        <div v-else class="conversation-pane">
          <div
            ref="chatBody"
            class="chat-thread"
            role="log"
            aria-label="차근과의 대화"
            aria-live="polite"
          >
            <article
              v-for="message in messages.filter(
                (item) => item.status !== 'welcome',
              )"
              :key="message.id"
              class="chat-message"
              :class="message.role"
            >
              <span class="chat-speaker">{{
                message.role === 'user' ? '나' : '차근'
              }}</span>
              <div class="chat-content">
                <p v-if="message.role === 'user'" class="chat-user-text">
                  {{ message.answer }}
                </p>
                <template v-else>
                  <div class="mobile-chat-reply">
                    <p>{{ spokenReply(message) }}</p>
                    <div v-if="message.sources?.some(source => !isMockSource(source))" class="mobile-message-sources">
                      <BookOpen :size="12" /><span>{{ [...new Set(message.sources.filter(source => !isMockSource(source)).map(source => source.title))].join(' · ') }}</span>
                    </div>
                  </div>
                  <h2 v-if="message.followup_question">
                    {{ message.followup_question }}
                  </h2>
                  <p
                    v-if="message.answer"
                    :class="
                      message.followup_question
                        ? 'answer-support'
                        : 'answer-text'
                    "
                  >
                    {{ message.answer }}
                  </p>
                  <div v-if="message.facts?.length" class="guide-facts">
                    <div v-for="fact in message.facts" :key="fact.label">
                      <span>{{ fact.label }}</span
                      ><strong>{{ fact.value }}</strong>
                    </div>
                  </div>
                  <template v-if="message.id === currentMessage?.id && !asking">
                    <div
                      v-if="message.status === 'need_vehicle'"
                      class="answer-options vehicle-options"
                    >
                      <button
                        v-for="car in vehicles"
                        :key="car.id"
                        @click="pickCar(car.id)"
                      >
                        <CarFront :size="21" /><span
                          >{{ car.nickname || `${car.manufacturer} ${car.model}` }}<small
                            >{{ car.model }} · {{ car.model_year }} · {{ car.powertrain }}</small
                          ></span
                        ><ArrowRight :size="18" />
                      </button>
                      <button
                        v-if="!vehicles.length"
                        @click="carFormOpen = true"
                      >
                        <Plus :size="20" /> 차량 등록
                      </button>
                    </div>
                    <div
                      v-if="message.suggestions?.length"
                      class="answer-options"
                      :class="{
                        'single-option': message.suggestions.length === 1,
                      }"
                    >
                      <button
                        v-for="suggestion in message.suggestions"
                        :key="suggestion"
                        :disabled="
                          message.localFlow && activePromptId !== message.id
                        "
                        @click="replyTo(message, suggestion)"
                      >
                        <span>{{ suggestion }}</span
                        ><ArrowRight :size="17" />
                      </button>
                    </div>
                    <div
                      v-if="message.details?.length"
                      class="collected-details"
                    >
                      <span v-for="detail in message.details" :key="detail">{{
                        detail
                      }}</span>
                    </div>
                  </template>
                  <button
                    v-if="message.warningId"
                    class="answer-diagnostic-link"
                    @click="openDiagnostic(message.warningId)"
                  >
                    <WarningSymbol
                      :type="message.warningId"
                      :size="23"
                    />차량에서 관련 부위 보기<ArrowRight :size="16" />
                  </button>
                  <div
                    v-if="
                      message.sources?.length ||
                      message.action ||
                      message.retryFlow ||
                      message.speech_text ||
                      message.followup_question
                    "
                    class="answer-actions"
                  >
                    <button
                      v-if="
                        message.sources?.some((source) => !isMockSource(source))
                      "
                      class="text-button"
                      @click="panel = { sourceId: message.id }"
                    >
                      <BookOpen :size="18" />근거 보기
                    </button>
                    <button
                      v-if="message.action?.type === 'open_my_car'"
                      class="text-button"
                      @click="showRecords(message)"
                    >
                      <Wrench :size="18" />정비 기록 보기
                      <ArrowRight :size="17" />
                    </button>
                    <button
                      v-if="message.retryFlow"
                      class="text-button"
                      :disabled="asking"
                      @click="retryQuestion(message)"
                    >
                      <RotateCcw :size="17" />다시 시도
                    </button>
                    <button
                      v-if="message.speech_text || message.followup_question"
                      class="text-button"
                      @click="playSpeech(message)"
                    >
                      <Volume2 :size="18" />{{ message.followup_question ? '질문 듣기' : '답변 듣기' }}
                    </button>
                  </div>
                </template>
              </div>
            </article>
            <div v-if="asking" class="chat-message assistant" role="status">
              <span class="chat-speaker">차근</span>
              <div class="answer-loading" aria-label="답변 확인 중">
                <span /><span /><span />
              </div>
            </div>
          </div>
        </div>
        <div v-if="isMobile && hasConversation && (asking || voiceState.active || voiceState.phase === 'speaking')" class="mobile-voice-feedback">
          <VoiceOrb :phase="asking && !voiceState.active ? 'thinking' : voiceState.phase" />
          <p class="mobile-chat-status" role="status">{{ voiceState.transcript || (asking ? '답변을 준비하고 있어요' : { listening: '듣고 있어요', connecting: '마이크 연결 중', thinking: '답변을 준비하고 있어요', speaking: '차근이 답하고 있어요' }[voiceState.phase]) }}</p>
        </div>
        <p v-else-if="isMobile && hasConversation && voiceState.error" class="mobile-chat-status" role="status">{{ voiceState.error }}</p>
        <form
          v-if="composerVisible"
          class="question-composer voice-text-composer"
          @submit.prevent="sendTyped"
        >
          <textarea
            ref="questionInput"
            v-model="question"
            rows="1"
            maxlength="500"
            aria-label="차근에게 질문하기"
            :placeholder="pendingQuestion ? '답을 적어 주세요' : hasConversation ? '이어서 물어보세요' : '궁금한 것을 적어 주세요'"
            @keydown.enter="onEnter"
            @focus="isMobile && voice.stop()"
          />
          <button
            v-if="hasConversation"
            class="mobile-composer-mic"
            type="button"
            :class="{ active: voiceState.active || voiceState.phase === 'speaking' }"
            :aria-label="voiceState.active || voiceState.phase === 'speaking' ? '음성 대화 멈추기' : '이어서 말하기'"
            :disabled="asking && !voiceState.active"
            @click="toggleVoice"
          ><Square v-if="voiceState.active || voiceState.phase === 'speaking'" :size="18" /><Mic v-else :size="22" /></button>
          <button
            class="submit-question"
            type="submit"
            :disabled="asking || !question.trim()"
            aria-label="질문 보내기"
          >
            <ArrowUp :size="23" />
          </button>
        </form>
        <p v-if="apiHealth === 'offline'" class="voice-offline" role="status">
          서버 연결을 확인해 주세요.
        </p>
      </main>
    </template>

    <DiagnosticView
      v-else
      :key="diagnosticVersion"
      :vehicle="selectedVehicle"
      :records="maintenance"
      :loading="maintenanceLoading"
      :error="maintenanceError"
      :entry="diagnosticEntry"
      :message="currentMessage"
      :asking="asking"
      :voice-state="voiceState"
      :vehicles="vehicles"
      :intro="!vehicleIntroShown"
      @introduced="vehicleIntroShown = true"
      @add-record="addRecord"
      @reload-records="loadMaintenance(selectedVehicleId)"
      @consult="beginConsultation"
      @reply="guidedReply"
      @question="askInContext"
      @context="guidedContext = $event"
      @voice="toggleVoice"
      @stop="voice.stop()"
      @source="showSources"
      @vehicle="panel = 'vehicles'"
      @choose-vehicle="pickCar"
      @retry="retryQuestion"
      @speak="playSpeech"
      @reset="resetGuidance"
      @mode="diagnosticMode = $event"
    />

    <nav class="app-nav" aria-label="주 메뉴">
      <button
        :class="{
          active:
            screen === 'assistant' ||
            (screen === 'diagnostics' &&
              diagnosticEntry.category &&
              diagnosticEntry.category !== 'maintenance'),
        }"
        :title="hasConversation ? '대화를 마치고 홈으로' : '홈'"
        @click="goHome"
      >
        <House :size="20" :stroke-width="1.6" /><span>홈</span>
      </button>
      <button
        :class="{
          active:
            screen !== 'assistant' &&
            (!diagnosticEntry.category ||
              diagnosticEntry.category === 'maintenance'),
        }"
        :disabled="asking"
        @click="openGuidance('maintenance')"
      >
        <CarFront :size="21" :stroke-width="1.6" /><span>내 차 케어</span>
      </button>
    </nav>

    <DialogSheet
      :open="panel === 'vehicles'"
      title="어떤 차를 타고 있나요?"
      :eyebrow="screen === 'assistant' ? '답변에 사용할 차량' : '확인할 차량'"
      @close="panel = null"
    >
      <p class="sheet-description">
        차종과 연식에 따라 버튼 위치와 정비 기준이 달라요.
      </p>
      <div class="vehicle-list">
        <button
          v-for="car in vehicles"
          :key="car.id"
          :class="{ selected: headerVehicle?.id === car.id }"
          @click="pickCar(car.id)"
        >
          <CarFront :size="27" /><span
            ><strong>{{ car.nickname || `${car.manufacturer} ${car.model}` }}</strong
            ><small>{{ car.model }} · {{ car.model_year }} · {{ car.powertrain }}</small></span
          ><Check v-if="headerVehicle?.id === car.id" :size="20" /><ArrowRight
            v-else
            :size="19"
          />
        </button>
      </div>
      <div class="vehicle-settings-account">
        <span>{{ user ? `${user.username}님` : '내 차 계정' }}</span>
        <button v-if="user" class="text-button" @click="signOut">
          <LogOut :size="16" />로그아웃
        </button>
        <button
          v-else
          class="text-button"
          @click="openLogin"
        >
          <LogIn :size="16" />로그인
        </button>
        <button v-if="headerVehicle" class="quiet-button" @click="deleteCar">
          차량 삭제
        </button>
      </div>
      <div class="sheet-footer">
        <button class="text-button" @click="openCarRegistration">
          <Plus :size="18" />차량 등록</button
        ><button class="quiet-button" @click="pickCar(null)">
          선택하지 않기
        </button>
      </div>
    </DialogSheet>

    <DialogSheet
      :open="Boolean(panel?.sourceId)"
      title="답변의 근거"
      @close="panel = null"
      ><div v-if="sourceMessage?.details?.length" class="source-context">
        <h3>확인한 정보</h3>
        <p v-for="detail in sourceMessage.details" :key="detail">
          {{ detail }}
        </p>
      </div>
      <div class="source-list">
        <a
          v-for="source in sourceMessage?.sources?.filter(
            (item) => !isMockSource(item),
          )"
          :key="source.url"
          :href="source.url"
          target="_blank"
          rel="noopener noreferrer"
          ><BookOpen :size="23" /><span
            ><strong>{{ source.title }}</strong
            ><small>{{ source.page }}</small></span
          ><ExternalLink :size="17"
        /></a></div
    ></DialogSheet>

    <DialogSheet
      :open="carFormOpen"
      title="내 차 등록"
      @close="carFormOpen = false"
      ><form class="detail-form" @submit.prevent="saveCar">
        <label
          >차종<select v-model="carForm.catalogIndex">
            <option v-for="(car, index) in catalog" :key="index" :value="index">
              {{ car.manufacturer }} {{ car.model }} · {{ car.model_year }} ·
              {{ car.powertrain }}
            </option>
          </select></label
        ><label
          >별명 <span>선택</span
          ><input
            v-model="carForm.nickname"
            maxlength="50"
            placeholder="예: 내 첫 차" /></label
        ><label
          >주행거리 <span>선택 · km</span
          ><input
            v-model="carForm.mileage_km"
            type="number"
            min="0"
            step="1"
            placeholder="0" /></label
        ><button
          class="primary-button"
          type="submit"
          :disabled="formBusy || !catalog.length"
        >
          {{ formBusy ? '등록 중…' : '차량 등록' }}<ArrowRight :size="18" />
        </button></form
    ></DialogSheet>

    <DialogSheet
      :open="maintenanceFormOpen"
      title="정비 기록 추가"
      @close="maintenanceFormOpen = false"
      ><form class="detail-form" @submit.prevent="saveMaintenance">
        <label
          >정비 항목<select v-model="maintenanceForm.item">
            <option
              v-for="item in maintenanceItems"
              :key="item.id"
              :value="item.id"
            >
              {{ item.label }}
            </option>
          </select></label
        >
        <div class="form-columns">
          <label
            >정비한 날짜<input
              v-model="maintenanceForm.performed_at"
              type="date"
              :max="today()"
              required /></label
          ><label
            >주행거리 <span>km</span
            ><input
              v-model="maintenanceForm.mileage_km"
              type="number"
              min="0"
              step="1"
              required
          /></label>
        </div>
        <label
          >메모 <span>선택</span
          ><input
            v-model="maintenanceForm.memo"
            maxlength="255"
            placeholder="예: 엔진오일과 필터 교환" /></label
        ><button class="primary-button" type="submit" :disabled="formBusy">
          {{ formBusy ? '저장 중…' : '기록 추가' }}<ArrowRight :size="18" />
        </button></form
    ></DialogSheet>

    <DialogSheet
      :open="authOpen"
      :title="authMode === 'login' ? '로그인' : '계정 만들기'"
      @close="authOpen = false"
      ><form class="detail-form" @submit.prevent="submitAuth">
        <BrandLogo class="auth-brand" />
        <label
          >아이디<input
            v-model="authForm.username"
            required
            autocomplete="username" /></label
        ><label
          >비밀번호<input
            v-model="authForm.password"
            type="password"
            required
            :autocomplete="
              authMode === 'login' ? 'current-password' : 'new-password'
            "
        /></label>
        <p v-if="authError" class="form-error" role="alert">{{ authError }}</p>
        <button class="primary-button" type="submit" :disabled="authBusy">
          {{
            authBusy
              ? '확인 중…'
              : authMode === 'login'
                ? '로그인'
                : '회원가입'
          }}<ArrowRight :size="18" /></button
        ><button class="quiet-button" type="button" @click="switchAuthMode">
          {{
            authMode === 'login'
              ? '처음이신가요? 계정 만들기'
              : '이미 계정이 있어요'
          }}
        </button>
      </form></DialogSheet
    >

    <div v-if="toastText" class="toast" role="status">
      <CircleAlert :size="18" /><span>{{ toastText }}</span>
    </div>
  </div>
</template>
