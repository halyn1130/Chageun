import { resolvePreparedGuide, keepPreparedEligibility } from '../preparedGuides.js'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api, checkAuth, login, logout, signup } from '../api.js'
import { buildRagRequest, resolveRagResponse, describeRecordAction } from '../ragConversation.js'
import { maintenanceItems, findGuideTopic } from '../guidance.js'
import {
  clarificationFor,
  continueQuestion,
  isNewQuestion,
  findSpokenVehicle,
  localBoundary,
  questionDetails,
  startQuestion,
} from '../conversation.js'

export function useChageun() {
  const screen = ref('assistant')
  const panel = ref(null)
  const theme = ref(localStorage.getItem('chageun-theme') || 'dark')
  const apiHealth = ref('checking')
  const user = ref(null)
  const authOpen = ref(false)
  const authMode = ref('login')
  const authBusy = ref(false)
  const authError = ref('')
  const authForm = ref({ username: '', password: '' })
  const toastText = ref('')
  let toastTimer

  const vehicles = ref([])
  const catalog = ref([])
  const selectedVehicleId = ref(null)
  const chatVehicleId = ref(null)
  const maintenance = ref([])
  const maintenanceLoading = ref(false)
  const maintenanceError = ref('')
  // Cache server-owned records for the current signed-in account.
  const maintenanceCache = new Map()
  const maintenanceRequests = new Map()
  let accountRevision = 0
  let recordKey = 0
  const maintenanceFilter = ref('all')
  const carFormOpen = ref(false)
  const maintenanceFormOpen = ref(false)
  const carForm = ref({ catalogIndex: 0, nickname: '', mileage_km: '' })
  const maintenanceForm = ref({
    item: 'engine_oil',
    performed_at: today(),
    mileage_km: '',
    memo: '',
  })
  const formBusy = ref(false)

  const messages = ref([
    {
      id: 1,
      role: 'assistant',
      status: 'welcome',
      answer:
        '안녕하세요, 차근이에요. 차 안 버튼이 헷갈리거나 계기판에 낯선 불이 켜졌나요? 편하게 설명해 주세요. 내 차 설명서와 도로 규칙에서 근거를 찾아드릴게요.',
      sources: [],
      speech_text: '',
    },
  ])
  const question = ref('')
  const asking = ref(false)
  const conversationId = ref(null)
  let questionRevision = 0
  let activeRequest = null
  const pendingQuestion = ref(null)
  const activePromptId = ref(null)
  const clarificationHistory = ref([])
  const canReturnToPreviousStep = computed(() => clarificationHistory.value.length > 0 && !asking.value)
  function rememberClarification(id) {
    clarificationHistory.value.push(JSON.parse(JSON.stringify({
      flow: pendingQuestion.value,
      message: messages.value.find(message => message.id === id),
    })))
  }
  function returnToPreviousStep() {
    if (!canReturnToPreviousStep.value) return
    const previous = JSON.parse(JSON.stringify(clarificationHistory.value.at(-1)))
    questionRevision++
    activeRequest?.abort()
    activeRequest = null
    question.value = ''
    // Start a fresh server branch; the restored flow carries only earlier answers.
    conversationId.value = null
    pendingQuestion.value = previous.flow
    activePromptId.value = appendMessage(previous.message)
  }
  const chatBody = ref(null)
  let messageId = 1
  watch(
    () => [messages.value.length, asking.value, screen.value],
    async () => {
      await nextTick()
      if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
    },
  )

  const selectedVehicle = computed(
    () =>
      vehicles.value.find((car) => car.id === selectedVehicleId.value) || null,
  )
  const chatVehicle = computed(
    () => vehicles.value.find((car) => car.id === chatVehicleId.value) || null,
  )
  const visibleMaintenance = computed(() =>
    maintenanceFilter.value === 'all'
      ? maintenance.value
      : maintenance.value.filter(
          (item) => item.item === maintenanceFilter.value,
        ),
  )
  const lastOil = computed(
    () => maintenance.value.find((item) => item.item === 'engine_oil') || null,
  )

  function today() {
    const date = new Date()
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  }
  function formatNumber(value) {
    return new Intl.NumberFormat('ko-KR').format(value || 0)
  }
  function dateLabel(value) {
    return value ? value.replaceAll('-', '.') : '날짜 미입력'
  }
  function itemLabel(item) {
    return maintenanceItems.find((entry) => entry.id === item)?.label || item
  }
  function isMockSource(source) {
    return (
      !/^https?:\/\//.test(source.url || '') || /example\.com/.test(source.url)
    )
  }

  function notify(message) {
    toastText.value = message
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
      toastText.value = ''
    }, 4200)
  }
  function showError(error) {
    notify(error?.message || '요청을 처리하지 못했어요.')
    if (error?.status === 401) authOpen.value = true
  }
  function go(next) {
    screen.value = ['car', 'diagnostics'].includes(next) ? next : 'assistant'
    panel.value = null
    if (['car', 'diagnostics'].includes(next) && selectedVehicleId.value)
      loadMaintenance(selectedVehicleId.value)
  }
  function showAssistant() {
    screen.value = 'assistant'
    panel.value = null
  }
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem('chageun-theme', theme.value)
  }
  function returnHome() {
    cancelQuestion()
    messages.value = [messages.value[0]]
    go('assistant')
  }
  function apiVehicleId(id) {
    return vehicles.value.find((car) => car.id === id)?._apiId ?? id
  }
  function orderedRecords(records) {
    return [...records].sort(
      (a, b) =>
        b.performed_at.localeCompare(a.performed_at) ||
        b.mileage_km - a.mileage_km,
    )
  }

  async function loadCars() {
    const revision = accountRevision
    try {
      const [carList, carCatalog, profile] = await Promise.all([
        api('/vehicles'),
        api('/vehicles/catalog'),
        api('/settings/profile').catch(() => null),
      ])
      if (revision !== accountRevision) return
      if (profile && user.value) user.value.display_name = profile.display_name
      vehicles.value = carList || []
      catalog.value = carCatalog || []
      chatVehicleId.value =
        vehicles.value.find((car) => car.is_primary)?.id ?? null
      if (
        !selectedVehicleId.value ||
        !vehicles.value.some((car) => car.id === selectedVehicleId.value)
      ) {
        selectedVehicleId.value = vehicles.value[0]?.id || null
      }
      if (selectedVehicleId.value)
        await loadMaintenance(selectedVehicleId.value)
    } catch (error) {
      showError(error)
    }
  }
  async function loadMaintenance(vehicleId) {
    const revision = accountRevision
    maintenanceError.value = ''
    if (maintenanceCache.has(vehicleId)) {
      if (selectedVehicleId.value === vehicleId) {
        maintenance.value = maintenanceCache.get(vehicleId)
        maintenanceLoading.value = false
      }
      return
    }
    if (selectedVehicleId.value === vehicleId) {
      maintenance.value = []
      maintenanceLoading.value = true
    }
    try {
      if (!maintenanceRequests.has(vehicleId)) {
        maintenanceRequests.set(
          vehicleId,
          api(`/vehicles/${apiVehicleId(vehicleId)}/maintenance`),
        )
      }
      const records = ((await maintenanceRequests.get(vehicleId)) || []).map(
        (record) => ({ ...record, _key: ++recordKey }),
      )
      if (revision !== accountRevision) return
      const sorted = orderedRecords(records)
      maintenanceCache.set(vehicleId, sorted)
      if (selectedVehicleId.value === vehicleId) maintenance.value = sorted
    } catch (error) {
      if (revision === accountRevision && selectedVehicleId.value === vehicleId) {
        maintenance.value = []
        maintenanceError.value = '정비 기록을 불러오지 못했어요.'
      }
      showError(error)
    } finally {
      if (revision !== accountRevision) return
      maintenanceRequests.delete(vehicleId)
      if (selectedVehicleId.value === vehicleId)
        maintenanceLoading.value = false
    }
  }
  async function selectVehicle(id) {
    selectedVehicleId.value = id
    maintenanceFilter.value = 'all'
    await loadMaintenance(id)
  }
  async function saveCar() {
    const chosen = catalog.value[Number(carForm.value.catalogIndex)]
    if (!chosen) return
    formBusy.value = true
    try {
      const car = await api('/vehicles', {
        method: 'POST',
        body: {
          ...chosen,
          nickname: carForm.value.nickname.trim() || null,
          mileage_km:
            carForm.value.mileage_km === ''
              ? null
              : Number(carForm.value.mileage_km),
        },
      })
      const created = car
      vehicles.value = [...vehicles.value, created]
      selectedVehicleId.value = created.id
      maintenanceCache.set(created.id, [])
      maintenance.value = []
      maintenanceFilter.value = 'all'
      maintenanceError.value = ''
      maintenanceLoading.value = false
      carFormOpen.value = false
      carForm.value = { catalogIndex: 0, nickname: '', mileage_km: '' }
      if (pendingQuestion.value?.awaiting === 'vehicle')
        await chooseChatVehicle(created.id)
      else {
        chatVehicleId.value = created.id
        screen.value = 'diagnostics'
      }
      notify('내 차량을 등록했어요.')
    } catch (error) {
      showError(error)
    } finally {
      formBusy.value = false
    }
  }
  async function deleteCar() {
    if (
      !selectedVehicle.value ||
      !window.confirm(
        `${selectedVehicle.value.nickname || selectedVehicle.value.model} 차량과 이 차량의 정비 기록을 모두 삭제할까요? 삭제 후에는 복구할 수 없어요.`,
      )
    )
      return
    try {
      const deletingId = selectedVehicleId.value
      await api(`/vehicles/${apiVehicleId(deletingId)}`, { method: 'DELETE' })
      if (chatVehicleId.value === deletingId) await chooseChatVehicle(null)
      maintenanceCache.delete(deletingId)
      vehicles.value = vehicles.value.filter((car) => car.id !== deletingId)
      selectedVehicleId.value = vehicles.value[0]?.id || null
      maintenance.value = []
      if (selectedVehicleId.value)
        await loadMaintenance(selectedVehicleId.value)
      notify('차량과 해당 정비 기록을 삭제했어요.')
    } catch (error) {
      showError(error)
    }
  }
  function openMaintenanceForm() {
    maintenanceForm.value = {
      item: 'engine_oil',
      performed_at: today(),
      mileage_km: selectedVehicle.value?.mileage_km ?? '',
      memo: '',
    }
    maintenanceFormOpen.value = true
  }
  async function saveMaintenance() {
    if (!selectedVehicleId.value) return
    const vehicleId = selectedVehicleId.value
    formBusy.value = true
    try {
      const record = await api(
        `/vehicles/${apiVehicleId(vehicleId)}/maintenance`,
        {
          method: 'POST',
          body: {
            item: maintenanceForm.value.item,
            performed_at: maintenanceForm.value.performed_at,
            mileage_km: Number(maintenanceForm.value.mileage_km),
            memo: maintenanceForm.value.memo.trim() || null,
          },
        },
      )
      const records = orderedRecords([
        { ...record, _key: ++recordKey },
        ...(maintenanceCache.get(vehicleId) || []),
      ])
      maintenanceCache.set(vehicleId, records)
      if (selectedVehicleId.value === vehicleId) maintenance.value = records
      const car = vehicles.value.find(entry => entry.id === vehicleId)
      if (car && (car.mileage_km == null || record.mileage_km > car.mileage_km)) car.mileage_km = record.mileage_km
      maintenanceFilter.value = 'all'
      maintenanceFormOpen.value = false
      notify('교환 기록을 저장했어요. 관리 화면에도 반영했어요.')
    } catch (error) {
      showError(error)
    } finally {
      formBusy.value = false
    }
  }

  function appendMessage(message) {
    const entry = { ...message, id: ++messageId }
    messages.value.push(entry)
    return entry.id
  }
  function vehicleLabel(car) {
    return car
      ? `${car.manufacturer} ${car.model} · ${car.model_year} · ${car.powertrain}`
      : '차량 미지정'
  }
  function cancelQuestion() {
    questionRevision++
    activeRequest?.abort()
    activeRequest = null
    asking.value = false
    pendingQuestion.value = null
    clarificationHistory.value = []
    activePromptId.value = null
    conversationId.value = null
    question.value = ''
  }
  async function chooseChatVehicle(id) {
    if (asking.value) return
    chatVehicleId.value = id
    conversationId.value = null
    selectedVehicleId.value = id
    if (id != null) {
      await loadMaintenance(id)
    } else maintenance.value = []
    if (pendingQuestion.value) {
      const flow = {
        ...pendingQuestion.value,
        vehicleId: id,
        vehicleResolved: id != null,
        vehicleNote: undefined,
      }
      if (flow.awaiting === 'vehicle' && id != null) {
        appendMessage({
          role: 'user',
          answer: `${vehicleLabel(chatVehicle.value)} 기준으로 알려줘`,
        })
        await continueOrSend(flow)
      } else pendingQuestion.value = flow
    }
  }
  async function continueOrSend(flow) {
    const revision = questionRevision
    asking.value = true
    if (flow.vehicleId != null && flow.category !== 'controls') await loadMaintenance(flow.vehicleId)
    if (revision !== questionRevision) return
    const records = maintenanceCache.get(flow.vehicleId) || []
    const guideTopic = findGuideTopic(flow.topicId, flow.category)
    flow = {
      ...flow,
      recordItem: flow.recordItem || guideTopic?.recordId,
      lastOil: records.find((record) => record.item === 'engine_oil'),
      lastService: records.find(
        (record) => record.item === (flow.recordItem || guideTopic?.recordId),
      ),
    }
    activePromptId.value = null
    const prompt = clarificationFor(flow)
    if (prompt) {
      pendingQuestion.value = { ...flow, awaiting: prompt.field }
      activePromptId.value = appendMessage({
        role: 'assistant',
        status: prompt.status || 'need_details',
        answer: prompt.answer,
        followup_question: prompt.question,
        suggestions: prompt.suggestions,
        clarificationField: prompt.field,
        localFlow: true,
        topicId: flow.topicId,
        category: flow.category,
        vehicleLabel:
          flow.vehicleId != null ? vehicleLabel(chatVehicle.value) : null,
      })
      rememberClarification(activePromptId.value)
      asking.value = false
      return
    }
    pendingQuestion.value = null
    const usedVehicle = vehicles.value.find(vehicle => vehicle.id === flow.vehicleId)
    const prepared = resolvePreparedGuide(flow, usedVehicle)
    if (prepared) {
      conversationId.value = null
      appendMessage({ role: 'assistant', ...prepared, originalQuestion: flow.original,
        topicId: flow.topicId, category: flow.category,
        vehicleLabel: usedVehicle ? vehicleLabel(usedVehicle) : null,
        details: [...questionDetails(flow), ...prepared.details] })
      asking.value = false
      return
    }
    await sendQuestion(flow)
  }
  async function replyTo(message, text) {
    if (
      (message.localFlow || message.serverFlow) &&
      message.id !== activePromptId.value
    )
      return
    await ask(text, {
      newQuestion: !message.localFlow && !message.serverFlow,
      followup: Boolean(message.localFlow || message.serverFlow),
    })
  }
  async function ask(text = question.value, options = {}) {
    const clean = text.trim()
    if (!clean || asking.value) return
    if (clean.length > 500) {
      notify('질문은 500자 이내로 입력해 주세요.')
      return
    }
    if (clean.length < 2 && !pendingQuestion.value) {
      notify('질문을 조금 더 설명해 주세요.')
      return
    }
    question.value = ''
    appendMessage({ role: 'user', answer: clean })
    if (options.surface === 'assistant' || screen.value !== 'diagnostics')
      showAssistant()
    const boundary = localBoundary(clean)
    if (boundary) {
      cancelQuestion()
      appendMessage({ role: 'assistant', ...boundary, sources: [] })
      return
    }
    const pending = pendingQuestion.value
    if (pending?.awaiting === 'vehicle' && !options.newQuestion && !isNewQuestion(clean, pending)) {
      const car = findSpokenVehicle(clean, vehicles.value)
      if (car) {
        chatVehicleId.value = car.id
        selectedVehicleId.value = car.id
        conversationId.value = null
        await continueOrSend({ ...pending, vehicleId: car.id, vehicleResolved: true, vehicleNote: undefined, awaiting: null })
        return
      }
      if (vehicles.value.length && !/모르|정보\s*없이|선택\s*안|건너뛰/.test(clean)) {
        await continueOrSend(pending)
        return
      }
    }
    if (
      pending &&
      !options.newQuestion &&
      (options.followup || !isNewQuestion(clean, pending))
    ) {
      const prompt = messages.value.find(message => message.id === activePromptId.value)
      await continueOrSend({ ...continueQuestion(pending, clean),
        preparedEligible: keepPreparedEligibility(pending, prompt, clean) })
    } else {
      if (pending || options.newQuestion) cancelQuestion()
      await continueOrSend({
        ...startQuestion(clean, chatVehicleId.value),
        preparedEligible: options.preparedMenu === true,
        ...(options.category ? { category: options.category } : {}),
        ...(options.topicId ? { topicId: options.topicId } : {}),
        ...(options.recordItem ? { recordItem: options.recordItem } : {}),
        ...(options.contextLabel ? { contextLabel: options.contextLabel } : {}),
        ...(options.intent ? { intent: options.intent } : {}),
      })
    }
  }
  async function askMaintenance() {
    if (asking.value) return
    cancelQuestion()
    chatVehicleId.value = selectedVehicleId.value
    await ask('내 차 엔진오일은 언제 교환해야 해?', {
      newQuestion: true,
      surface: 'assistant',
    })
  }
  async function openCarFromAnswer(message) {
    const id = message.action?.vehicle_id
    if (!vehicles.value.some((car) => car.id === id)) {
      notify('이 차량은 현재 등록되어 있지 않아요.')
      return
    }
    selectedVehicleId.value = id
    maintenanceFilter.value = message.action.item || 'all'
    go('car')
  }
  async function sendQuestion(flow) {
    const revision = questionRevision
    const controller = new AbortController()
    activeRequest = controller
    asking.value = true
    const usedVehicle = vehicles.value.find((car) => car.id === flow.vehicleId)
    const context = {
      originalQuestion: flow.original,
      vehicleLabel: usedVehicle ? vehicleLabel(usedVehicle) : null,
      details: questionDetails(flow),
      topicId: flow.topicId,
      category: flow.category,
    }
    try {
      if (flow.vehicleId != null && flow.category !== 'controls') await loadMaintenance(flow.vehicleId)
      if (revision !== questionRevision) return
      const records = maintenanceCache.get(flow.vehicleId)
      const rawResult = await api('/rag-query', {
        method: 'POST',
        signal: controller.signal,
        body: buildRagRequest(flow, {
          vehicle: usedVehicle,
          records,
          vehicleId:
            flow.vehicleId != null ? apiVehicleId(flow.vehicleId) : null,
          conversationId: conversationId.value,
        }),
      })
      if (revision !== questionRevision) return
      const result = resolveRagResponse(flow, rawResult, {
        vehicle: usedVehicle,
        records,
        now: today(),
      })
      conversationId.value =
        rawResult.conversation_id === 'c_mock'
          ? null
          : rawResult.conversation_id || conversationId.value
      if (
        (result.action && result.action.type !== 'open_my_car') ||
        result.status === 'need_location'
      ) {
        appendMessage({
          role: 'assistant',
          status: 'out_of_scope',
          answer:
            '차근에서는 차량 조작, 경고등, 소모품 관리와 도로 규칙을 도와드려요. 장소 검색은 지원하지 않아요.',
          sources: [],
        })
      } else {
        const serverFlow =
          result.status === 'need_details' && Boolean(result.followup_question)
        const id = appendMessage({
          role: 'assistant',
          ...result,
          ...context,
          recordSummary: describeRecordAction(result, { vehicle: usedVehicle, records }),
          details: [...context.details, ...(result.details || [])],
          serverFlow,
        })
        if (serverFlow) {
          pendingQuestion.value = {
            ...flow,
            awaiting: 'server',
            serverFollowup: true,
            serverQuestion: result.followup_question,
          }
          activePromptId.value = id
          rememberClarification(id)
        }
        if (result.action?.type === 'open_my_car' && flow.vehicleId != null) {
          selectedVehicleId.value = flow.vehicleId
          maintenanceFilter.value = result.action.item || 'all'
          await loadMaintenance(flow.vehicleId)
        }
      }
    } catch (error) {
      if (revision !== questionRevision || error.name === 'AbortError') return
      appendMessage({
        role: 'assistant',
        status: 'error',
        ...context,
        answer: error.message || '잠시 후 다시 시도해 주세요.',
        sources: [],
        retryFlow: flow,
      })
      if (error.status === 401) authOpen.value = true
    } finally {
      if (revision === questionRevision) {
        asking.value = false
        activeRequest = null
      }
    }
  }
  async function retryQuestion(message) {
    if (asking.value) return
    await sendQuestion(message.retryFlow)
  }
  async function submitAuth() {
    if (!authForm.value.username.trim() || !authForm.value.password) return
    authBusy.value = true
    authError.value = ''
    try {
      if (authMode.value === 'signup') {
        await signup(authForm.value.username.trim(), authForm.value.password)
        authMode.value = 'login'
        authForm.value.password = ''
        notify('계정을 만들었어요. 이제 로그인해 주세요.')
      } else {
        await login(authForm.value.username.trim(), authForm.value.password)
        user.value = (await checkAuth()) || {
          username: authForm.value.username.trim(),
        }
        authOpen.value = false
        authForm.value.password = ''
        clearAccountData()
        await loadCars()
        notify(`${user.value.display_name || user.value.username}님, 반가워요.`)
      }
    } catch (error) {
      authError.value = error.message
    } finally {
      authBusy.value = false
    }
  }
  async function signOut() {
    await logout()
    user.value = null
    clearAccountData()
    notify('로그아웃했어요.')
  }
  function onUnauthorized() {
    user.value = null
    clearAccountData()
    authOpen.value = true
    notify('로그인이 만료됐어요. 다시 로그인해 주세요.')
  }
  function clearAccountData() {
    accountRevision++
    vehicles.value = []
    maintenance.value = []
    selectedVehicleId.value = null
    chatVehicleId.value = null
    maintenanceCache.clear()
    maintenanceRequests.clear()
    maintenanceError.value = ''
    maintenanceLoading.value = false
    cancelQuestion()
    messages.value = [messages.value[0]]
  }

  onMounted(async () => {
    window.addEventListener('chageun:unauthorized', onUnauthorized)
    const results = await Promise.allSettled([
      loadCars(),
      checkAuth(),
      api('/health'),
    ])
    if (results[1].status === 'fulfilled') user.value = results[1].value
    apiHealth.value =
      results[2].status === 'fulfilled' && results[2].value?.status === 'ok'
        ? 'online'
        : 'offline'
  })
  onBeforeUnmount(() => {
    cancelQuestion()
    window.removeEventListener('chageun:unauthorized', onUnauthorized)
    clearTimeout(toastTimer)
  })

  const currentMessage = computed(() =>
    [...messages.value]
      .reverse()
      .find(
        (message) =>
          message.role === 'assistant' && message.status !== 'welcome',
      ),
  )
  const hasConversation = computed(() =>
    messages.value.some((message) => message.role === 'user'),
  )
  return {
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
    maintenanceLoading,
    maintenanceError,
    loadMaintenance,
    askMaintenance,
    chatVehicle,
    visibleMaintenance,
    lastOil,
    currentMessage,
    hasConversation,
    today,
    formatNumber,
    dateLabel,
    itemLabel,
    isMockSource,
    go,
    toggleTheme,
    returnHome,
    selectVehicle,
    saveCar,
    deleteCar,
    openMaintenanceForm,
    openCarFromAnswer,
    saveMaintenance,
    vehicleLabel,
    cancelQuestion,
    canReturnToPreviousStep,
    returnToPreviousStep,
    chooseChatVehicle,
    replyTo,
    ask,
    retryQuestion,
    submitAuth,
    signOut,
  }
}
