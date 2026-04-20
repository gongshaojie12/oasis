<template>
  <div class="parameter-panel">
    <div class="param-section">
      <h4>{{ t('simulation.agentCount') }}</h4>
      <NSlider v-model:value="localConfig.num_agents" :min="1" :max="10000" :step="10" @update:value="emitUpdate" />
      <NInputNumber v-model:value="localConfig.num_agents" :min="1" :max="100000" size="small" style="width: 120px; margin-top: 8px" @update:value="emitUpdate" />
    </div>

    <div class="param-section">
      <h4>{{ t('simulation.timeSteps') }}</h4>
      <NSlider v-model:value="localConfig.num_steps" :min="1" :max="200" :step="1" @update:value="emitUpdate" />
      <NInputNumber v-model:value="localConfig.num_steps" :min="1" :max="1000" size="small" style="width: 120px; margin-top: 8px" @update:value="emitUpdate" />
    </div>

    <div v-if="localConfig.agent_groups.length > 0" class="param-section">
      <h4>{{ t('composer.agentGroups') }}</h4>
      <div ref="pieRef" class="agent-pie-chart" />
      <div class="group-list">
        <div v-for="(group, idx) in localConfig.agent_groups" :key="idx" class="group-item">
          <span class="group-name">{{ group.name }}</span>
          <NInputNumber v-model:value="group.ratio" :min="0" :max="1" :step="0.05" size="small" style="width: 90px" @update:value="emitUpdate" />
        </div>
      </div>
    </div>

    <div class="param-section">
      <div class="section-header">
        <h4>{{ t('composer.eventInjections') }}</h4>
        <NButton size="tiny" @click="addEvent">{{ t('composer.addEvent') }}</NButton>
      </div>
      <div v-for="(evt, idx) in localConfig.event_injections" :key="idx" class="event-item">
        <NInputNumber v-model:value="evt.round" :min="1" :max="localConfig.num_steps" size="small" style="width: 80px" :placeholder="t('composer.eventRound')" />
        <NInput v-model:value="evt.content" size="small" :placeholder="t('composer.eventContent')" style="flex: 1" />
        <NButton size="tiny" quaternary type="error" @click="removeEvent(idx)">{{ t('composer.removeEvent') }}</NButton>
      </div>
    </div>

    <div v-if="estimate" class="param-section estimate-card">
      <h4>{{ t('composer.estimateTitle') }}</h4>
      <div class="estimate-grid">
        <div class="estimate-item">
          <span class="estimate-label">{{ t('composer.llmCalls') }}</span>
          <span class="estimate-value">{{ estimate.llm_calls.toLocaleString() }}</span>
        </div>
        <div class="estimate-item">
          <span class="estimate-label">{{ t('composer.estimatedTokens') }}</span>
          <span class="estimate-value">{{ estimate.estimated_tokens.toLocaleString() }}</span>
        </div>
        <div class="estimate-item">
          <span class="estimate-label">{{ t('composer.estimatedTime') }}</span>
          <span class="estimate-value">{{ estimate.estimated_minutes }} {{ t('composer.minutes') }}</span>
        </div>
        <div class="estimate-item">
          <span class="estimate-label">{{ t('composer.estimatedCost') }}</span>
          <span class="estimate-value">${{ estimate.estimated_cost_usd }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NSlider, NInputNumber, NInput, NButton } from 'naive-ui'
import * as echarts from 'echarts'

const { t } = useI18n()

const props = defineProps<{
  config: {
    num_agents: number
    num_steps: number
    agent_groups: { name: string; ratio: number; stance_range: number[] }[]
    event_injections: { round: number; content: string }[]
  }
  estimate: {
    llm_calls: number
    estimated_tokens: number
    estimated_minutes: number
    estimated_cost_usd: number
  } | null
}>()

const emit = defineEmits<{
  'update:config': [config: any]
  'request-estimate': []
}>()

const localConfig = reactive({
  num_agents: props.config.num_agents,
  num_steps: props.config.num_steps,
  agent_groups: [...props.config.agent_groups],
  event_injections: [...props.config.event_injections],
})

watch(() => props.config, (val) => {
  localConfig.num_agents = val.num_agents
  localConfig.num_steps = val.num_steps
  localConfig.agent_groups = [...val.agent_groups]
  localConfig.event_injections = [...val.event_injections]
}, { deep: true })

const pieRef = ref<HTMLElement>()
let pieChart: echarts.ECharts | null = null

function updatePie() {
  if (!pieChart || localConfig.agent_groups.length === 0) return
  pieChart.setOption({
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: localConfig.agent_groups.map(g => ({ name: g.name, value: g.ratio })),
      label: { fontSize: 11 },
    }],
  })
}

onMounted(() => {
  if (pieRef.value) {
    pieChart = echarts.init(pieRef.value)
    updatePie()
    const observer = new ResizeObserver(() => pieChart?.resize())
    observer.observe(pieRef.value)
    onUnmounted(() => {
      observer.disconnect()
      pieChart?.dispose()
    })
  }
})

watch(() => localConfig.agent_groups, updatePie, { deep: true })

function emitUpdate() {
  emit('update:config', { ...localConfig })
  emit('request-estimate')
}

function addEvent() {
  localConfig.event_injections.push({ round: 1, content: '' })
}

function removeEvent(idx: number) {
  localConfig.event_injections.splice(idx, 1)
  emitUpdate()
}
</script>

<style scoped>
.parameter-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.param-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.section-header h4 {
  margin-bottom: 0;
}

.agent-pie-chart {
  height: 200px;
  margin-bottom: 12px;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 8px;
}

.group-name {
  font-size: 13px;
  color: var(--text-primary);
}

.event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.estimate-card {
  background: #f0f4ff;
  border-radius: 12px;
  padding: 16px;
}

.estimate-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.estimate-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.estimate-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.estimate-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
