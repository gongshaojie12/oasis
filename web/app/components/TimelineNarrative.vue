<template>
  <n-card :title="$t('analysis.timelineNarrative')">
    <n-timeline>
      <n-timeline-item
        v-for="(item, index) in timeline"
        :key="index"
        :type="significanceType(item.significance)"
        :title="item.title"
        :content="item.description"
        :time="$t('analysis.roundLabel', { round: item.step })"
      />
    </n-timeline>
    <n-empty v-if="!timeline.length" :description="$t('analysis.noTimelineData')" />
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
