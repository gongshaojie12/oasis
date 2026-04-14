<template>
  <NTag :type="tagType" :bordered="false" size="small" round>
    {{ label }}
  </NTag>
</template>

<script setup lang="ts">
import { NTag } from 'naive-ui'

const props = defineProps<{ status: string }>()

const statusMap: Record<string, { type: string; label: string }> = {
  pending: { type: 'default', label: '等待中' },
  running: { type: 'info', label: '运行中' },
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'error', label: '失败' },
  cancelled: { type: 'warning', label: '已取消' },
}

const tagType = computed(() => (statusMap[props.status]?.type || 'default') as any)
const label = computed(() => statusMap[props.status]?.label || props.status)
</script>
