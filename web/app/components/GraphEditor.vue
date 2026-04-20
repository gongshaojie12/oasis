<template>
  <div style="position: relative; width: 100%; height: 100%">
    <div ref="chartRef" style="width: 100%; height: 100%" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

echarts.use([CanvasRenderer, GraphChart, TooltipComponent, LegendComponent])

interface Node { id: string; type: string; label: string; x: number; y: number; properties: any }
interface Edge { id: string; source: string; target: string; type: string; weight: number; properties: any }

const props = defineProps<{
  nodes: Node[]
  edges: Edge[]
}>()

const emit = defineEmits<{
  nodeClick: [node: Node]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const categoryColors: Record<string, string> = {
  person: '#5470c6',
  organization: '#91cc75',
  topic: '#fac858',
  community: '#ee6666',
  content: '#73c0de',
}

const categoryNames: Record<string, string> = {
  person: '人物',
  organization: '组织',
  topic: '话题',
  community: '社区',
  content: '内容',
}

function getCategories() {
  return Object.entries(categoryNames).map(([key, name]) => ({ name }))
}

function getCategoryIndex(type: string) {
  const keys = Object.keys(categoryNames)
  return keys.indexOf(type)
}

function render() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', (params: any) => {
      if (params.dataType === 'node') {
        const node = props.nodes.find(n => n.id === params.data.id)
        if (node) emit('nodeClick', node)
      }
    })
  }

  const echartsNodes = props.nodes.map(n => ({
    id: n.id,
    name: n.label,
    x: n.x || Math.random() * 600,
    y: n.y || Math.random() * 400,
    symbolSize: n.type === 'person' ? 40 : 30,
    category: getCategoryIndex(n.type),
    itemStyle: { color: categoryColors[n.type] || '#999' },
    label: { show: true, position: 'bottom', fontSize: 11 },
  }))

  const edgeTypeLabels: Record<string, string> = {
    follows: '关注', opposes: '对立', belongs_to: '隶属',
    interested_in: '兴趣', influences: '影响', publishes: '发布',
  }

  const echartsEdges = props.edges.map(e => ({
    source: e.source,
    target: e.target,
    label: { show: true, formatter: edgeTypeLabels[e.type] || e.type, fontSize: 9 },
    lineStyle: {
      width: Math.max(1, e.weight * 2),
      curveness: 0.2,
      type: e.type === 'opposes' ? 'dashed' as const : 'solid' as const,
    },
  }))

  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: getCategories().map(c => c.name), top: 10 },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      force: { repulsion: 200, edgeLength: [80, 200], gravity: 0.1 },
      categories: getCategories(),
      data: echartsNodes,
      links: echartsEdges,
      emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
    }],
  }, true)
}

onMounted(() => nextTick(render))
onUnmounted(() => { if (chart) { chart.dispose(); chart = null } })
watch([() => props.nodes, () => props.edges], () => nextTick(render), { deep: true })
</script>
