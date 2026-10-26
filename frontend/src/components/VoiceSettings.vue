<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { CarFront, Check, ChevronDown, LogOut, Palette, Play, Plus, Square, UserRound, Volume2 } from 'lucide-vue-next'
import DialogSheet from './DialogSheet.vue'
import { api, getToken } from '../api.js'
import { createRemoteSpeech } from '../remoteSpeech.js'

const props = defineProps({
  vehicles: { type: Array, default: () => [] },
  initialVehicleId: { type: Number, default: null },
  saveMileage: { type: Function, required: true },
  theme: { type: String, default: 'dark' },
})
const emit = defineEmits(['close', 'register', 'theme', 'saved', 'logout'])
const themes = [{ id: 'light', name: '밝게' }, { id: 'dark', name: '다크' }, { id: 'black', name: '블랙' }]
const vehicleId = ref(props.initialVehicleId)
const currentVehicle = computed(() => props.vehicles.find(car => car.id === vehicleId.value))
const mileage = ref('')
const mileageBusy = ref(false)
const mileageError = ref('')
const mileageMessage = ref('')
const mileageChanged = computed(() => currentVehicle.value && String(mileage.value) !== String(currentVehicle.value.mileage_km ?? ''))
const number = value => new Intl.NumberFormat('ko-KR').format(value)

watch(() => props.vehicles.map(car => car.id), ids => {
  if (!ids.includes(vehicleId.value)) vehicleId.value = props.vehicles.find(car => car.is_primary)?.id ?? ids[0] ?? null
}, { immediate: true })
watch(() => [currentVehicle.value?.id, currentVehicle.value?.mileage_km], () => {
  mileage.value = currentVehicle.value?.mileage_km ?? ''
  mileageError.value = ''
  mileageMessage.value = ''
}, { immediate: true })

const loaded = ref(false)
const loading = ref(true)
const voices = ref([])
const selected = ref(null)
const savedVoice = ref(null)
const voiceBusy = ref(false)
const voiceError = ref('')
const voiceMessage = ref('')
const playing = ref(null)
const voiceOptions = computed(() => [{ name: '기본 목소리', voice_id: null }, ...voices.value])
let alive = true
const requests = new AbortController()
const preview = createRemoteSpeech({ platform: window, getToken, getVoice: () => playing.value === 'default' ? null : playing.value })
const displayName = ref('')
const primaryVehicleId = ref(null)
const savedProfile = ref(null)
const profileBusy = ref(false)
const profileError = ref('')
const profileMessage = ref('')
const profileChanged = computed(() => savedProfile.value && (displayName.value.trim() !== savedProfile.value.display_name || primaryVehicleId.value !== savedProfile.value.vehicle_id))
const profileCarName = computed(() => props.vehicles.find(car => car.id === savedProfile.value?.vehicle_id)?.nickname || props.vehicles.find(car => car.id === savedProfile.value?.vehicle_id)?.model)

async function loadProfile() {
  profileError.value = ''
  try {
    const profile = await api('/settings/profile', { signal: requests.signal })
    if (!alive) return
    savedProfile.value = profile
    displayName.value = profile.display_name
    primaryVehicleId.value = profile.vehicle_id
  } catch (error) {
    if (alive) profileError.value = error.message
  }
}
async function saveProfile() {
  if (profileBusy.value || voiceBusy.value || !loaded.value || !savedProfile.value) return
  profileBusy.value = true
  profileError.value = ''
  profileMessage.value = ''
  try {
    const saved = await api('/settings/profile', {
      method: 'PUT',
      body: { display_name: displayName.value.trim(), vehicle_id: primaryVehicleId.value, voice_id: savedVoice.value },
      signal: requests.signal,
    })
    if (!alive) return
    savedProfile.value = saved
    displayName.value = saved.display_name
    vehicleId.value = saved.vehicle_id
    profileMessage.value = '이름과 기본 차량을 저장했어요.'
    emit('saved', { ...saved, vehicles: props.vehicles })
  } catch (error) {
    if (alive) profileError.value = error.message
  } finally {
    if (alive) profileBusy.value = false
  }
}
onMounted(loadProfile)

