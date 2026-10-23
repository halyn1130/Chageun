<script setup>
import { computed } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import GuideIcon from './GuideIcon.vue'
import { usageState } from '../maintenanceUsage.js'
const props = defineProps({ usage: { type: Object, required: true }, disabled: Boolean })
defineEmits(['select'])
const state = computed(() => usageState(props.usage))
const number = value => new Intl.NumberFormat('ko-KR').format(value)
const percent = computed(() => props.usage.priorityRatio == null ? null : Math.min(100, Math.floor(props.usage.priorityRatio * 100)))
const emptyLabel = computed(() => ({ loading: '기록을 확인하고 있어요', unavailable: '기록을 다시 불러와 주세요', no_vehicle: '내 차를 선택해 주세요', no_record: '교환 기록을 남겨 주세요', invalid_record: '날짜·주행거리 확인이 필요해요' })[props.usage.status])
</script>
<template>
  <button class="maintenance-card" :data-item="usage.item.id" :data-tone="state.tone" :disabled="disabled" :aria-label="`${usage.item.label} 관리 · ${state.label}`" @click="$emit('select', usage.item)">
    <span class="maintenance-symbol" aria-hidden="true">
      <svg class="maintenance-ring" viewBox="0 0 80 80"><circle class="maintenance-ring-track" cx="40" cy="40" r="35" pathLength="100" /><circle v-if="percent != null" class="maintenance-ring-fill" cx="40" cy="40" r="35" pathLength="100" :stroke-dasharray="`${percent} 100`" /></svg>
      <GuideIcon :name="usage.item.icon" :size="25" /><small v-if="percent != null">{{ percent }}<span>%</span></small>
    </span>
    <span class="maintenance-card-body">
      <span class="maintenance-card-title"><strong>{{ usage.item.label }}</strong><span class="maintenance-state">{{ state.label }}</span></span>
      <span v-if="usage.status === 'recorded'" class="maintenance-metrics">
        <span class="maintenance-metric"><span class="maintenance-metric-reading"><span class="maintenance-metric-label">주행</span><strong>{{ usage.distance == null ? '미입력' : number(usage.distance) }}</strong><span>{{ usage.interval ? `/ ${number(usage.interval.km)} km` : 'km' }}</span></span><span v-if="usage.distanceRatio != null" class="maintenance-meter"><i :style="{ width: `${usage.distanceRatio * 100}%` }" /></span><small v-else>교환 기준 확인 필요</small></span>
        <span class="maintenance-metric"><span class="maintenance-metric-reading"><span class="maintenance-metric-label">기간</span><strong>{{ usage.months }}</strong><span>{{ usage.interval ? `/ ${usage.interval.months}개월` : '개월 경과' }}</span></span><span v-if="usage.timeRatio != null" class="maintenance-meter"><i :style="{ width: `${usage.timeRatio * 100}%` }" /></span><small v-else>{{ usage.last.performed_at.replaceAll('-', '.') }} 교환</small></span>
      </span>
      <span v-else class="maintenance-empty-copy">{{ emptyLabel }}</span>
    </span>
    <ChevronRight class="maintenance-chevron" :size="22" />
  </button>
</template>
