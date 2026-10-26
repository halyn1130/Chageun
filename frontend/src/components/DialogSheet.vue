<script setup>
import { nextTick, ref, useId, watch } from 'vue'
import { X } from 'lucide-vue-next'
const props = defineProps({
  open: Boolean,
  title: String,
  eyebrow: String,
  wide: Boolean,
})
const emit = defineEmits(['close'])
const element = ref(null)
const titleId = useId()
function onBackdropClick(event) {
  if (event.target === element.value) emit('close')
}
watch(
  () => props.open,
  async (open) => {
    await nextTick()
    if (open && !element.value.open) element.value.showModal()
    if (!open && element.value.open) element.value.close()
  },
  { immediate: true },
)
</script>

<template>
  <dialog
    ref="element"
    class="sheet"
    :class="{ 'sheet-wide': wide }"
    :aria-labelledby="titleId"
    @cancel.prevent="emit('close')"
    @click="onBackdropClick"
  >
    <div class="sheet-inner">
      <header class="sheet-header">
        <div>
          <p v-if="eyebrow" class="overline">{{ eyebrow }}</p>
          <h2 :id="titleId">{{ title }}</h2>
        </div>
        <button class="icon-button" aria-label="닫기" @click="emit('close')">
          <X :size="22" />
        </button>
      </header>
      <div class="sheet-body"><slot /></div>
    </div>
  </dialog>
</template>