async function loadVoices() {
  loading.value = true
  voiceError.value = ''
  try {
    const [catalog, saved] = await Promise.all([
      api('/settings/voices', { signal: requests.signal }),
      api('/settings/voice', { signal: requests.signal }),
    ])
    if (!alive) return
    voices.value = catalog
    selected.value = saved.voice_id
    savedVoice.value = saved.voice_id
    loaded.value = true
  } catch (error) {
    if (alive) voiceError.value = error.message
  } finally {
    if (alive) loading.value = false
  }
}
onMounted(loadVoices)

async function submitMileage() {
  if (mileageBusy.value || !currentVehicle.value) return
  mileageError.value = ''
  mileageMessage.value = ''
  const value = String(mileage.value).trim()
  if (!/^\d+$/.test(value) || Number(value) > 4294967295) {
    mileageError.value = '주행거리는 0부터 4,294,967,295 사이의 정수로 입력해 주세요.'
    return
  }
  mileageBusy.value = true
  try {
    const saved = await props.saveMileage(vehicleId.value, Number(value), { signal: requests.signal })
    if (alive && saved) {
      mileage.value = saved.mileage_km
      mileageMessage.value = `${number(saved.mileage_km)} km로 저장했어요.`
    }
  } catch (error) {
    if (alive) mileageError.value = error.message
  } finally {
    if (alive) mileageBusy.value = false
  }
}
function stopPreview() {
  preview.stop()
  playing.value = null
}
function listen(id) {
  const key = id ?? 'default'
  if (playing.value === key) return stopPreview()
  voiceError.value = ''
  playing.value = key
  preview.speak('안녕하세요. 차근입니다. 차량에 대해 궁금한 점을 편하게 말씀해 주세요.', {
    onEnd: () => { playing.value = null },
    onError: error => { playing.value = null; voiceError.value = error },
  })
}
function chooseVoice() {
  voiceMessage.value = ''
  voiceError.value = ''
  stopPreview()
}
async function saveVoice() {
  if (voiceBusy.value || profileBusy.value || !loaded.value || selected.value === savedVoice.value) return
  voiceBusy.value = true
  voiceError.value = ''
  voiceMessage.value = ''
  stopPreview()
  try {
    const saved = await api('/settings/voice', {
      method: 'PUT', body: { voice_id: selected.value }, signal: requests.signal,
    })
    if (alive) {
      savedVoice.value = saved.voice_id
      voiceMessage.value = '저장했어요. 다음 음성 안내부터 적용돼요.'
    }
  } catch (error) {
    if (alive) voiceError.value = error.message
  } finally {
    if (alive) voiceBusy.value = false
  }
}
onBeforeUnmount(() => { alive = false; requests.abort(); stopPreview() })
</script>

