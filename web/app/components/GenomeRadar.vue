<!-- web/app/components/GenomeRadar.vue -->
<template>
  <div ref="chartRef" :style="{ width: width, height: height }" />
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import * as echarts from 'echarts/core'

use([CanvasRenderer, RadarChart, TitleComponent, TooltipComponent, LegendComponent])

interface Props {
  traits: {
    openness: number
    conscientiousness: number
    extraversion: number
    agreeableness: number
    neuroticism: number
  }
  width?: string
  height?: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '300px',
  title: '人格特质',
})

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const labels = {
  openness: '开放性',
  conscientiousness: '尽责性',
  extraversion: '外向性',
  agreeableness: '宜人性',
  neuroticism: '神经质',
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  chart.setOption({
    title: { text: props.title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {},
    radar: {
      indicator: Object.entries(labels).map(([key, name]) => ({ name, max: 1 })),
      shape: 'polygon',
      splitNumber: 4,
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          props.traits.openness,
          props.traits.conscientiousness,
          props.traits.extraversion,
          props.traits.agreeableness,
          props.traits.neuroticism,
        ],
        areaStyle: { opacity: 0.3 },
      }],
    }],
  })
}

onMounted(() => renderChart())
watch(() => props.traits, () => renderChart(), { deep: true })
</script>
