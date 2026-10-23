<script setup>
import { ArrowRight } from 'lucide-vue-next'
import GuideIcon from './GuideIcon.vue'
import { guidanceCategories } from '../guidance.js'
defineProps({ busy: Boolean })
const emit = defineEmits(['select'])
const categories = guidanceCategories.filter(category => category.id !== 'maintenance')
const examples = {
  warning: '경고등 · 소리와 진동 · 시동 · 냄새',
  controls: '온도·공기 · 시야·조명 · 시트·편의 · 주행 보조',
  rules: '교차로 · 차선과 표지 · 주정차 · 보호구역',
}
</script>
<template>
  <nav class="guidance-menu home-guidance" aria-label="도움받을 주제">
    <div class="guidance-categories">
      <button
        v-for="category in categories"
        :key="category.id"
        :disabled="busy"
        :data-category="category.id"
        @click="emit('select', { category: category.id })"
      >
        <span class="category-symbol"
          ><GuideIcon :name="category.icon" :size="29"
        /></span>
        <span class="category-copy"
          ><strong>{{ category.label }}</strong
          ><span>{{ category.description }}</span
          ><small>{{ examples[category.id] }}</small></span
        ><ArrowRight :size="24" />
      </button>
    </div>
  </nav>
</template>
