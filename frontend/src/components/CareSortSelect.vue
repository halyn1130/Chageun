<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount, useId } from 'vue'
import { ChevronDown, Check } from 'lucide-vue-next'
const props = defineProps({ modelValue: { type: String, default: 'default' } })
const emit = defineEmits(['update:modelValue'])
const options = [{ value: 'default', label: '기본 순서' }, { value: 'urgent', label: '교환 임박순' }]
const open = ref(false)
const root = ref(null)
const trigger = ref(null)
const menuId = useId()
function focusOption(index) { root.value?.querySelectorAll('[role="menuitemradio"]')[index]?.focus() }
async function showMenu() {
  open.value = true
  await nextTick()
  focusOption(options.findIndex(option => option.value === props.modelValue))
}
function closeMenu(restore = false) {
  open.value = false
  if (restore) trigger.value?.focus()
}
function choose(value) { emit('update:modelValue', value); closeMenu(true) }
function outside(event) { if (!root.value?.contains(event.target)) closeMenu() }
function onFocusOut(event) { if (!root.value?.contains(event.relatedTarget)) closeMenu() }
function move(event, index) {
  const key = event.key
  if (key === 'Escape') { event.preventDefault(); closeMenu(true) }
  else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(key)) {
    event.preventDefault()
    focusOption(key === 'Home' ? 0 : key === 'End' ? 1 : (index + (key === 'ArrowDown' ? 1 : -1) + options.length) % options.length)
  }
}
onMounted(() => document.addEventListener('pointerdown', outside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', outside))
</script>
<template>
  <div ref="root" class="care-sort-picker" @focusout="onFocusOut">
    <button ref="trigger" type="button" class="care-sort-trigger" aria-label="소모품 정렬 방식" aria-haspopup="menu" :aria-expanded="open" :aria-controls="menuId" @click="open ? closeMenu() : showMenu()" @keydown.down.prevent="showMenu" @keydown.up.prevent="showMenu" @keydown.esc.prevent="closeMenu(true)">
      <span>{{ options.find(option => option.value === modelValue)?.label }}</span><ChevronDown :size="14" aria-hidden="true" />
    </button>
    <div v-if="open" :id="menuId" class="care-sort-menu" role="menu" aria-label="정렬 선택">
      <button v-for="(option, index) in options" :key="option.value" type="button" role="menuitemradio" :aria-checked="modelValue === option.value" @click="choose(option.value)" @keydown="move($event, index)"><span>{{ option.label }}</span><Check v-if="modelValue === option.value" :size="14" aria-hidden="true" /></button>
    </div>
  </div>
</template>
<style scoped>
.care-sort-picker { position: relative; }
.care-sort-trigger { display: inline-flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 112px; min-height: 32px; padding: 6px 10px; border: 1px solid #a5bfff30; border-radius: 7px; background: #252d3d; color: #d5def0; font: inherit; line-height: 1.4; }
.care-sort-trigger svg { flex: 0 0 14px; }
.care-sort-menu { position: absolute; top: calc(100% + 6px); left: 0; z-index: 20; min-width: 140px; padding: 4px; border: 1px solid #a5bfff40; border-radius: 9px; background: #252d3d; box-shadow: 0 8px 22px #0005; }
.care-sort-menu button { display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; min-height: 34px; padding: 7px 9px; border: 0; border-radius: 5px; color: #d5def0; background: transparent; font: inherit; text-align: left; white-space: nowrap; }
.care-sort-menu button:hover, .care-sort-menu button:focus-visible { background: #bdcdf722; }
.care-sort-trigger:focus-visible, .care-sort-menu button:focus-visible { outline: 2px solid #91b5ff; outline-offset: 2px; }
[data-theme='light'] .care-sort-trigger, [data-theme='light'] .care-sort-menu { background: #fff; color: #334f7a; border-color: #b9cbe9; }
[data-theme='light'] .care-sort-menu button { color: #334f7a; }
@media (max-width: 700px) { .care-sort-trigger { min-height: 44px; min-width: 100px; gap: 6px; padding-inline: 8px; } .care-sort-menu button { min-height: 44px; } }
</style>
