<template>
  <n-card size="small">
    <div style="display: flex; align-items: center; gap: 16px">
      <n-text strong style="white-space: nowrap">{{ $t('timeMachine.round') }} {{ modelValue }} / {{ max }}</n-text>
      <n-slider
        :value="modelValue"
        :min="1"
        :max="max"
        :step="1"
        :marks="sliderMarks"
        style="flex: 1"
        @update:value="$emit('update:modelValue', $event)"
      />
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: number
  max: number
}>()

defineEmits<{
  'update:modelValue': [value: number]
}>()

const sliderMarks = computed(() => {
  const marks: Record<number, string> = {}
  if (props.max <= 20) {
    for (let i = 1; i <= props.max; i++) marks[i] = String(i)
  } else {
    const step = Math.ceil(props.max / 10)
    for (let i = 1; i <= props.max; i += step) marks[i] = String(i)
    marks[props.max] = String(props.max)
  }
  return marks
})
</script>
