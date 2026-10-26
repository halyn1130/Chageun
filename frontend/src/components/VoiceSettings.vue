<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { LogOut } from 'lucide-vue-next'
import DialogSheet from './DialogSheet.vue'
import { api, getToken } from '../api.js'
import { createRemoteSpeech } from '../remoteSpeech.js'
const emit = defineEmits(['close', 'saved', 'register', 'logout'])
const loaded = ref(false)
const displayName = ref(''), vehicleId = ref(null), vehicles = ref([]), voiceOpen = ref(false)
const selectedName = computed(() => voices.value.find(v => v.voice_id === selected.value)?.name || '이겸 · 기본')
const voices = ref([]), selected = ref(null), busy = ref(true), error = ref(''), message = ref(''), playing = ref(null)
let alive = true
const requests = new AbortController()
const preview = createRemoteSpeech({ platform: window, getToken, getVoice: () => playing.value === 'default' ? null : playing.value })
onMounted(async () => {
 try {
  const [catalog, saved, profile, cars] = await Promise.all([api('/settings/voices', {signal: requests.signal}), api('/settings/voice', {signal: requests.signal}), api('/settings/profile', {signal: requests.signal}), api('/vehicles', {signal: requests.signal})])
  if (!alive) return
  displayName.value = profile.display_name; vehicleId.value = profile.vehicle_id; vehicles.value = cars;
  voices.value = catalog; selected.value = saved.voice_id; loaded.value = true
 } catch(e) { if(alive) error.value = e.message }
 finally { if(alive) busy.value = false }
})
function listen(id) {
 if(playing.value === id) { preview.stop(); playing.value = null; return }
 error.value=''; playing.value=id
 preview.speak('안녕하세요. 차근입니다. 차량에 대해 궁금한 점을 편하게 말씀해 주세요.', {
  onEnd: () => { playing.value=null }, onError: value => { playing.value=null; error.value=value }
 })
}
async function save() {
 busy.value=true; error.value=''; message.value=''; preview.stop(); playing.value=null
 try { const saved = await api('/settings/profile',{method:'PUT',body:{display_name:displayName.value.trim(), vehicle_id:vehicleId.value, voice_id:selected.value},signal:requests.signal}); if(alive) { message.value='설정을 저장했어요.'; emit('saved', {...saved, vehicles: vehicles.value}) } }
 catch(e) { if(alive) error.value=e.message }
 finally { if(alive) busy.value=false }
}
onBeforeUnmount(() => {alive=false;requests.abort();preview.stop()})
</script>
<template>
 <DialogSheet :open="true" title="개인 설정" eyebrow="나에게 맞는 차근" @close="emit('close')">
  <form class="personal-settings" @submit.prevent="save">
   <fieldset aria-label="개인 설정 항목" :disabled="busy || !loaded">
    <label class="field">이름<input v-model="displayName" required maxlength="50" autocomplete="nickname" placeholder="사용할 이름" /></label>
    <p class="hint">차근에서 사용할 이름이에요. 로그인 아이디는 유지돼요.</p>
    <label class="field">차종 · 기본 차량
     <select v-if="vehicles.length" v-model="vehicleId" required>
      <option v-for="car in vehicles" :key="car.id" :value="car.id">{{ car.manufacturer }} {{ car.model }} · {{ car.model_year }} · {{ car.powertrain }}{{ car.nickname ? ` (${car.nickname})` : '' }}</option>
     </select>
     <span v-else class="empty">등록된 차량이 없어요.</span>
    </label>
    <button class="register" type="button" @click="emit('register')">차량 등록하기 <span aria-hidden="true">＋</span></button>
    <div class="voice-category">
     <button class="category-toggle" type="button" :aria-expanded="voiceOpen" aria-controls="voice-options" @click="voiceOpen = !voiceOpen">
      <span>안내 목소리 <small>{{ selectedName }}</small></span><span class="chevron" :class="{expanded: voiceOpen}" aria-hidden="true">⌄</span>
     </button>
     <div v-if="voiceOpen" id="voice-options" class="voice-options">
      <p class="hint">하나를 선택하면 다음 음성 안내부터 적용돼요.</p>
      <div class="voice-grid" role="radiogroup" aria-label="안내 목소리 선택">
       <div v-for="v in [{name:'이겸 · 기본', voice_id:null}, ...voices]" :key="v.voice_id || 'default'" class="voice-card" :class="{chosen: selected === v.voice_id}">
        <label><input type="radio" name="voice-choice" :value="v.voice_id" v-model="selected" />{{ v.name }}</label>
        <button type="button" :aria-label="`${v.name} 미리 듣기`" @click="listen(v.voice_id || 'default')">{{ playing === (v.voice_id || 'default') ? '재생 중 · 중지' : '미리 듣기' }}</button>
       </div>
      </div>
     </div>
    </div>
    <button type="submit" class="settings-save">{{ busy ? '저장 중…' : '변경 사항 저장' }}</button>
   </fieldset>
  </form>
  <p v-if="busy && !loaded" role="status">설정을 불러오는 중이에요.</p>
  <p v-if="error" role="alert">{{ error }}</p><p v-if="message" class="settings-feedback" role="status">{{ message }}</p>
  <div class="settings-account">
   <button type="button" class="settings-logout" :disabled="busy && loaded" @click="emit('logout')"><LogOut :size="16" aria-hidden="true" />로그아웃</button>
  </div>
 </DialogSheet>
</template>
<style scoped>
fieldset {border:0;padding:0;margin:0;min-width:0;}
.field:first-child {margin-top:0;}
.field {display:flex;flex-direction:column;gap:9px;font-size:13px;margin-top:16px;color:var(--text);}
.field input,.field select {width:100%;min-width:0;box-sizing:border-box;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--text);padding:12px;font:inherit;min-height:46px;}
.hint {font-size:12px;color:var(--secondary);line-height:1.6;margin:8px 0 14px;} .empty {color:var(--secondary);padding:12px 0;}
button {font:inherit;cursor:pointer;color:var(--text);} .register {background:none;border:0;padding:10px 0;font-size:12px;color:var(--secondary);}
.voice-category {border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:20px;}
.category-toggle {display:flex;justify-content:space-between;align-items:center;width:100%;border:0;background:none;padding:18px 0;text-align:left;font-size:14px;}
.category-toggle small {display:block;font-size:12px;color:var(--secondary);margin-top:6px;}.chevron {display:grid;place-items:center;width:24px;height:24px;font-size:22px;}.expanded {transform:rotate(180deg);}
.voice-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding-bottom:18px;}
.voice-card {border:1px solid var(--line);border-radius:10px;padding:12px;}.voice-card.chosen {border-color:var(--accent);background:var(--surface-raised);}
.voice-card label {display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;}.voice-card input {accent-color:var(--accent);margin:0;}
.voice-card button {background:none;border:0;padding:9px 0 0;font-size:11px;color:var(--secondary);}
.settings-save {width:100%;border:1px solid var(--line);border-radius:10px;background:var(--surface-raised);padding:13px;margin-top:22px;font-size:14px;}
.settings-feedback {font-size:12px;font-weight:400;line-height:1.5;color:var(--secondary);margin:10px 0 0;text-align:center;}
.settings-account {border-top:1px solid var(--line);margin-top:20px;padding-top:8px;}
.settings-logout {display:flex;align-items:center;justify-content:center;gap:8px;width:100%;min-height:44px;border:0;background:none;color:var(--secondary);font-size:13px;}
.settings-logout:hover {color:var(--text);}
fieldset:disabled {opacity:.6;} :disabled {cursor:wait;}
</style>
