<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Monitor, Smartphone, RotateCcw } from 'lucide-vue-next'
import BrandLogo from './components/BrandLogo.vue'
const stage = ref(null)
const surface = ref(null)
const savedMode = localStorage.getItem('chageun-preview')
const mode = ref(['pc', 'mobile'].includes(savedMode) ? savedMode : window.matchMedia('(max-width: 700px)').matches ? 'mobile' : 'pc')
const bounds = ref({ width: window.innerWidth, height: window.innerHeight - 140 })
const size = computed(() => mode.value === 'mobile' ? { width: 390, height: 844 } : { width: 1280, height: 480 })
const scale = computed(() => Math.max(0.1, Math.min(
  (bounds.value.width - 24) / size.value.width,
  (bounds.value.height - 24) / size.value.height,
  mode.value === 'mobile' ? 1 : 2,
)))
const frameStyle = computed(() => ({
  width: `${size.value.width * scale.value}px`,
  height: `${size.value.height * scale.value}px`,
}))
let observer
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    bounds.value = { width: entry.contentRect.width, height: entry.contentRect.height }
  })
  observer.observe(stage.value)
})
onBeforeUnmount(() => observer?.disconnect())
function reset() {
  surface.value.contentWindow.location.reload()
}
function selectMode(value) {
  mode.value = value
  localStorage.setItem('chageun-preview', value)
}
</script>

<template>
  <div class="display-preview">
    <header class="preview-header">
      <div class="preview-brand"><BrandLogo /><span>차근 서비스 시연</span></div>
      <div class="preview-actions">
        <div class="preview-modes" role="group" aria-label="미리보기 화면">
          <button :aria-pressed="mode === 'pc'" @click="selectMode('pc')"><Monitor :size="16" />PC</button>
          <button :aria-pressed="mode === 'mobile'" @click="selectMode('mobile')"><Smartphone :size="16" />모바일</button>
        </div>
        <button class="preview-reset" aria-label="시연 초기화" @click="reset"><RotateCcw :size="15" /><span>시연 초기화</span></button>
      </div>
    </header>
    <main ref="stage" class="preview-stage">
      <div class="display-frame" :class="{ 'mobile-frame': mode === 'mobile' }" :style="frameStyle">
        <iframe
          ref="surface"
          :title="mode === 'mobile' ? '차근 모바일 화면' : '차근 12.3형 와이드 화면'"
          allow="microphone"
          src="/?surface=1"
          :style="{ width: `${size.width}px`, height: `${size.height}px`, transform: `scale(${scale})` }"
        />
      </div>
    </main>
    <footer class="preview-footer">
      <strong>{{ mode === 'mobile' ? '모바일' : '12.3형 와이드' }}</strong><span>{{ mode === 'mobile' ? '390 × 844 · 세로 화면' : '8:3 · 1280 × 480 시연 기준' }}</span>
    </footer>
  </div>
</template>

<style scoped>
.display-preview {
  height: 100dvh;
  min-height: 350px;
  background: #090a0b;
  color: #b1b3b8;
  display: flex;
  flex-direction: column;
  padding: 0 38px;
  font-family:
    -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
}
.preview-header {
  height: 78px;
  flex: 0 0 78px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
}
.preview-header > div {
  display: flex;
  align-items: center;
  gap: 16px;
}
.preview-header strong {
  font-size: 18px;
  color: #eee;
  letter-spacing: -0.7px;
  font-weight: 600;
}
.preview-brand > span {
  font-size: 12px;
  color: #71747b;
}
.preview-header button {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  background: transparent;
  border: 1px solid #ffffff13;
  border-radius: 8px;
  color: #9b9ea5;
  font-size: 12px;
}
.preview-header button:hover {
  background: #ffffff09;
  color: #eee;
}
.preview-header .preview-actions { gap: 12px; }
.preview-modes { display: flex; gap: 3px; padding: 4px; border: 1px solid #ffffff16; border-radius: 12px; background: #12151a; }
.preview-modes button { border: 0; min-height: 34px; padding-inline: 13px; border-radius: 8px; }
.preview-modes button[aria-pressed='true'] { background: #303949; color: #e2eaff; box-shadow: inset 0 0 0 1px #b1c6ff20; }
.preview-reset span { color: inherit; }
.preview-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}
.display-frame {
  position: relative;
  border-radius: 15px;
  outline: 1px solid #ffffff18;
  overflow: hidden;
  box-shadow:
    0 40px 90px #0007,
    0 0 0 6px #111214;
  background: #141517;
  flex: 0 0 auto;
}
.display-frame iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 1280px;
  height: 480px;
  transform-origin: top left;
  border: 0;
  background: #141517;
}
.display-frame.mobile-frame { border-radius: 30px; box-shadow: 0 30px 80px #0008, 0 0 0 7px #1b1e25, 0 0 0 8px #ffffff16; }
.preview-footer {
  height: 68px;
  flex: 0 0 68px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 12px;
  font-size: 11px;
  letter-spacing: 0.3px;
  color: #62656b;
}
.preview-footer strong {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 1.5px;
  color: #9a9ca3;
}
@media (max-width: 800px) {
  .display-preview {
    padding: 0 14px;
  }
  .preview-header {
    height: 60px;
    flex-basis: 60px;
  }
  .preview-footer {
    height: 60px;
    flex-basis: 60px;
    font-size: 10px;
    gap: 10px;
  }
}
@media (max-width: 540px) {
  .display-preview { padding: 0 10px; min-height: 320px; }
  .preview-header { padding-inline: 2px; }
  .preview-brand > span { display: none; }
  .preview-brand :deep(.brand-logo) { width: 42px; height: 26px; }
  .preview-brand :deep(.wordmark strong) { font-size: 18px; }
  .preview-header .preview-actions { gap: 6px; }
  .preview-modes button { padding-inline: 9px; gap: 5px; }
  .preview-header .preview-reset { padding: 0; width: 36px; justify-content: center; }
  .preview-reset span { display: none; }
  .preview-footer { height: 38px; flex-basis: 38px; padding: 0 6px; }
}
</style>
