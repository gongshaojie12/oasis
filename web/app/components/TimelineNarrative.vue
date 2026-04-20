<template>
  <n-card title="时间线叙事">
    <n-timeline>
      <n-timeline-item
        v-for="(item, index) in timeline"
        :key="index"
        :type="significanceType(item.significance)"
        :title="item.title"
        :content="item.description"
        :time="`第 ${item.step} 轮`"
      />
    </n-timeline>
    <n-empty v-if="!timeline.length" description="暂无时间线数据" />
  </n-card>
</template>

<script setup lang="ts">
interface TimelineItem {
  step: number
  title: string
  description: string
  significance: 'high' | 'medium' | 'low'
}

defineProps<{ timeline: TimelineItem[] }>()

function significanceType(sig: string): 'error' | 'warning' | 'info' {
  if (sig === 'high') return 'error'
  if (sig === 'medium') return 'warning'
  return 'info'
}
</script>
