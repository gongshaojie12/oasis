<template>
  <div class="dna-mixer">
    <h3>{{ t('composer.mixerTitle') }}</h3>
    <div class="mixer-scenes">
      <div class="mixer-scene">
        <h4>{{ t('composer.sceneA') }}</h4>
        <NSelect v-model:value="selectedA" :options="templateOptions" size="small" :placeholder="t('composer.sceneA')" />
        <DNARadarChart v-if="dnaA" :dna="dnaA" :size="200" />
      </div>

      <div class="mixer-controls">
        <div class="weight-display">A: {{ Math.round(weightA * 100) }}% / B: {{ Math.round((1 - weightA) * 100) }}%</div>
        <NSlider v-model:value="weightA" :min="0" :max="1" :step="0.05" vertical style="height: 160px" />
        <NButton type="primary" size="small" :loading="composerStore.mixing" :disabled="!dnaA || !dnaB" @click="handleMix">
          {{ t('composer.mixBtn') }}
        </NButton>
      </div>

      <div class="mixer-scene">
        <h4>{{ t('composer.sceneB') }}</h4>
        <NSelect v-model:value="selectedB" :options="templateOptions" size="small" :placeholder="t('composer.sceneB')" />
        <DNARadarChart v-if="dnaB" :dna="dnaB" :size="200" />
      </div>
    </div>

    <div v-if="composerStore.mixing" class="mixing-hint">
      <NSpin size="small" />
      <span>{{ t('composer.mixing') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NSelect, NSlider, NButton, NSpin } from 'naive-ui'
import { useComposerStore } from '~/stores/composer'
import type { ScenarioDNA } from '~/stores/composer'
import DNARadarChart from './DNARadarChart.vue'

const { t } = useI18n()
const composerStore = useComposerStore()

const props = defineProps<{
  templates: {
    description: string
    dna: ScenarioDNA | null
  }[]
}>()

const emit = defineEmits<{
  mixed: [config: any]
}>()

const selectedA = ref<number | null>(null)
const selectedB = ref<number | null>(null)
const weightA = ref(0.5)

const templateOptions = computed(() =>
  props.templates.map((t, i) => ({ label: t.description, value: i }))
)

const dnaA = computed(() => {
  if (selectedA.value === null) return null
  return props.templates[selectedA.value]?.dna || null
})

const dnaB = computed(() => {
  if (selectedB.value === null) return null
  return props.templates[selectedB.value]?.dna || null
})

async function handleMix() {
  if (!dnaA.value || !dnaB.value) return
  try {
    const config = await composerStore.mix(dnaA.value, dnaB.value, weightA.value)
    emit('mixed', config)
  } catch {}
}
</script>

<style scoped>
.dna-mixer h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.mixer-scenes {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: start;
}

.mixer-scene h4 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.mixer-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-top: 30px;
}

.weight-display {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.mixing-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
