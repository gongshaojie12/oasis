<template>
  <div>
    <CommonPageHeader :title="$t('analysis.reportTitle')" :subtitle="report?.status === 'completed' ? $t('analysis.completed') : $t('analysis.analyzing')">
      <template #actions>
        <n-button v-if="report?.status === 'analyzing'" :loading="true" disabled>{{ $t('analysis.analyzing') }}</n-button>
      </template>
    </CommonPageHeader>

    <div v-if="report?.status === 'analyzing'">
      <n-card>
        <n-space vertical align="center">
          <n-spin size="large" />
          <n-text>{{ $t('analysis.analyzingMessage') }}</n-text>
          <n-progress type="line" :percentage="progress" style="width: 400px" />
        </n-space>
      </n-card>
    </div>

    <div v-if="report?.status === 'completed' && report.finalReport">
      <n-card :title="$t('analysis.executiveSummary')" style="margin-bottom: 16px">
        <n-text>{{ report.finalReport.executive_summary }}</n-text>
      </n-card>

      <n-grid :cols="2" :x-gap="16" style="margin-bottom: 16px">
        <n-gi>
          <n-card :title="$t('analysis.consensus')">
            <n-ul>
              <n-li v-for="(c, i) in report.finalReport.consensus" :key="i">{{ c }}</n-li>
            </n-ul>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card :title="$t('analysis.disagreements')">
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

      <n-card :title="$t('analysis.analystReports')" style="margin-bottom: 16px">
        <n-tabs type="line">
          <n-tab-pane
            v-for="(ar, role) in report.analystReports"
            :key="role"
            :name="role"
            :tab="roleLabel(role)"
          >
            <n-h4>{{ $t('analysis.findings') }}</n-h4>
            <n-ul>
              <n-li v-for="(f, i) in ar.findings" :key="i">{{ f }}</n-li>
            </n-ul>
            <n-h4>{{ $t('analysis.keyInsights') }}</n-h4>
            <n-ul>
              <n-li v-for="(ins, i) in ar.key_insights" :key="i">{{ ins }}</n-li>
            </n-ul>
            <n-h4>{{ $t('analysis.narrative') }}</n-h4>
            <n-text>{{ ar.narrative }}</n-text>
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <DebateLog :messages="report.debateLog || []" />

      <n-card :title="$t('analysis.openQuestions')" v-if="report.finalReport.open_questions?.length" style="margin-top: 16px">
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
const { $t } = useI18n()

const report = ref<any>(null)
const progress = ref(0)
let pollTimer: any = null

const roleLabels = computed<Record<string, string>>(() => ({
  data_analyst: $t('analysis.roles.data_analyst'),
  sociologist: $t('analysis.roles.sociologist'),
  psychologist: $t('analysis.roles.psychologist'),
  devils_advocate: $t('analysis.roles.devils_advocate'),
}))

function roleLabel(role: string) { return roleLabels.value[role] || role }

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
