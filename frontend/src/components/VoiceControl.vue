<script setup>
import { computed } from 'vue'
import { Mic, Square, Keyboard, Volume2 } from 'lucide-vue-next'
import VoiceOrb from './VoiceOrb.vue'
const props = defineProps({ state: Object, compact: Boolean, busy: Boolean, keyboardOpen: Boolean })
defineEmits(['toggle', 'keyboard'])
const usesTypecast = import.meta.env.VITE_TTS_PROVIDER === 'typecast'
const label = computed(
  () =>
    (props.busy && !props.state.active ? '답변을 준비하고 있어요' : {
      idle: props.compact ? '이어서 말하기' : '음성 대화 시작',
      connecting: '마이크 연결 중',
      listening: '듣고 있어요',
      thinking: '확인하고 있어요',
      speaking: '차근이 답하고 있어요',
      error: '다시 말하기',
    }[props.state.phase]),
)
</script>
<template>
  <section
    class="voice-control"
    :class="{ compact, 'voice-active': state.active }"
    :data-phase="state.phase"
    aria-label="음성 대화"
  >
    <div class="voice-orbit">
      <VoiceOrb v-if="state.active || state.phase === 'speaking'" class="home-voice-orb" :phase="state.phase" />
      <div class="voice-wave" aria-hidden="true">
        <i
          v-for="n in 17"
          :key="n"
          :style="{
            '--i': n,
            '--height': `${12 + Math.sin(n * 2.1) * 10 + (9 - Math.abs(n - 9)) * 4}px`,
          }"
        />
      </div>
      <button
        class="voice-primary"
        :class="{ 'is-active': state.active }"
        :aria-label="
          state.active ? '음성 입력 멈추기' : state.phase === 'speaking'
            ? '읽기 멈추기'
            : compact ? '이어서 말하기' : '음성 대화 시작'
        "
        :disabled="busy && !state.active"
        @click="$emit('toggle')"
      >
        <Square
          v-if="state.active"
          :size="30"
          fill="currentColor"
          :stroke-width="0"
        />
        <Volume2 v-else-if="state.phase === 'speaking'" :size="38" />
        <Mic v-else :size="compact ? 34 : 43" :stroke-width="1.45" />
      </button>
    </div>
    <h1>{{ label }}</h1>
    <p class="voice-prompt" role="status">
      {{
        state.error ||
        state.transcript ||
        (busy ? '내 차에 맞는 설명을 찾고 있어요' : state.active
          ? '듣기를 멈추려면 한 번 더 누르세요'
          : compact ? '궁금한 점을 더 말씀해 주세요' : '눌러서 편하게 물어보세요')
      }}
    </p>
    <button v-if="!compact || !keyboardOpen" class="keyboard-link" @click="$emit('keyboard')">
      <Keyboard :size="17" />{{ keyboardOpen ? '입력창 닫기' : compact ? '글로 이어 묻기' : '글로 물어보기' }}
    </button>
    <span v-if="!compact && !state.active" class="voice-service-note" :class="{ 'has-tts-credit': usesTypecast }"
      >브라우저 음성 인식 · 마이크 권한 필요<template v-if="usesTypecast"> · <a href="https://typecast.ai" target="_blank" rel="noopener noreferrer">음성 제공: Typecast</a></template></span
    >
  </section>
</template>
