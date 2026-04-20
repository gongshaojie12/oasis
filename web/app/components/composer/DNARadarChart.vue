<template>
  <div ref="chartRef" class="dna-radar-chart" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts'

const { t } = useI18n()

const props = defineProps<{
  dna: {
    conflict_level: number
    information_density: number
    viral_potential: number
    sentiment_polarity: number
    agent_diversity: number
  }
  editable?: boolean
  size?: number
}>()

const emit = defineEmits<{
  'update:dna': [dna: any]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const dimensions = computed(() => [
  { key: 'conflict_level', label: t('composer.dnaConflict') },
  { key: 'information_density', label: t('composer.dnaInfoDensity') },
  { key: 'viral_potential', label: t('composer.dnaViralPotential') },
  { key: 'sentiment_polarity', label: t('composer.dnaSentiment') },
  { key: 'agent_diversity', label: t('composer.dnaDiversity') },
])

function getOption() {
  return {
    radar: {
      indicator: dimensions.value.map(d => ({ name: d.label, max: 1 })),
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#666', fontSize: 11 },
      splitArea: { areaStyle: { color: ['rgba(99,133,255,0.05)', 'rgba(99,133,255,0.1)'] } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: dimensions.value.map(d => (props.dna as any)[d.key] || 0),
        areaStyle: { color: 'rgba(99,133,255,0.25)' },
        lineStyle: { color: '#6385ff', width: 2 },
        itemStyle: { color: '#6385ff' },
      }],
    }],
  }
}

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(getOption())

  const observer = new ResizeObserver(() => chart?.resize())
  observer.observe(chartRef.value)
  onUnmounted(() => {
    observer.disconnect()
    chart?.dispose()
  })
})

watch(() => props.dna, () => {
  chart?.setOption(getOption())
}, { deep: true })
</script>

<style scoped>
.dna-radar-chart {
  width: 100%;
  height: v-bind('(props.size || 280) + "px"');
}
</style>
