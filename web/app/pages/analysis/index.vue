<template>
  <div>
    <CommonPageHeader title="深度分析" subtitle="多视角辩论式仿真分析报告" />

    <n-card>
      <n-empty v-if="!reports.length && !loading" description="暂无分析报告，请在完成的仿真任务中点击「生成深度分析报告」">
        <template #extra>
          <n-button type="primary" @click="router.push('/simulations')">前往仿真任务</n-button>
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

function statusType(s: string): 'info' | 'success' | 'error' | 'warning' {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'analyzing') return 'warning'
  return 'info'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '等待中', analyzing: '分析中', completed: '已完成', failed: '失败' }
  return map[s] || s
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
