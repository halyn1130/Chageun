<script setup>
import { computed } from 'vue'
import {
  Wrench,
  TriangleAlert,
  SlidersHorizontal,
  Signpost,
  Droplet,
  Wind,
  CircleDot,
  Disc3,
  Battery,
  Thermometer,
  Fuel,
  AudioLines,
  Power,
  Sun,
  Armchair,
  Gauge,
  Route,
  CircleParking,
  Footprints,
  Filter,
} from 'lucide-vue-next'
const props = defineProps({ name: String, size: { type: Number, default: 24 } })
const icon = computed(
  () =>
    ({
      wrench: Wrench,
      alert: TriangleAlert,
      sliders: SlidersHorizontal,
      sign: Signpost,
      oil: Droplet,
      drop: Droplet,
      filter: Filter,
      wind: Wind,
      tire: CircleDot,
      brake: Disc3,
      battery: Battery,
      temp: Thermometer,
      fuel: Fuel,
      audio: AudioLines,
      power: Power,
      sun: Sun,
      seat: Armchair,
      steer: Gauge,
      route: Route,
      parking: CircleParking,
      walk: Footprints,
    })[props.name] || CircleDot,
)
</script>
<template>
  <svg v-if="['wiper', 'oil-filter', 'air-filter', 'cabin-filter'].includes(name)" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'wiper'">
      <path d="M3 6a23 23 0 0 1 18 0l-2 12H5L3 6Z" />
      <path d="m8 18 7-9m-4-1 7 4" />
    </template>
    <template v-else-if="name === 'oil-filter'">
      <path d="M7 5V3h10v2m-12 0h14v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5Zm4 4v8m6-8v8" />
    </template>
    <template v-else-if="name === 'air-filter'">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M7 7v10m5-10v10m5-10v10" />
    </template>
    <template v-else>
      <path d="m3 8 4-4h14v12l-4 4H3V8Zm0 0h14v12m0-12 4-4M6 11h8m-8 3h8m-8 3h8" />
    </template>
  </svg>
  <component v-else :is="icon" :size="size" :stroke-width="1.5" aria-hidden="true" />
</template>
