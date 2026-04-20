<template>
  <n-grid :cols="2" :x-gap="16" :y-gap="16" v-if="snapshot">
    <n-gi>
      <n-card :title="$t('timeMachine.roundMetrics')" size="small">
        <n-space vertical>
          <n-text>{{ $t('timeMachine.totalActions') }}: {{ snapshot.metrics.total_actions }}</n-text>
          <n-text>{{ $t('timeMachine.newPosts') }}: {{ snapshot.metrics.total_posts_this_round }}</n-text>
        </n-space>
        <div ref="actionChartRef" style="height: 200px; margin-top: 12px" />
      </n-card>
    </n-gi>
    <n-gi>
      <n-card :title="$t('timeMachine.activeAgents')" size="small">
        <n-list :show-divider="false" style="max-height: 280px; overflow-y: auto">
          <n-list-item v-for="a in snapshot.agent_summaries" :key="a.agent_id">
            <n-space justify="space-between" align="center" style="width: 100%">
              <n-button
                text
                type="primary"
                @click="$emit('selectAgent', a.agent_id, a.user_name)"
              >
                {{ a.user_name }}
              </n-button>
              <n-space>
                <n-tag size="tiny" type="info">{{ $t('timeMachine.actionCount', { count: a.action_count }) }}</n-tag>
              </n-space>
            </n-space>
          </n-list-item>
        </n-list>
      </n-card>
    </n-gi>
    <n-gi :span="2" v-if="snapshot.posts.length">
      <n-card :title="$t('timeMachine.roundPosts')" size="small">
        <n-list :show-divider="false" style="max-height: 300px; overflow-y: auto">
          <n-list-item v-for="(p, idx) in snapshot.posts.slice(0, 20)" :key="idx">
            <n-text depth="3" style="font-size: 12px">Agent {{ p.user_id }}:</n-text>
            <n-text>{{ p.content }}</n-text>
          </n-list-item>
        </n-list>
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

echarts.use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const props = defineProps<{ snapshot: any }>()
defineEmits<{ selectAgent: [agentId: number, agentName: string] }>()

const actionChartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!actionChartRef.value || !props.snapshot) return
  if (!chart) {
    chart = echarts.init(actionChartRef.value)
  }
  const dist = props.snapshot.metrics.action_distribution || {}
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['35%', '65%'],
      data: Object.entries(dist).map(([name, value]) => ({ name, value })),
    }],
  }, true)
}

watch(() => props.snapshot, () => nextTick(renderChart), { immediate: true, deep: true })
onUnmounted(() => { if (chart) { chart.dispose(); chart = null } })
</script>
