<script setup>
import { computed, ref, useId, watch, onMounted, onBeforeUnmount } from 'vue'
const props = defineProps({
  focus: String,
  contextual: Boolean,
  intro: Boolean,
  maintenanceTones: Object,
  selectedTone: String,
})
const emit = defineEmits(['introduced'])
const artwork = ref(null)
const groundId = useId()
const revealing = ref(false)
const introPending = ref(props.intro)
const scanDuration = 950
const scanParts = ['coolant', 'engine', 'battery', 'wiper', 'tires']
const layerNames = ['engine', 'oil', 'brakes', 'battery', 'tires', 'fuel', 'coolant', 'cabin', 'wiper']
const priority = { comfortable: 0, soon: 1, urgent: 2 }
const orderedLayers = computed(() => [...layerNames].sort((a, b) => (priority[props.maintenanceTones?.[a]] || 0) - (priority[props.maintenanceTones?.[b]] || 0)))
const scanLayers = computed(() => orderedLayers.value.filter(name => scanParts.includes(name) || props.maintenanceTones?.[name] === 'urgent'))
let revealTimer
let disposed = false
function finishIntro() {
  clearTimeout(revealTimer)
  introPending.value = false
  revealing.value = false
  emit('introduced')
}
onMounted(async () => {
  if (!props.intro) return
  // Decode the component layers too, so none of the first-visit highlights is missed.
  await Promise.all(
    [...artwork.value.querySelectorAll('img')].map((image) =>
      image.decode().catch(() => {}),
    ),
  )
  if (disposed || !introPending.value) return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    finishIntro()
    return
  }
  introPending.value = false
  revealing.value = true
  // One spatial mask reveals the white body light and every component together.
  // The timer is only a fallback; the shared scan's animationend finishes the intro.
  revealTimer = setTimeout(finishIntro, scanDuration + 100)
})
// Choosing a component takes precedence over the introductory tour.
watch(() => props.focus, () => {
  if (revealing.value || introPending.value) finishIntro()
})
onBeforeUnmount(() => {
  disposed = true
  clearTimeout(revealTimer)
})
const layer = computed(
  () =>
    ({
      oil: 'oil',
      abs: 'brakes',
      brake: 'brakes',
      tire: 'tires',
      airbag: 'cabin',
      // Restore the original front assembly as a system-level visual.
      // It is not a diagram of the cabin filter's exact physical location.
      'cabin-filter': 'coolant',
    })[props.focus] || props.focus,
)
function visiblePart(name) {
  if (revealing.value) return false
  if (layer.value) return layer.value === name
  return ['urgent', 'soon'].includes(props.maintenanceTones?.[name])
}
function stateTone(name) {
  if (layer.value === name && props.selectedTone) return props.selectedTone
  if (props.maintenanceTones) return props.maintenanceTones[name === 'oil' ? 'engine' : name] || 'unknown'
  if (props.contextual) return 'unknown'
  if (props.focus === 'abs' && name === 'brakes') return 'soon'
  return { engine: 'soon', oil: 'urgent', brakes: 'urgent', battery: 'urgent', tires: 'soon', fuel: 'soon', coolant: 'urgent', cabin: 'urgent', wiper: 'comfortable' }[name]
}
function stateSource(name) {
  const tone = stateTone(name)
  // Each status is its own generated material rendering. Unknown stays neutral.
  return tone in priority ? `/images/states/${name}-${tone}.png` : '/images/vehicle-cutaway.png'
}
</script>
<template>
  <div
    class="vehicle-canvas"
    :data-warning="focus"
    :class="{ contextual, revealing, 'intro-pending': introPending, 'care-vehicle': maintenanceTones }"
    :style="{ '--scan-duration': `${scanDuration}ms` }"
  >
    <div
      ref="artwork"
      class="vehicle-art"
      role="img"
      :aria-label="
        maintenanceTones && !focus
          ? '교환 임박 부품은 빨간색, 교환 준비 부품은 주황색으로 표시한 차량 구조'
          : focus
          ? '대화와 관련된 계통을 강조한 차량 구조'
          : '반투명 차량 내부 구조'
      "
    >
      <!-- Ground shares the image coordinates: front wheel (758, 850), rear wheel (1548, 641).
           The near edge follows their contact line, while the far edge narrows toward the rear. -->
      <svg v-if="maintenanceTones" class="car-ground-light" viewBox="0 0 1774 887" aria-hidden="true" focusable="false">
        <defs>
          <radialGradient :id="`${groundId}-glow`" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(900 697) rotate(-15) scale(840 154)">
            <stop stop-color="#b3c9e8" stop-opacity=".18" />
            <stop offset=".5" stop-color="#90add4" stop-opacity=".1" />
            <stop offset=".8" stop-color="#7797bf" stop-opacity=".035" />
            <stop offset="1" stop-color="#7797bf" stop-opacity="0" />
          </radialGradient>
          <filter :id="`${groundId}-soft`" x="-10%" y="-20%" width="120%" height="140%" color-interpolation-filters="sRGB">
            <feGaussianBlur stdDeviation="10" />
          </filter>
        </defs>
        <path d="M68 704C190 658 1080 485 1308 474C1415 467 1650 546 1704 599C1740 635 1575 692 1338 756L813 894C733 915 608 883 457 845L152 751C98 734 62 716 68 704Z" :fill="`url(#${groundId}-glow)`" :filter="`url(#${groundId}-soft)`" />
        <g fill="#05080d" fill-opacity=".42" :filter="`url(#${groundId}-soft)`">
          <ellipse cx="758" cy="850" rx="101" ry="16" transform="rotate(-15 758 850)" />
          <ellipse cx="1548" cy="641" rx="75" ry="12" transform="rotate(-15 1548 641)" />
        </g>
      </svg>
      <img class="car-base" src="/images/vehicle-cutaway.png" alt="" />
      <svg width="0" height="0" aria-hidden="true">
        <defs>
          <clipPath id="clip-engine" clipPathUnits="objectBoundingBox">
            <path
              d="M.12 .48 .18 .37 .27 .39 .36 .43 .37 .52 .29 .61 .245 .615 .235 .59 .19 .605 .17 .59 .11 .53Z"
            />
          </clipPath>
          <clipPath id="clip-oil" clipPathUnits="objectBoundingBox">
            <path
              d="M.12 .48 .18 .37 .27 .39 .36 .43 .37 .52 .29 .61 .265 .71 .19 .70 .17 .59 .11 .53Z"
            />
          </clipPath>
          <clipPath id="clip-battery" clipPathUnits="objectBoundingBox">
            <path d="M.284 .543 .308 .527 .353 .547 .352 .568 .315 .612 .285 .622Z" />
          </clipPath>
          <clipPath id="clip-brakes" clipPathUnits="objectBoundingBox">
            <ellipse cx=".437" cy=".789" rx=".057" ry=".126" />
            <ellipse cx=".875" cy=".582" rx=".042" ry=".108" />
          </clipPath>
          <clipPath id="clip-tires" clipPathUnits="objectBoundingBox">
            <ellipse cx=".428" cy=".787" rx=".084" ry=".178" />
            <ellipse cx=".868" cy=".58" rx=".063" ry=".15" />
          </clipPath>
          <clipPath id="clip-fuel" clipPathUnits="objectBoundingBox">
            <path
              d="M.654 .475 .717 .469 .77 .495 .775 .56 .73 .595 .663 .561Z"
            />
          </clipPath>
          <clipPath id="clip-coolant" clipPathUnits="objectBoundingBox">
            <path
              d="M.081 .551 .115 .49 .166 .48 .23 .57 .23 .735 .18 .79 .08 .71Z"
            />
          </clipPath>
          <clipPath id="clip-cabin" clipPathUnits="objectBoundingBox">
            <path
              d="M.29 .19 .76 .12 .835 .39 .763 .46 .61 .53 .53 .48 .4 .39 .29 .34Z"
            />
          </clipPath>
          <clipPath id="clip-wiper" clipPathUnits="objectBoundingBox">
            <path d="M.26 .285 .48 .405 .48 .455 .26 .345Z" />
          </clipPath>
        </defs>
      </svg>
      <img
        v-for="name in orderedLayers"
        :key="name"
        class="car-state"
        :data-layer="name"
        :class="{ visible: visiblePart(name) }"
        :data-tone="stateTone(name)"
        :src="stateSource(name)"
        alt=""
      />
      <div v-if="revealing" class="car-scan" aria-hidden="true" @animationend.self="finishIntro">
        <img class="scan-body" src="/images/vehicle-cutaway.png" alt="" />
        <img v-for="name in scanLayers" :key="name" class="car-state" :data-layer="name" :src="stateSource(name)" alt="" />
      </div>
    </div>
  </div>
</template>
