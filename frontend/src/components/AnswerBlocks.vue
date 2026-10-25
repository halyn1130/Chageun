<script setup>
import { computed } from 'vue'
import { answerBlocks } from '../answerSections.js'
const props = defineProps({ text: { type: String, default: '' } })
const blocks = computed(() => answerBlocks(props.text))
</script>
<template>
  <div class="answer-blocks">
    <template v-for="(block, index) in blocks" :key="index">
      <ol v-if="block.type === 'ordered'" class="answer-steps">
        <li v-for="(step, i) in block.items" :key="i"><span class="answer-step-number" aria-hidden="true">{{ i + 1 }}</span><span class="answer-step-text">{{ step }}</span></li>
      </ol>
      <ul v-else-if="block.type === 'unordered'" class="answer-bullets"><li v-for="(step, i) in block.items" :key="i">{{ step }}</li></ul>
      <p v-else class="answer-prose">{{ block.text }}</p>
    </template>
  </div>
</template>
