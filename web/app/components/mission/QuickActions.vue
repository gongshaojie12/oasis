<template>
  <div class="quick-actions">
    <div class="actions-grid">
      <NuxtLink
        v-for="action in filteredActions"
        :key="action.path"
        :to="action.path"
        class="action-card"
      >
        <div class="action-icon" :style="{ background: action.bg }">
          <Icon :name="action.icon" size="20" />
        </div>
        <span>{{ action.label }}</span>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
const { t } = useI18n()

const props = defineProps<{
  stage: 'prepare' | 'launch' | 'monitor' | 'analyze' | 'idle'
  activeSim?: { id: string } | null
}>()

const allActions = computed(() => [
  { key: 'newSim', path: '/simulations/create', icon: 'carbon:add-alt', label: t('missionControl.quickNewSim'), bg: 'rgba(59, 130, 246, 0.15)', stages: ['idle', 'prepare', 'analyze'] },
  { key: 'viewReport', path: '/reports', icon: 'carbon:report', label: t('missionControl.quickViewReport'), bg: 'rgba(245, 158, 11, 0.15)', stages: ['analyze', 'idle'] },
  { key: 'timeMachine', path: props.activeSim ? `/simulations/${props.activeSim.id}/timemachine` : '/simulations', icon: 'carbon:time', label: t('missionControl.quickTimeMachine'), bg: 'rgba(139, 92, 246, 0.15)', stages: ['analyze'] },
  { key: 'manageGenome', path: '/genomes', icon: 'carbon:dna', label: t('missionControl.quickManageGenome'), bg: 'rgba(34, 197, 94, 0.15)', stages: ['idle', 'prepare'] },
  { key: 'importTemplate', path: '/templates', icon: 'carbon:template', label: t('missionControl.quickImportTemplate'), bg: 'rgba(236, 72, 153, 0.15)', stages: ['idle', 'prepare'] },
  { key: 'viewProgress', path: props.activeSim ? `/simulations/${props.activeSim.id}` : '/simulations', icon: 'carbon:activity', label: t('missionControl.quickViewProgress'), bg: 'rgba(59, 130, 246, 0.15)', stages: ['monitor', 'launch'] },
  { key: 'analysis', path: '/analysis', icon: 'carbon:data-vis-4', label: t('missionControl.quickAnalysis'), bg: 'rgba(139, 92, 246, 0.15)', stages: ['analyze'] },
])

const filteredActions = computed(() =>
  allActions.value.filter(a => a.stages.includes(props.stage))
)
</script>

<style scoped>
.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 22px 16px;
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.action-card:hover {
  box-shadow: var(--shadow-md);
  color: var(--accent-blue);
  transform: translateY(-2px);
}

.action-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
}
</style>
