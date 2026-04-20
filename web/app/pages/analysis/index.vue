<template>
  <div>
    <CommonPageHeader :title="$t('analysis.title')" :subtitle="$t('analysis.subtitle')" />

    <n-card>
      <n-empty v-if="!reports.length && !loading" :description="$t('analysis.noData')">
        <template #extra>
          <n-button type="primary" @click="router.push('/simulations')">{{ $t('analysis.goToSimulations') }}</n-button>
        </template>
      </n-empty>

      <n-spin v-if="loading" size="large" style="display: flex; justify-content: center; padding: 40px" />

      <div v-if="reports.length" class="report-list">
        <n-card
          v-for="r in reports"
          :key="r.id"
          size="small"
          hoverable
          style="cursor: pointer; margin-bottom: 12px"
          @click="router.push(`/analysis/${r.id}`)"
        >
          <n-space justify="space-between" align="center">
            <n-space align="center">
              <n-tag :type="statusType(r.status)" size="small">{{ statusLabel(r.status) }}</n-tag>
              <n-text>{{ r.simulationId }}</n-text>
            </n-space>
            <n-text depth="3">{{ formatTime(r.createdAt) }}</n-text>
          </n-space>
        </n-card>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const router = useRouter()
const loading = ref(true)
const reports = ref<any[]>([])
const { $t } = useI18n()

function statusType(s: string): 'info' | 'success' | 'error' | 'warning' {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'analyzing') return 'warning'
  return 'info'
}

function statusLabel(s: string) {
  const map = computed<Record<string, string>>(() => ({
    pending: $t('simulation.status.pending'),
    analyzing: $t('analysis.status.analyzing'),
    completed: $t('simulation.status.completed'),
    failed: $t('simulation.status.failed')
  }))
  return map.value[s] || s
}

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(async () => {
  const { $api } = useApi()
  try {
    const res = await $api<any>('/api/analysis')
    if (res.code === 0) reports.value = res.data || []
  } catch {}
  loading.value = false
})
</script>
