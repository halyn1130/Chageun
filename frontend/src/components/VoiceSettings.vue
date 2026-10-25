<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import DialogSheet from './DialogSheet.vue'
import { api, getToken } from '../api.js'
import { createRemoteSpeech } from '../remoteSpeech.js'
const emit = defineEmits(['close'])
const loaded = ref(false)
const voices = ref([]), selected = ref(null), busy = ref(true), error = ref(''), message = ref(''), playing = ref(null)
let alive = true
const requests = new AbortController()
const preview = createRemoteSpeech({ platform: window, getToken, getVoice: () => playing.value })
onMounted(async () => {
 try {
  const [catalog, saved] = await Promise.all([api('/settings/voices', {signal: requests.signal}), api('/settings/voice', {signal: requests.signal})])
  if (!alive) return
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
 try { await api('/settings/voice',{method:'PUT',body:{voice_id:selected.value},signal:requests.signal}); if(alive) message.value='저장했어요. 다음 음성 안내부터 적용돼요.' }
 catch(e) { if(alive) error.value=e.message }
 finally { if(alive) busy.value=false }
}
onBeforeUnmount(() => {alive=false;requests.abort();preview.stop()})
</script>
<template>
 <DialogSheet :open="true" title="개인 설정" eyebrow="나에게 맞는 차근" @close="emit('close')">
  <fieldset class="voice-settings" :disabled="busy || !loaded">
   <legend>안내 목소리</legend>
   <p>미리 들어보고 선택해 주세요. 저장한 목소리는 다음 로그인에도 유지돼요.</p>
   <label class="voice-choice"><input type="radio" name="voice-choice" :value="null" v-model="selected" @change="message=''" />기본 목소리 (이겸)</label>
   <div v-for="v in voices" :key="v.voice_id" class="voice-choice">
    <label><input type="radio" name="voice-choice" :value="v.voice_id" v-model="selected" @change="message=''" />{{ v.name }}</label>
    <button type="button" :aria-label="`${v.name} 미리 듣기`" @click="listen(v.voice_id)">{{ playing === v.voice_id ? '재생 중 · 중지' : '미리 듣기' }}</button>
   </div>
   <button type="button" class="voice-save" @click="save">{{ busy ? '처리 중…' : '저장' }}</button>
  </fieldset>
  <p v-if="error" role="alert">{{ error }}</p><p v-if="message" role="status">{{ message }}</p>
 </DialogSheet>
</template>
<style scoped>
.voice-settings { border:0; padding:0; margin:0; min-width:0; }
legend {font-size:16px;font-weight:600;} p {font-size:13px;color:var(--secondary);line-height:1.6;}
.voice-choice {display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid var(--line);font-size:14px;min-height:44px;}
.voice-choice label {display:flex;align-items:center;gap:10px;flex:1;} input {accent-color:var(--accent);margin-right:8px;}
button {border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--text);padding:9px 12px;cursor:pointer;font-size:12px;min-height:40px;}
.voice-save {width:100%;margin-top:18px;background:var(--surface-raised);font-size:14px;} :disabled {opacity:.6;cursor:wait;}
</style>
