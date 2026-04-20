<template>
  <NCard class="event-injector">
    <h3>{{ t('liveControl.injectEvent') }}</h3>
    <div class="inject-form">
      <NInput
        v-model:value="eventContent"
        type="textarea"
        :placeholder="t('liveControl.injectPlaceholder')"
        :rows="3"
      />
      <div class="inject-actions">
        <NInputNumber v-model:value="agentId" size="small" :placeholder="'Agent ID'" :min="0" style="width: 120px" clearable />
        <NButton type="primary" :disabled="!eventContent.trim()" @click="handleInject">
          {{ t('liveControl.injectBtn') }}
        </NButton>
      </div>
    </div>
  </NCard>
</template>

<script setup lang="ts">
import { NCard, NInput, NInputNumber, NButton } from 'naive-ui'

const { t } = useI18n()
const message = useMessage()

const props = defineProps<{
  onInject: (content: string, agentId?: number) => void
}>()

const eventContent = ref('')
const agentId = ref<number | null>(null)

function handleInject() {
  if (!eventContent.value.trim()) return
  props.onInject(eventContent.value, agentId.value || undefined)
  message.success(t('liveControl.injectSuccess'))
  eventContent.value = ''
  agentId.value = null
}
</script>

<style scoped>
.event-injector {
  background: #ffffff !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow-sm);
}

.event-injector h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.inject-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.inject-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: flex-end;
}
</style>
