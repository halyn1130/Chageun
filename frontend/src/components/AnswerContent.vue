<script setup>
import { computed } from 'vue'
import { Info, TriangleAlert, CircleCheck } from 'lucide-vue-next'
import { splitAnswer } from '../answerSections.js'
import AnswerBlocks from './AnswerBlocks.vue'
const props = defineProps({ text: { type: String, default: '' } })
const answer = computed(() => splitAnswer(props.text))
const icons = { meaning: Info, caution: TriangleAlert, steps: CircleCheck }
</script>

<template>
  <div class="answer-content">
    <AnswerBlocks v-if="answer.intro" :text="answer.intro" />
    <div v-if="answer.sections.length" class="answer-sections">
      <section v-for="(section, index) in answer.sections" :key="index" class="answer-section" :class="`answer-section--${section.kind}`">
        <component :is="icons[section.kind]" class="answer-section-icon" :size="20" aria-hidden="true" />
        <div class="answer-section-body">
          <h4 class="answer-section-title">{{ section.title }}</h4>
          <AnswerBlocks :text="section.content" />
        </div>
      </section>
    </div>
  </div>
</template>
