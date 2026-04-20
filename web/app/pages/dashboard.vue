<template>
  <div class="dashboard">
    <h1 class="page-title">{{ $t('dashboard.title') }}</h1>

    <div class="stats-grid">
      <CommonStatCard
        icon="carbon:play-outline"
        :label="$t('dashboard.stats.totalSims')"
        :value="stats.totalSims"
        icon-bg="rgba(59, 130, 246, 0.15)"
      />
      <CommonStatCard
        icon="carbon:checkmark-outline"
        :label="$t('dashboard.stats.completed')"
        :value="stats.completedSims"
        icon-bg="rgba(34, 197, 94, 0.15)"
      />
      <CommonStatCard
        icon="carbon:cube"
        :label="$t('dashboard.stats.remainingQuota')"
        :value="stats.remainingQuota"
        icon-bg="rgba(139, 92, 246, 0.15)"
      />
      <CommonStatCard
        icon="carbon:report"
        :label="$t('dashboard.stats.reports')"
        :value="stats.totalReports"
        icon-bg="rgba(245, 158, 11, 0.15)"
      />
    </div>

    <div class="dashboard-sections">
      <div class="section">
        <div class="section-header">
          <h2>{{ $t('dashboard.quickStart') }}</h2>
        </div>
        <div class="quick-actions">
          <NuxtLink to="/simulations/create" class="action-card">
            <Icon name="carbon:add-alt" size="24" />
            <span>{{ $t('simulation.create') }}</span>
          </NuxtLink>
          <NuxtLink to="/reports" class="action-card">
            <Icon name="carbon:report" size="24" />
            <span>{{ $t('report.view') }}</span>
          </NuxtLink>
          <NuxtLink to="/templates" class="action-card">
            <Icon name="carbon:template" size="24" />
            <span>{{ $t('template.manage') }}</span>
          </NuxtLink>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>{{ $t('dashboard.recentTasks') }}</h2>
          <NuxtLink to="/simulations" class="view-all">{{ $t('common.viewAll') }}</NuxtLink>
        </div>
        <div class="empty-state" v-if="recentSims.length === 0">
          <Icon name="carbon:no-image" size="48" />
          <p>{{ $t('dashboard.noSimulations') }}</p>
          <NuxtLink to="/simulations/create">
            <NButton type="primary" size="small">{{ $t('dashboard.createFirst') }}</NButton>
          </NuxtLink>
        </div>
        <div v-else class="recent-list">
          <NuxtLink
            v-for="sim in recentSims"
            :key="sim.id"
            :to="`/simulations/${sim.id}`"
            class="recent-item"
          >
            <div class="recent-info">
              <span class="recent-name">{{ sim.name }}</span>
              <span class="recent-meta">{{ sim.platform }} · {{ sim.agentCount }} agents</span>
            </div>
            <CommonStatusTag :status="sim.status" />
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'

const authStore = useAuthStore()
const { $api } = useApi()

const usageStats = ref<any>(null)
const recentSims = ref<any[]>([])
const loading = ref(true)

const stats = computed(() => ({
  totalSims: usageStats.value?.simulations?.total ?? 0,
  completedSims: usageStats.value?.simulations?.completed ?? 0,
  remainingQuota: authStore.enterprise?.simQuota ?? 0,
  totalReports: usageStats.value?.reports ?? 0,
}))

onMounted(async () => {
  try {
    const [usageRes, simsRes] = await Promise.all([
      $api<any>('/api/enterprises/usage'),
      $api<any>('/api/simulations?pageSize=5'),
    ])
    if (usageRes.code === 0) usageStats.value = usageRes.data
    if (simsRes.code === 0) recentSims.value = simsRes.data.items
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 28px;
  color: var(--text-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-bottom: 32px;
}

.dashboard-sections {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.view-all {
  font-size: 13px;
  color: var(--accent-blue);
  text-decoration: none;
  font-weight: 500;
}

.view-all:hover {
  text-decoration: underline;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 28px;
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 52px;
  color: var(--text-secondary);
  background: #ffffff;
  border: 2px dashed var(--border-color);
  border-radius: 14px;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  text-decoration: none;
  transition: all 0.2s;
  box-shadow: var(--shadow-sm);
}

.recent-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.recent-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.recent-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.recent-meta {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
