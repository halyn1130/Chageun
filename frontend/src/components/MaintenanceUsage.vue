<script setup>
import { computed } from 'vue'
import { CalendarDays, CircleAlert } from 'lucide-vue-next'
import GuideIcon from './GuideIcon.vue'
import { usageState } from '../maintenanceUsage.js'
const props = defineProps({ usage: Object, compact: Boolean })
const number = value => new Intl.NumberFormat('ko-KR').format(value)
const emptyLabel = computed(() => ({ loading:'기록을 확인하고 있어요', unavailable:'기록을 다시 불러와 주세요', no_vehicle:'내 차를 선택해 주세요', no_record:'첫 교환 기록을 남겨보세요', invalid_record:'날짜·주행거리를 확인해 주세요' })[props.usage.status])
const accessibleLabel = computed(() => emptyLabel.value || `${props.usage.item.label}: 교환 기록 이후 ${props.usage.distance == null ? '주행거리 미입력' : number(props.usage.distance) + 'km 주행'}${props.usage.interval ? ', 교환 기준 ' + number(props.usage.interval.km) + 'km 또는 ' + props.usage.interval.months + '개월' : ', 교환 기준 미확인'}, ${props.usage.months}개월 경과`)
</script>
<template>
  <div class="usage-visual" :class="{ compact, 'usage-empty': usage.status !== 'recorded' }" :data-tone="usageState(usage).tone" role="img" :aria-label="accessibleLabel">
    <div class="usage-dial" :class="{ unknown: usage.distanceRatio == null, exceeded: usage.mileageDue }">
      <svg class="usage-ring" viewBox="0 0 120 120" aria-hidden="true">
        <circle class="usage-track" cx="60" cy="60" r="52" pathLength="100" />
        <circle v-if="usage.distanceRatio != null" class="usage-fill" cx="60" cy="60" r="52" pathLength="100" :stroke-dasharray="`${usage.distanceRatio * 100} 100`" />
      </svg>
      <span v-if="usage.distance != null" class="usage-reading"><strong>{{ number(usage.distance) }}</strong><small>km · 기록 이후</small></span>
      <GuideIcon v-else :name="usage.item?.icon || 'oil'" :size="compact ? 29 : 37" />
    </div>
    <div class="usage-copy">
      <div class="usage-title"><strong>{{ compact ? usage.item?.label : '마지막 교환 이후' }}</strong><span v-if="usage.needsConfirmation" class="usage-caution"><CircleAlert :size="12" />기록 확인</span></div>
      <template v-if="usage.status === 'recorded'">
        <div class="usage-limit" v-if="usage.interval">{{ number(usage.interval.km) }} km 교환 기준 <small v-if="usage.intervalSource === 'manual'">· {{ usage.condition === 'severe' ? '가혹' : '일반' }} 운행</small></div>
        <div class="usage-limit" v-else>차종별 교환 기준 확인 필요</div>
        <div class="usage-time" :class="{ exceeded: usage.dateDue }"><CalendarDays :size="13" /><span>{{ usage.months > 0 ? `${usage.months}개월` : `${usage.days}일` }} 경과</span><small v-if="usage.interval">/ {{ usage.interval.months }}개월 기준</small></div>
        <div v-if="usage.timeRatio != null" class="usage-time-track" :class="{ exceeded: usage.dateDue }"><i :style="{ width: `${usage.timeRatio * 100}%` }" /></div>
        <small v-if="!compact" class="usage-caption">{{ usage.last.performed_at.replaceAll('-', '.') }} 교환 기록 · {{ usage.interval ? '거리와 기간 중 먼저 도래하는 기준으로 확인해요.' : '교환 기준은 차종과 운행 환경에 따라 달라요.' }}</small>
      </template>
      <template v-else><p class="usage-empty-label">{{ emptyLabel }}</p><small>기록을 바탕으로 관리 시점을 함께 확인해요.</small></template>
    </div>
  </div>
</template>
