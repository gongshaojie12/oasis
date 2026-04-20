<template>
  <NCard class="live-control-panel">
    <div class="control-header">
      <h3>{{ t('liveControl.controlPanel') }}</h3>
      <NBadge :dot="true" :type="ws.connected.value ? 'success' : 'error'">
        <span class="conn-status">{{ ws.connected.value ? t('liveControl.connected') : t('liveControl.disconnected') }}</span>
      </NBadge>
    </div>

    <div class="control-row">
      <NButtonGroup>
        <NButton :type="ws.status.value === 'running' ? 'warning' : 'default'" @click="ws.pause()">
          <template #icon><Icon name="carbon:pause" size="16" /></template>
          {{ t('liveControl.pause') }}
        </NButton>
        <NButton type="primary" @click="ws.resume()">
          <template #icon><Icon name="carbon:play" size="16" /></template>
          {{ t('liveControl.resume') }}
        </NButton>
        <NButton @click="ws.step()">
          <template #icon><Icon name="carbon:skip-forward-filled" size="16" /></template>
          {{ t('liveControl.step') }}
        </NButton>
      </NButtonGroup>
    </div>

    <div class="control-row">
      <span class="speed-label">{{ t('liveControl.speedLabel') }}</span>
      <NButtonGroup size="small">
        <NButton v-for="s in speeds" :key="s" :type="currentSpeed === s ? 'primary' : 'default'" @click="changeSpeed(s)">
          {{ s }}x
        </NButton>
      </NButtonGroup>
    </div>

    <div class="control-row">
      <span class="round-label">{{ t('liveControl.currentRound') }}: {{ ws.currentStep.value }}</span>
      <NProgress :percentage="ws.progress.value" :show-indicator="false" :height="6" style="flex: 1; margin-left: 12px" />
    </div>
  </NCard>
</template>

<script setup lang="ts">
import { NCard, NButton, NButtonGroup, NBadge, NProgress } from 'naive-ui'

const { t } = useI18n()

const props = defineProps<{
  ws: {
    connected: Ref<boolean>
    status: Ref<string>
    progress: Ref<number>
    currentStep: Ref<number>
    pause: () => void
    resume: () => void
    step: () => void
    setSpeed: (speed: number) => void
  }
}>()

const speeds = [0.5, 1, 2, 4]
const currentSpeed = ref(1)

function changeSpeed(speed: number) {
  currentSpeed.value = speed
  props.ws.setSpeed(speed)
}
</script>

<style scoped>
.live-control-panel {
  background: #ffffff !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow-sm);
}

.control-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.control-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.conn-status {
  font-size: 12px;
  color: var(--text-secondary);
}

.control-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.speed-label, .round-label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}
</style>
