<template>
  <div>
    <CommonPageHeader title="深度分析报告" :subtitle="report?.status === 'completed' ? '分析完成' : '分析中...'">
      <template #actions>
        <n-button v-if="report?.status === 'analyzing'" :loading="true" disabled>分析进行中</n-button>
      </template>
    </CommonPageHeader>

    <div v-if="report?.status === 'analyzing'">
      <n-card>
        <n-space vertical align="center">
          <n-spin size="large" />
          <n-text>正在进行多视角分析和辩论...</n-text>
          <n-progress type="line" :percentage="progress" style="width: 400px" />
        </n-space>
      </n-card>
    </div>

    <div v-if="report?.status === 'completed' && report.finalReport">
      <n-card title="执行摘要" style="margin-bottom: 16px">
        <n-text>{{ report.finalReport.executive_summary }}</n-text>
      </n-card>

      <n-grid :cols="2" :x-gap="16" style="margin-bottom: 16px">
        <n-gi>
          <n-card title="共识结论">
            <n-ul>
              <n-li v-for="(c, i) in report.finalReport.consensus" :key="i">{{ c }}</n-li>
            </n-ul>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card title="分歧观点">
            <div v-for="(d, i) in report.finalReport.disagreements" :key="i" style="margin-bottom: 8px">
              <n-tag type="warning" size="small">{{ d.topic }}</n-tag>
              <div v-for="(view, role) in d.sides" :key="role" style="margin-left: 16px; margin-top: 4px">
                <n-text depth="3">{{ roleLabel(role as string) }}：</n-text>
                <n-text>{{ view }}</n-text>
              </div>
            </div>
          </n-card>
        </n-gi>
      </n-grid>

      <TimelineNarrative :timeline="report.finalReport.timeline_narrative || []" style="margin-bottom: 16px" />

      <AnalysisDashboard :data="report.chartData" style="margin-bottom: 16px" />

      <n-card title="各分析师报告" style="margin-bottom: 16px">
        <n-tabs type="line">
          <n-tab-pane
            v-for="(ar, role) in report.analystReports"
            :key="role"
            :name="role"
            :tab="roleLabel(role)"
          >
            <n-h4>核心发现</n-h4>
            <n-ul>
              <n-li v-for="(f, i) in ar.findings" :key="i">{{ f }}</n-li>
            </n-ul>
            <n-h4>关键洞察</n-h4>
            <n-ul>
              <n-li v-for="(ins, i) in ar.key_insights" :key="i">{{ ins }}</n-li>
            </n-ul>
            <n-h4>分析叙述</n-h4>
            <n-text>{{ ar.narrative }}</n-text>
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <DebateLog :messages="report.debateLog || []" />

      <n-card title="待探索问题" v-if="report.finalReport.open_questions?.length" style="margin-top: 16px">
        <n-ul>
          <n-li v-for="(q, i) in report.finalReport.open_questions" :key="i">{{ q }}</n-li>
        </n-ul>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAnalysisStore } from '~/stores/analysis'

const route = useRoute()
const store = useAnalysisStore()

const report = ref<any>(null)
const progress = ref(0)
let pollTimer: any = null

const roleLabels: Record<string, string> = {
  data_analyst: '数据分析师',
  sociologist: '社会学家',
  psychologist: '心理学家',
  devils_advocate: '魔鬼代言人',
}

function roleLabel(role: string) { return roleLabels[role] || role }

async function loadReport() {
  const res = await store.fetchOne(route.params.id as string)
  if (res.code === 0) {
    report.value = res.data
    if (res.data.status === 'analyzing') {
      startPolling()
    }
  }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    const res = await store.fetchStatus(route.params.id as string)
    if (res.code === 0) {
      const engineStatus = res.data.engineStatus
      if (engineStatus) {
        progress.value = Math.round((engineStatus.progress || 0) * 100)
      }
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        clearInterval(pollTimer)
        await loadReport()
      }
    }
  }, 3000)
}

onMounted(() => loadReport())
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>