<template>
  <DialogSheet :open="true" title="개인 설정" @close="emit('close')">
    <div class="personal-settings">
      <details class="profile-settings">
        <summary><UserRound :size="18" aria-hidden="true" /><span>프로필<small>{{ savedProfile ? [savedProfile.display_name, profileCarName].filter(Boolean).join(' · ') : '이름 · 기본 차량' }}</small></span><ChevronDown :size="18" aria-hidden="true" /></summary>
        <form v-if="savedProfile" @submit.prevent="saveProfile">
          <fieldset :disabled="profileBusy || voiceBusy || !loaded">
            <label class="settings-field">이름<input v-model="displayName" required maxlength="50" autocomplete="nickname" placeholder="사용할 이름" @input="profileMessage = ''" /></label>
            <label v-if="vehicles.length" class="settings-field">기본 차량
              <select v-model="primaryVehicleId" required @change="profileMessage = ''">
                <option v-for="car in vehicles" :key="car.id" :value="car.id">{{ car.nickname || car.model }} · {{ car.model }} {{ car.model_year }}</option>
              </select>
            </label>
            <button type="button" class="quiet-button" @click="emit('register')">차량 등록하기</button>
            <button type="submit" class="secondary-button profile-save" :disabled="!profileChanged">{{ profileBusy ? '저장 중…' : '프로필 저장' }}</button>
          </fieldset>
        </form>
        <p v-else-if="!profileError" class="settings-hint" role="status">프로필을 불러오는 중이에요.</p>
        <p v-if="profileError" class="settings-error" role="alert">{{ profileError }}</p>
        <button v-if="profileError && !savedProfile" type="button" class="quiet-button" @click="loadProfile">다시 불러오기</button>
        <p v-if="profileMessage" class="settings-success" role="status"><Check :size="15" aria-hidden="true" />{{ profileMessage }}</p>
      </details>
      <section class="settings-section" aria-labelledby="vehicle-settings-title">
        <h3 id="vehicle-settings-title"><CarFront :size="18" aria-hidden="true" />내 차량</h3>
        <form v-if="currentVehicle" @submit.prevent="submitMileage">
          <fieldset :disabled="mileageBusy" class="mileage-fields">
            <label v-if="vehicles.length > 1" class="settings-field">
              차량 선택
              <select v-model="vehicleId">
                <option v-for="car in vehicles" :key="car.id" :value="car.id">{{ car.nickname || car.model }} · {{ car.model }} {{ car.model_year }}</option>
              </select>
            </label>
            <div v-else class="vehicle-summary">
              <strong>{{ currentVehicle.nickname || currentVehicle.model }}</strong>
              <span>{{ currentVehicle.manufacturer }} {{ currentVehicle.model }} · {{ currentVehicle.model_year }}</span>
            </div>
            <label for="settings-mileage" class="field-label">현재 주행거리</label>
            <div class="mileage-editor">
              <div class="mileage-input">
                <input id="settings-mileage" v-model="mileage" type="text" inputmode="numeric" pattern="[0-9]+" maxlength="10" required autocomplete="off" placeholder="0" aria-describedby="mileage-hint" :aria-invalid="mileageError ? true : undefined" @input="mileageMessage = ''; mileageError = ''" />
                <span aria-hidden="true">km</span>
              </div>
              <button type="submit" class="mileage-save" :disabled="!mileageChanged">{{ mileageBusy ? '저장 중…' : '주행거리 저장' }}</button>
            </div>
          </fieldset>
          <p id="mileage-hint" class="settings-hint">계기판의 누적 주행거리를 입력해 주세요.</p>
          <p v-if="mileageError" class="settings-error" role="alert">{{ mileageError }}</p>
          <p v-if="mileageMessage" class="settings-success" role="status"><Check :size="15" aria-hidden="true" />{{ mileageMessage }}</p>
        </form>
        <div v-else class="settings-empty">
          <p>주행거리를 관리할 차량을 등록해 주세요.</p>
          <button type="button" class="secondary-button" @click="emit('register')"><Plus :size="16" aria-hidden="true" />차량 등록</button>
        </div>
      </section>

      <section class="settings-section divided-section" aria-labelledby="theme-settings-title">
        <h3 id="theme-settings-title"><Palette :size="18" aria-hidden="true" />화면 테마</h3>
        <fieldset class="theme-options" aria-label="화면 테마 선택">
          <label v-for="option in themes" :key="option.id" class="theme-choice" :class="{ chosen: theme === option.id }" :data-preview-theme="option.id">
            <input type="radio" name="settings-theme" :value="option.id" :checked="theme === option.id" @change="emit('theme', option.id)" />
            <span class="theme-preview" aria-hidden="true"><span></span><span></span><span></span></span>
            <span class="theme-name">{{ option.name }}<Check v-if="theme === option.id" :size="14" aria-hidden="true" /></span>
          </label>
        </fieldset>
      </section>

      <section class="settings-section divided-section voice-section" aria-labelledby="voice-settings-title">
        <h3 id="voice-settings-title"><Volume2 :size="18" aria-hidden="true" />안내 목소리</h3>
        <p class="settings-hint">미리 듣고 마음에 드는 목소리를 골라보세요.</p>
        <p v-if="loading" class="settings-hint" role="status">목소리를 불러오는 중이에요.</p>
        <form v-if="loaded" @submit.prevent="saveVoice">
          <fieldset class="voice-settings" :disabled="voiceBusy || profileBusy" aria-label="안내 목소리 선택">
            <div class="voice-grid">
              <div v-for="v in voiceOptions" :key="v.voice_id ?? 'default'" class="voice-card" :class="{ chosen: selected === v.voice_id }">
                <label class="voice-choice">
                  <input v-model="selected" type="radio" name="voice-choice" :value="v.voice_id" @change="chooseVoice" />
                  <span>{{ v.name }}</span>
                </label>
                <button type="button" class="voice-preview" :aria-label="`${v.name} ${playing === (v.voice_id ?? 'default') ? '미리 듣기 중지' : '미리 듣기'}`" :aria-pressed="playing === (v.voice_id ?? 'default')" @click="listen(v.voice_id)">
                  <Square v-if="playing === (v.voice_id ?? 'default')" :size="14" aria-hidden="true" />
                  <Play v-else :size="14" aria-hidden="true" />
                  {{ playing === (v.voice_id ?? 'default') ? '듣기 중지' : '미리 듣기' }}
                </button>
              </div>
            </div>
            <button type="submit" class="primary-button voice-save" :disabled="selected === savedVoice">{{ voiceBusy ? '저장 중…' : '목소리 적용' }}</button>
          </fieldset>
        </form>
        <p v-if="voiceError" class="settings-error" role="alert">{{ voiceError }}</p>
        <button v-if="!loaded && !loading" type="button" class="secondary-button" @click="loadVoices">다시 불러오기</button>
        <p v-if="voiceMessage" class="settings-success" role="status"><Check :size="15" aria-hidden="true" />{{ voiceMessage }}</p>
      </section>
      <button type="button" class="settings-logout" :disabled="mileageBusy || voiceBusy || profileBusy" @click="emit('logout')"><LogOut :size="16" aria-hidden="true" />로그아웃</button>
    </div>
  </DialogSheet>
