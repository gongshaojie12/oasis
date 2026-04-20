<template>
  <n-card title="数据仪表盘">
    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <n-gi>
        <n-card title="帖子数量趋势" size="small">
          <div ref="timelineChartRef" style="height: 250px" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="行为类型分布" size="small">
          <div ref="actionChartRef" style="height: 250px" />
        </n-card>
      </n-gi>
      <n-gi :span="2">
        <n-card title="Agent 活跃度排行" size="small">
          <div ref="agentChartRef" style="height: 250px" />
        </n-card>
      </n-gi>
    </n-grid>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components'

echarts.use([CanvasRenderer, LineChart, PieChart, BarChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent])

interface ChartData {
  posts_timeline: { step: number; count: number }[]
  action_distribution: { action: string; count: number }[]
  top_agents: { agent_id: number; actions: number }[]
}

const props = defineProps<{ data: ChartData | null }>()

const timelineChartRef = ref<HTMLElement>()
const actionChartRef = ref<HTMLElement>()
const agentChartRef = ref<HTMLElement>()
const chartInstances: echarts.ECharts[] = []

function initChart(el: HTMLElement): echarts.ECharts {
  const existing = echarts.getInstanceByDom(el)
  if (existing) return existing
  const instance = echarts.init(el)
  chartInstances.push(instance)
  return instance
}

function render() {
  if (!props.data) return

  if (timelineChartRef.value) {
    const chart = initChart(timelineChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: props.data.posts_timeline.map(d => `第${d.step}轮`) },
      yAxis: { type: 'value' },
      series: [{ type: 'line', data: props.data.posts_timeline.map(d => d.count), smooth: true, areaStyle: { opacity: 0.3 } }],
    })
  }

  if (actionChartRef.value) {
    const chart = initChart(actionChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        data: props.data.action_distribution.map(d => ({ name: d.action, value: d.count })),
      }],
    })
  }

  if (agentChartRef.value) {
    const chart = initChart(agentChartRef.value)
    chart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: props.data.top_agents.map(d => `Agent ${d.agent_id}`) },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: props.data.top_agents.map(d => d.actions), itemStyle: { color: '#2080f0' } }],
    })
  }
}

onMounted(() => nextTick(render))
onUnmounted(() => chartInstances.forEach(c => c.dispose()))
watch(() => props.data, () => nextTick(render), { deep: true })
</script>
