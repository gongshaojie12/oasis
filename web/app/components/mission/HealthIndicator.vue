<template>
  <div class="health-indicator">
    <div ref="gaugeRef" class="health-gauge" />
    <div class="health-status" :class="statusClass">
      {{ statusText }}
    </div>
    <div class="indicator-list">
      <div v-for="ind in indicatorItems" :key="ind.key" class="indicator-row">
        <span class="indicator-label">{{ ind.label }}</span>
        <NProgress
          :percentage="ind.value * 100"
          :color="ind.color"
          :show-indicator="false"
          :height="6"
          style="flex: 1"
        />
        <span class="indicator-value">{{ Math.round(ind.value * 100) }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NProgress } from 'naive-ui'
import * as echarts from 'echarts'

const { t } = useI18n()

const props = defineProps<{
  health: {
    health_score: number
    indicators: {
      agent_activity?: number
      response_quality?: number
      action_diversity?: number
      system_load?: number
      error_rate?: number
    }
  }
}>()

const gaugeRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const statusClass = computed(() => {
  const s = props.health.health_score
  if (s >= 0.7) return 'status-good'
  if (s >= 0.4) return 'status-warning'
  return 'status-critical'
})

const statusText = computed(() => {
  const s = props.health.health_score
  if (s >= 0.7) return t('missionControl.healthGood')
  if (s >= 0.4) return t('missionControl.healthWarning')
  return t('missionControl.healthCritical')
})

const indicatorItems = computed(() => {
  const ind = props.health.indicators
  return [
    { key: 'agent_activity', label: t('missionControl.agentActivity'), value: ind.agent_activity || 0, color: '#22c55e' },
    { key: 'response_quality', label: t('missionControl.responseQuality'), value: ind.response_quality || 0, color: '#3b82f6' },
    { key: 'action_diversity', label: t('missionControl.actionDiversity'), value: ind.action_diversity || 0, color: '#8b5cf6' },
    { key: 'system_load', label: t('missionControl.systemLoad'), value: ind.system_load || 0, color: '#f59e0b' },
    { key: 'error_rate', label: t('missionControl.errorRate'), value: ind.error_rate || 0, color: '#ef4444' },
  ]
})

function getGaugeOption() {
  return {
    series: [{
      type: 'gauge',
      startAngle: 200,
      endAngle: -20,
      min: 0,
      max: 1,
      splitNumber: 10,
      itemStyle: { color: '#6385ff' },
      progress: { show: true, width: 14 },
      pointer: { show: false },
      axisLine: { lineStyle: { width: 14, color: [[0.4, '#ef4444'], [0.7, '#f59e0b'], [1, '#22c55e']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      detail: {
        valueAnimation: true,
        fontSize: 28,
        fontWeight: 700,
        offsetCenter: [0, '10%'],
        formatter: (v: number) => Math.round(v * 100) + '',
        color: 'inherit',
      },
      title: { offsetCenter: [0, '40%'], fontSize: 12, color: '#999' },
      data: [{ value: props.health.health_score, name: t('missionControl.healthScore') }],
    }],
  }
}

onMounted(() => {
  if (!gaugeRef.value) return
  chart = echarts.init(gaugeRef.value)
  chart.setOption(getGaugeOption())
  const observer = new ResizeObserver(() => chart?.resize())
  observer.observe(gaugeRef.value)
  onUnmounted(() => {
    observer.disconnect()
    chart?.dispose()
  })
})

watch(() => props.health, () => {
  chart?.setOption(getGaugeOption())
}, { deep: true })
</script>

<style scoped>
.health-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.health-gauge {
  width: 100%;
  height: 180px;
}

.health-status {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
  margin-bottom: 16px;
}

.status-good {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.status-warning {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.status-critical {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.indicator-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.indicator-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.indicator-label {
  width: 80px;
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.indicator-value {
  width: 40px;
  text-align: right;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
