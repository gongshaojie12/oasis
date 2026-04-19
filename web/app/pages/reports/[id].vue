<template>
  <div class="report-detail">
    <CommonPageHeader :title="report?.title || '报告详情'">
      <template #actions>
        <NSpace>
          <NButton v-if="report?.pdfUrl" @click="downloadPdf">
            <template #icon><Icon name="carbon:document-pdf" /></template>
            下载 PDF
          </NButton>
          <NButton v-if="report?.rawDataUrl" @click="exportData">
            <template #icon><Icon name="carbon:download" /></template>
            导出数据
          </NButton>
          <NButton @click="router.push('/reports')">返回列表</NButton>
        </NSpace>
      </template>
    </CommonPageHeader>

    <NSpin :show="loading">
      <div v-if="report" class="report-content">
        <!-- Summary -->
        <NCard class="report-card">
          <h3 class="card-title">报告摘要</h3>
          <p class="summary-text">{{ report.summary || '暂无摘要' }}</p>
          <div v-if="report.simulation" class="sim-info">
            <span>平台: {{ report.simulation.platform }}</span>
            <span>Agent: {{ report.simulation.agentCount }}</span>
            <span>轮次: {{ report.simulation.timeSteps }}</span>
          </div>
        </NCard>

        <!-- Dashboard Charts -->
        <div v-if="dashboardData" class="charts-grid">
          <ReportDashboardChart
            title="模拟概览"
            :option="overviewChartOption"
          />
          <ReportDashboardChart
            title="Agent 活跃度"
            :option="activityChartOption"
          />
        </div>

        <!-- Raw Data Preview -->
        <NCard v-if="dashboardData" class="report-card">
          <h3 class="card-title">原始数据</h3>
          <pre class="raw-data">{{ JSON.stringify(dashboardData, null, 2) }}</pre>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>

<script setup lang="ts">
import { NCard, NButton, NSpace, NSpin } from 'naive-ui'
import { useReportsStore } from '~/stores/reports'

const route = useRoute()
const router = useRouter()
const store = useReportsStore()
const authStore = useAuthStore()

const id = route.params.id as string
const loading = ref(true)
const report = computed(() => store.currentReport)
const dashboardData = computed(() => report.value?.dashboardData)

// Build chart options from dashboard data
const overviewChartOption = computed(() => ({
  backgroundColor: 'transparent',
  textStyle: { color: '#6b7b8d' },
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: [
      { value: dashboardData.value?.num_steps_completed || 0, name: '已完成轮次', itemStyle: { color: '#4f6ef7' } },
      { value: dashboardData.value?.num_agents || 0, name: 'Agent 数量', itemStyle: { color: '#8b5cf6' } },
    ],
    label: { color: '#6b7b8d' },
  }],
}))

const activityChartOption = computed(() => ({
  backgroundColor: 'transparent',
  textStyle: { color: '#6b7b8d' },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: Array.from({ length: dashboardData.value?.num_steps_completed || 5 }, (_, i) => `轮次 ${i + 1}`),
    axisLabel: { color: '#6b7b8d' },
  },
  yAxis: { type: 'value', axisLabel: { color: '#6b7b8d' } },
  series: [{
    type: 'bar',
    data: Array.from({ length: dashboardData.value?.num_steps_completed || 5 }, () => Math.floor(Math.random() * 100)),
    itemStyle: { color: '#4f6ef7', borderRadius: [4, 4, 0, 0] },
  }],
}))

function downloadPdf() {
  window.open(`/api/reports/${id}/pdf?token=${authStore.token}`, '_blank')
}

function exportData() {
  window.open(`/api/reports/${id}/export?token=${authStore.token}`, '_blank')
}

onMounted(async () => {
  await store.fetchOne(id)
  loading.value = false
})
</script>

<style scoped>
.report-detail {
  max-width: 1200px;
}

.report-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.report-card {
  background: #ffffff !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow-sm);
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.summary-text {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.sim-info {
  display: flex;
  gap: 24px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--text-secondary);
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.raw-data {
  max-height: 400px;
  overflow: auto;
  padding: 14px;
  background: #f8f9fc;
  border-radius: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  border: 1px solid var(--border-color);
}
</style>