</template>

<style scoped>
.personal-settings { padding-top: 6px; }
.profile-settings { padding-bottom: 18px; margin-bottom: 22px; border-bottom: 1px solid var(--line-strong); }
.profile-settings summary { display: flex; align-items: center; gap: 9px; min-height: 44px; cursor: pointer; list-style: none; font-size: 15px; font-weight: 600; }
.profile-settings summary::-webkit-details-marker { display: none; }
.profile-settings summary > svg:first-child { color: var(--accent); }
.profile-settings summary > svg:last-child { margin-left: auto; color: var(--secondary); }
.profile-settings[open] summary > svg:last-child { transform: rotate(180deg); }
.profile-settings summary small { display: block; margin-top: 5px; color: var(--secondary); font-size: 12px; font-weight: 400; }
.profile-settings form { padding-top: 18px; }
.profile-save { width: 100%; }
.settings-logout { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; min-height: 48px; margin-top: 24px; padding-top: 12px; border: 0; border-top: 1px solid var(--line-strong); background: none; color: var(--secondary); font-size: 13px; }
.settings-section h3 { display: flex; align-items: center; gap: 9px; margin: 0 0 16px; font-size: 15px; font-weight: 600; }
.settings-section h3 svg { color: var(--accent); }
fieldset { min-width: 0; margin: 0; padding: 0; border: 0; }
.vehicle-summary { display: flex; align-items: baseline; flex-wrap: wrap; gap: 7px 12px; padding: 14px 16px; margin-bottom: 18px; border: 1px solid var(--line); border-radius: 12px; background: var(--bg); }
.vehicle-summary strong { font-size: 15px; font-weight: 600; }
.vehicle-summary span { color: var(--secondary); font-size: 12px; }
.settings-field { display: grid; gap: 8px; margin-bottom: 16px; font-size: 13px; }
.settings-field select, .settings-field input { width: 100%; min-width: 0; min-height: 46px; border: 1px solid var(--line-strong); border-radius: 10px; background: var(--bg); color: var(--text); padding: 10px 12px; font-size: 14px; }
.field-label { display: block; font-size: 13px; margin-bottom: 8px; color: var(--secondary); }
.mileage-editor { display: flex; align-items: stretch; gap: 10px; }
.mileage-input { display: flex; align-items: center; min-width: 0; flex: 1; border: 1px solid var(--line-strong); border-radius: 11px; background: var(--bg); }
.mileage-input:focus-within { border-color: var(--accent); }
.mileage-input input { min-width: 0; width: 100%; padding: 12px 0 12px 14px; border: 0; background: transparent; color: var(--text); font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }
.mileage-input input:focus-visible { outline: none; }
.mileage-input > span { padding: 0 14px 0 8px; color: var(--secondary); font-size: 13px; }
.mileage-save { flex-shrink: 0; padding: 12px 15px; border: 1px solid var(--line-strong); border-radius: 11px; background: var(--surface-raised); font-size: 13px; }
.mileage-save:hover:not(:disabled) { background: var(--hover); }
.settings-hint { color: var(--secondary); font-size: 12px; line-height: 1.6; margin: 10px 0 0; }
.settings-error { color: var(--warning); font-size: 13px; line-height: 1.6; margin: 10px 0 0; }
.settings-success { display: flex; align-items: center; gap: 6px; color: var(--accent); font-size: 12px; line-height: 1.6; margin: 10px 0 0; }
.settings-success svg { flex-shrink: 0; }
.settings-empty p { color: var(--secondary); font-size: 13px; line-height: 1.6; }
.divided-section { margin-top: 24px; padding-top: 22px; border-top: 1px solid var(--line-strong); }
.theme-options { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.theme-choice { position: relative; padding: 7px; border: 1px solid var(--line-strong); border-radius: 11px; cursor: pointer; }
.theme-choice.chosen { border-color: var(--accent); }
.theme-choice input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.theme-choice:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: 3px; }
.theme-preview { display: grid; gap: 4px; padding: 9px; height: 49px; border: 1px solid #ffffff12; border-radius: 6px; background: #171b24; }
.theme-preview > span { height: 5px; width: 74%; border-radius: 2px; background: #4f5c76; }
.theme-preview > span:first-child { width: 40%; background: #b6c8ed; }
.theme-preview > span:last-child { width: 56%; }
[data-preview-theme='light'] .theme-preview { background: #f2f4f7; border-color: #0000000d; }
[data-preview-theme='light'] .theme-preview > span { background: #bdc6d3; }
[data-preview-theme='light'] .theme-preview > span:first-child { background: #5f7091; }
[data-preview-theme='black'] .theme-preview { background: #050505; }
[data-preview-theme='black'] .theme-preview > span { background: #39393e; }
[data-preview-theme='black'] .theme-preview > span:first-child { background: #c0c0c6; }
.theme-name { display: flex; align-items: center; justify-content: space-between; gap: 4px; min-height: 27px; padding: 5px 2px 0; font-size: 12px; }
.theme-name svg { color: var(--accent); }
.voice-section h3 { margin-bottom: 0; }
.voice-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 16px; }
.voice-card { min-width: 0; border: 1px solid var(--line-strong); border-radius: 13px; background: var(--bg); overflow: hidden; }
.voice-card.chosen { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 9%, var(--bg)); }
.voice-choice { display: flex; align-items: center; gap: 10px; min-height: 48px; padding: 12px 14px; cursor: pointer; font-size: 14px; font-weight: 500; }
.voice-choice input { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); flex-shrink: 0; }
.voice-preview { display: flex; align-items: center; justify-content: center; gap: 7px; width: calc(100% - 20px); min-height: 40px; margin: 0 10px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--secondary); font-size: 12px; }
.voice-preview:hover { background: var(--hover); color: var(--text); }
.voice-preview[aria-pressed='true'] { color: var(--accent); border-color: var(--accent); }
.voice-save { width: 100%; margin-top: 16px; }
fieldset:disabled { opacity: .65; }
@media (max-width: 520px) {
  .voice-grid { grid-template-columns: 1fr; gap: 8px; }
  .voice-card { display: grid; grid-template-columns: minmax(0, 1fr) 104px; align-items: center; }
  .voice-choice { min-height: 64px; padding: 12px; gap: 8px; }
  .voice-preview { width: auto; min-height: 44px; margin: 8px 8px 8px 0; }
  .mileage-editor { flex-wrap: wrap; }
  .mileage-input { flex-basis: 150px; }
  .mileage-save { flex: 1 0 auto; }
}
</style>
