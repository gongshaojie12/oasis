<!-- web/app/components/PopulationPreview.vue -->
<template>
  <n-card title="群体画像预览" v-if="data">
    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <n-gi>
        <n-statistic label="总人数" :value="data.count" />
      </n-gi>
      <n-gi>
        <n-statistic label="平均年龄" :value="data.ageDistribution.mean" />
      </n-gi>
    </n-grid>

    <n-divider />
    <n-h4>五大人格分布</n-h4>
    <div ref="traitChartRef" style="width: 100%; height: 250px" />

    <n-divider />
    <n-h4>活跃度分布</n-h4>
    <div ref="activityChartRef" style="width: 100%; height: 200px" />

    <n-divider />
    <n-h4>职业分布</n-h4>
    <div ref="professionChartRef" style="width: 100%; height: 250px" />
  </n-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TitleComponent, TooltipComponent } from 'echarts/components'

echarts.use([CanvasRenderer, BarChart, PieChart, GridComponent, TitleComponent, TooltipComponent])

interface PreviewData {
  count: number
  traitDistribution: Record<string, { mean: number; std: number }>
  ageDistribution: { values: number[]; mean: number }
  activityDistribution: { values: number[]; mean: number }
  professionCounts: Record<string, number>
}

const props = defineProps<{ data: PreviewData | null }>()

const traitChartRef = ref<HTMLElement>()
const activityChartRef = ref<HTMLElement>()
const professionChartRef = ref<HTMLElement>()

const traitLabels: Record<string, string> = {
  openness: '开放性', conscientiousness: '尽责性', extraversion: '外向性',
  agreeableness: '宜人性', neuroticism: '神经质',
}

function renderCharts() {
  if (!props.data) return

  if (traitChartRef.value) {
    const chart = echarts.init(traitChartRef.value)
    const keys = Object.keys(props.data.traitDistribution)
    chart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: keys.map(k => traitLabels[k] || k) },
      yAxis: { type: 'value', max: 1 },
      series: [{
        type: 'bar', data: keys.map(k => props.data!.traitDistribution[k].mean),
        itemStyle: { color: '#18a058' },
      }],
    })
  }

  if (activityChartRef.value) {
    const chart = echarts.init(activityChartRef.value)
    const bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    const counts = new Array(bins.length - 1).fill(0)
    for (const v of props.data.activityDistribution.values) {
      const idx = Math.min(Math.floor(v * 5), 4)
      counts[idx]++
    }
    chart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: ['极低', '低', '中', '高', '极高'] },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: counts, itemStyle: { color: '#2080f0' } }],
    })
  }

  if (professionChartRef.value) {
    const chart = echarts.init(professionChartRef.value)
    const entries = Object.entries(props.data.professionCounts)
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: '60%',
        data: entries.map(([name, value]) => ({ name, value })),
      }],
    })
  }
}

onMounted(() => { nextTick(renderCharts) })
watch(() => props.data, () => { nextTick(renderCharts) }, { deep: true })
</script>
