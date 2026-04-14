<template>
  <div class="detail-page">
    <CommonPageHeader :title="sim?.name || '模拟详情'">
      <template #actions>
        <NSpace>
          <NButton v-if="canCancel" type="warning" @click="handleCancel" :loading="cancelling">取消</NButton>
          <NButton v-if="canRetry" type="info" @click="handleRetry" :loading="retrying">重试</NButton>
          <NButton @click="router.push('/simulations')">返回列表</NButton>
        </NSpace>
      </template>
    </CommonPageHeader>

    <NSpin :show="loading">
      <div v-if="sim" class="detail-content">
        <!-- Status + Progress -->
        <NCard class="info-card">
          <div class="status-bar">
            <CommonStatusTag :status="displayStatus" />
            <span class="progress-text">{{ displayProgress }}%</span>
          </div>
          <NProgress
            :percentage="displayProgress"
            :status="progressStatus"
            :show-indicator="false"
            :height="8"
            class="progress-bar"
          />
          <div v-if="sse.currentStep.value > 0" class="step-info">
            步骤 {{ sse.currentStep.value }} / {{ sse.totalSteps.value }}
          </div>
          <div v-if="displayError" class="error-info">
            <Icon name="carbon:warning" size="16" />
            {{ displayError }}
          </div>
        </NCard>

        <!-- Details Grid -->
        <div class="info-grid">
          <NCard class="info-card">
            <h3 class="card-title">基本信息</h3>
            <div class="detail-list">
              <div class="detail-row"><span class="label">名称</span><span>{{ sim.name }}</span></div>
              <div class="detail-row"><span class="label">类型</span><span>{{ typeNameMap[sim.type] || sim.type }}</span></div>
              <div class="detail-row"><span class="label">平台</span><span>{{ platformNameMap[sim.platform] || sim.platform }}</span></div>
              <div class="detail-row"><span class="label">Agent 数量</span><span>{{ sim.agentCount || '-' }}</span></div>
              <div class="detail-row"><span class="label">模拟轮次</span><span>{{ sim.timeSteps || '-' }}</span></div>
              <div class="detail-row"><span class="label">LLM 模型</span><span>{{ sim.llmModel || '默认' }}</span></div>
            </div>
          </NCard>

          <NCard class="info-card">
            <h3 class="card-title">时间信息</h3>
            <div class="detail-list">
              <div class="detail-row"><span class="label">创建时间</span><span>{{ formatTime(sim.createdAt) }}</span></div>
              <div class="detail-row"><span class="label">开始时间</span><span>{{ formatTime(sim.startedAt) }}</span></div>
              <div class="detail-row"><span class="label">完成时间</span><span>{{ formatTime(sim.completedAt) }}</span></div>
            </div>
          </NCard>
        </div>
      </div>
    </NSpin>
  </div>
</template>

<script setup lang="ts">
import { NCard, NProgress, NButton, NSpace, NSpin } from 'naive-ui'
import { useSimulationsStore } from '~/stores/simulations'
import { useSSE } from '~/composables/useSSE'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const store = useSimulationsStore()

const id = route.params.id as string
const loading = ref(true)
const cancelling = ref(false)
const retrying = ref(false)

const sim = computed(() => store.currentSimulation)

const sse = useSSE(id)

const typeNameMap: Record<string, string> = {
  marketing_sim: '社交营销', sentiment_predict: '舆情预测', recsys_test: '推荐算法',
  research: '社会研究', digital_twin: '数字孪生', synthetic_data: '合成数据',
}

const platformNameMap: Record<string, string> = {
  twitter: 'Twitter', reddit: 'Reddit', weibo: '微博',
  xiaohongshu: '小红书', douyin: '抖音', kuaishou: '快手',
  bilibili: 'B站', wechat_video: '视频号',
}

const displayStatus = computed(() => sse.status.value || sim.value?.status || 'pending')
const displayProgress = computed(() => sse.progress.value || sim.value?.progress || 0)
const displayError = computed(() => sse.error.value || sim.value?.errorMessage)

const canCancel = computed(() => ['pending', 'running'].includes(displayStatus.value))
const canRetry = computed(() => ['failed', 'cancelled'].includes(displayStatus.value))

const progressStatus = computed(() => {
  if (displayStatus.value === 'completed') return 'success'
  if (displayStatus.value === 'failed') return 'error'
  return 'default'
})

function formatTime(t: string | null | undefined) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function handleCancel() {
  cancelling.value = true
  const res = await store.cancel(id)
  cancelling.value = false
  if (res.code === 0) {
    message.success('已取消')
    await store.fetchOne(id)
  } else {
    message.error(res.message)
  }
}

async function handleRetry() {
  retrying.value = true
  const res = await store.retry(id)
  retrying.value = false
  if (res.code === 0) {
    message.success('已重新提交')
    await store.fetchOne(id)
    sse.connect()
  } else {
    message.error(res.message)
  }
}

onMounted(async () => {
  await store.fetchOne(id)
  loading.value = false

  // Connect SSE for active simulations
  if (sim.value && ['pending', 'running'].includes(sim.value.status)) {
    sse.connect()
  }
})
</script>

<style scoped>
.detail-page {
  max-width: 1000px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.progress-text {
  font-size: 24px;
  font-weight: 600;
  color: var(--accent-blue);
}

.progress-bar {
  margin-bottom: 8px;
}

.step-info {
  font-size: 13px;
  color: var(--text-secondary);
}

.error-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 8px;
  color: var(--error);
  font-size: 13px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.detail-row .label {
  color: var(--text-secondary);
}
</style>
