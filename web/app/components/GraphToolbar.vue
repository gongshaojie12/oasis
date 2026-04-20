<template>
  <n-space>
    <n-dropdown :options="nodeOptions" @select="$emit('addNode', $event)">
      <n-button type="primary" size="small">{{ $t('worldBuilder.addNode') }}</n-button>
    </n-dropdown>
    <n-button size="small" @click="$emit('autoLayout')">{{ $t('worldBuilder.autoLayout') }}</n-button>
    <n-button size="small" @click="$emit('analyze')">{{ $t('worldBuilder.runAnalysis') }}</n-button>
    <n-button size="small" @click="$emit('exportJson')">{{ $t('worldBuilder.exportJson') }}</n-button>
    <n-button size="small" type="info" @click="$emit('toSimulation')">{{ $t('worldBuilder.toSimulation') }}</n-button>
  </n-space>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

defineEmits<{
  addNode: [type: string]
  autoLayout: []
  analyze: []
  exportJson: []
  toSimulation: []
}>()

const { t } = useI18n()

const nodeOptions = computed(() => [
  { label: `${t('worldBuilder.nodeTypes.person')} (Person)`, key: 'person' },
  { label: `${t('worldBuilder.nodeTypes.organization')} (Organization)`, key: 'organization' },
  { label: `${t('worldBuilder.nodeTypes.topic')} (Topic)`, key: 'topic' },
  { label: `${t('worldBuilder.nodeTypes.community')} (Community)`, key: 'community' },
  { label: `${t('worldBuilder.nodeTypes.content')} (Content)`, key: 'content' },
])
</script>
