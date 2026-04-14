<template>
  <div class="dashboard">
    <h1 class="page-title">工作台</h1>

    <div class="stats-grid">
      <CommonStatCard
        icon="carbon:play-outline"
        label="模拟总次数"
        :value="stats.totalSims"
        icon-bg="rgba(59, 130, 246, 0.15)"
      />
      <CommonStatCard
        icon="carbon:checkmark-outline"
        label="已完成"
        :value="stats.completedSims"
        icon-bg="rgba(34, 197, 94, 0.15)"
      />
      <CommonStatCard
        icon="carbon:cube"
        label="剩余配额"
        :value="stats.remainingQuota"
        icon-bg="rgba(139, 92, 246, 0.15)"
      />
      <CommonStatCard
        icon="carbon:report"
        label="报告数量"
        :value="stats.totalReports"
        icon-bg="rgba(245, 158, 11, 0.15)"
      />
    </div>

    <div class="dashboard-sections">
      <div class="section">
        <div class="section-header">
          <h2>快速开始</h2>
        </div>
        <div class="quick-actions">
          <NuxtLink to="/simulations/create" class="action-card">
            <Icon name="carbon:add-alt" size="24" />
            <span>新建模拟</span>
          </NuxtLink>
          <NuxtLink to="/reports" class="action-card">
            <Icon name="carbon:report" size="24" />
            <span>查看报告</span>
          </NuxtLink>
          <NuxtLink to="/templates" class="action-card">
            <Icon name="carbon:template" size="24" />
            <span>模板管理</span>
          </NuxtLink>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>最近任务</h2>
          <NuxtLink to="/simulations" class="view-all">查看全部</NuxtLink>
        </div>
        <div class="empty-state" v-if="recentSims.length === 0">
          <Icon name="carbon:no-image" size="48" />
          <p>暂无模拟任务</p>
          <NuxtLink to="/simulations/create">
            <NButton type="primary" size="small">创建第一个模拟</NButton>
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'

const authStore = useAuthStore()

const stats = computed(() => ({
  totalSims: 0,
  completedSims: 0,
  remainingQuota: authStore.enterprise?.simQuota ?? 0,
  totalReports: 0,
}))

const recentSims = ref([])
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.dashboard-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
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
}

.view-all {
  font-size: 13px;
  color: var(--accent-blue);
  text-decoration: none;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  cursor: pointer;
}

.action-card:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  background: var(--bg-hover);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
}
</style>
