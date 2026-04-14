<template>
  <div class="create-page">
    <CommonPageHeader title="新建模拟" subtitle="配置模拟参数并提交" />

    <NSteps :current="currentStep" class="wizard-steps">
      <NStep title="选择业务类型" />
      <NStep title="配置参数" />
      <NStep title="确认提交" />
    </NSteps>

    <NCard class="wizard-content">
      <!-- Step 1: Business Type -->
      <div v-if="currentStep === 1">
        <h3 class="step-title">选择业务方向</h3>
        <div class="type-grid">
          <div
            v-for="t in businessTypes"
            :key="t.value"
            class="type-card"
            :class="{ selected: form.type === t.value }"
            @click="form.type = t.value"
          >
            <Icon :name="t.icon" size="32" />
            <strong>{{ t.label }}</strong>
            <p>{{ t.desc }}</p>
          </div>
        </div>
      </div>

      <!-- Step 2: Platform + Parameters -->
      <div v-if="currentStep === 2">
        <h3 class="step-title">配置模拟参数</h3>
        <NForm label-placement="left" label-width="100">
          <NFormItem label="模拟名称">
            <NInput v-model:value="form.name" placeholder="例如：新品推广微博模拟" maxlength="100" />
          </NFormItem>
          <NFormItem label="选择平台">
            <NSelect v-model:value="form.platform" :options="platformOptions" placeholder="选择平台" />
          </NFormItem>
          <NFormItem label="Agent 数量">
            <NInputNumber v-model:value="form.agentCount" :min="1" :max="100000" :step="10" style="width: 100%" />
          </NFormItem>
          <NFormItem label="模拟轮次">
            <NInputNumber v-model:value="form.timeSteps" :min="1" :max="1000" style="width: 100%" />
          </NFormItem>
          <NFormItem label="初始内容">
            <NInput v-model:value="form.seedContent" type="textarea" placeholder="可选：模拟的种子内容/话题（留空则由 Agent 自由互动）" :rows="3" />
          </NFormItem>
        </NForm>
      </div>

      <!-- Step 3: Confirm -->
      <div v-if="currentStep === 3">
        <h3 class="step-title">确认模拟配置</h3>
        <div class="confirm-grid">
          <div class="confirm-item">
            <span class="confirm-label">业务类型</span>
            <span class="confirm-value">{{ getTypeName(form.type) }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">模拟名称</span>
            <span class="confirm-value">{{ form.name }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">平台</span>
            <span class="confirm-value">{{ getPlatformName(form.platform) }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">Agent 数量</span>
            <span class="confirm-value">{{ form.agentCount }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">模拟轮次</span>
            <span class="confirm-value">{{ form.timeSteps }}</span>
          </div>
          <div v-if="form.seedContent" class="confirm-item">
            <span class="confirm-label">初始内容</span>
            <span class="confirm-value">{{ form.seedContent }}</span>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="wizard-nav">
        <NButton v-if="currentStep > 1" @click="currentStep--">上一步</NButton>
        <div class="wizard-nav-spacer" />
        <NButton
          v-if="currentStep < 3"
          type="primary"
          :disabled="!canProceed"
          @click="currentStep++"
        >
          下一步
        </NButton>
        <NButton
          v-if="currentStep === 3"
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          提交模拟
        </NButton>
      </div>
    </NCard>
  </div>
</template>

<script setup lang="ts">
import {
  NCard, NSteps, NStep, NForm, NFormItem, NInput,
  NInputNumber, NSelect, NButton,
} from 'naive-ui'
import { useSimulationsStore } from '~/stores/simulations'

const store = useSimulationsStore()
const message = useMessage()
const router = useRouter()

const currentStep = ref(1)
const submitting = ref(false)

const form = reactive({
  name: '',
  type: '',
  platform: '',
  agentCount: 50,
  timeSteps: 10,
  seedContent: '',
})

const businessTypes = [
  { value: 'marketing_sim', label: '社交营销模拟', icon: 'carbon:bullhorn', desc: '品牌投放前预演策略效果' },
  { value: 'sentiment_predict', label: '舆情预测预警', icon: 'carbon:warning-alt', desc: '模拟危机事件传播与公关响应' },
  { value: 'recsys_test', label: '推荐算法测试', icon: 'carbon:recommend', desc: '测试推荐策略对用户行为影响' },
  { value: 'research', label: '社会科学研究', icon: 'carbon:research--bloch-sphere', desc: '学术研究模拟社会现象' },
  { value: 'digital_twin', label: '数字孪生社区', icon: 'carbon:ibm-cloud-direct-link-2-dedicated', desc: '创建目标社区的数字镜像' },
  { value: 'synthetic_data', label: '合成数据工厂', icon: 'carbon:data-base', desc: '批量生成高质量训练数据' },
]

const platformOptions = [
  { label: 'Twitter', value: 'twitter' },
  { label: 'Reddit', value: 'reddit' },
  { label: '微博', value: 'weibo' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '抖音', value: 'douyin' },
  { label: '快手', value: 'kuaishou' },
  { label: 'B站', value: 'bilibili' },
  { label: '微信视频号', value: 'wechat_video' },
]

const canProceed = computed(() => {
  if (currentStep.value === 1) return !!form.type
  if (currentStep.value === 2) return !!form.name && !!form.platform
  return true
})

function getTypeName(type: string) {
  return businessTypes.find(t => t.value === type)?.label || type
}

function getPlatformName(platform: string) {
  return platformOptions.find(p => p.value === platform)?.label || platform
}

async function handleSubmit() {
  submitting.value = true
  try {
    const res = await store.create({
      name: form.name,
      type: form.type,
      platform: form.platform,
      agentCount: form.agentCount,
      timeSteps: form.timeSteps,
      seedContent: form.seedContent || undefined,
    })
    if (res.code === 0) {
      message.success('模拟任务已提交')
      await router.push(`/simulations/${res.data.id}`)
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.create-page {
  max-width: 900px;
}

.wizard-steps {
  margin-bottom: 24px;
}

.wizard-content {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-primary);
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.type-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-primary);
}

.type-card:hover {
  border-color: var(--accent-blue);
}

.type-card.selected {
  border-color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.08);
}

.type-card strong {
  font-size: 14px;
  color: var(--text-primary);
}

.type-card p {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.confirm-grid {
  display: grid;
  gap: 16px;
}

.confirm-item {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.confirm-label {
  flex-shrink: 0;
  width: 100px;
  font-size: 14px;
  color: var(--text-secondary);
}

.confirm-value {
  font-size: 14px;
  color: var(--text-primary);
}

.wizard-nav {
  display: flex;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.wizard-nav-spacer {
  flex: 1;
}
</style>
