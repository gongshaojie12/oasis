<template>
  <div class="create-page">
    <CommonPageHeader :title="$t('simulation.create')" :subtitle="$t('simulation.createSubtitle')" />

    <NSteps :current="currentStep" class="wizard-steps">
      <NStep :title="$t('simulation.wizard.step1')" />
      <NStep :title="$t('simulation.wizard.step2')" />
      <NStep :title="$t('simulation.wizard.step3')" />
    </NSteps>

    <NCard class="wizard-content">
      <!-- Step 1: Business Type -->
      <div v-if="currentStep === 1">
        <h3 class="step-title">{{ $t('simulation.selectBusinessType') }}</h3>
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
        <h3 class="step-title">{{ $t('simulation.configureParameters') }}</h3>
        <NForm label-placement="left" label-width="100">
          <NFormItem :label="$t('simulation.name')">
            <NInput v-model:value="form.name" :placeholder="$t('simulation.namePlaceholder')" maxlength="100" />
          </NFormItem>
          <NFormItem :label="$t('simulation.selectPlatform')">
            <NSelect v-model:value="form.platform" :options="platformOptions" :placeholder="$t('simulation.selectPlatform')" />
          </NFormItem>
          <NFormItem :label="$t('simulation.agentCount')">
            <NInputNumber v-model:value="form.agentCount" :min="1" :max="100000" :step="10" style="width: 100%" />
          </NFormItem>
          <NFormItem :label="$t('simulation.timeSteps')">
            <NInputNumber v-model:value="form.timeSteps" :min="1" :max="1000" style="width: 100%" />
          </NFormItem>
          <NFormItem :label="$t('simulation.seedContent')">
            <NInput v-model:value="form.seedContent" type="textarea" :placeholder="$t('simulation.seedContentPlaceholder')" :rows="3" />
          </NFormItem>
        </NForm>
      </div>

      <!-- Step 3: Confirm -->
      <div v-if="currentStep === 3">
        <h3 class="step-title">{{ $t('simulation.confirmConfig') }}</h3>
        <div class="confirm-grid">
          <div class="confirm-item">
            <span class="confirm-label">{{ $t('simulation.businessType') }}</span>
            <span class="confirm-value">{{ getTypeName(form.type) }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">{{ $t('simulation.name') }}</span>
            <span class="confirm-value">{{ form.name }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">{{ $t('common.platform') }}</span>
            <span class="confirm-value">{{ getPlatformName(form.platform) }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">{{ $t('simulation.agentCount') }}</span>
            <span class="confirm-value">{{ form.agentCount }}</span>
          </div>
          <div class="confirm-item">
            <span class="confirm-label">{{ $t('simulation.timeSteps') }}</span>
            <span class="confirm-value">{{ form.timeSteps }}</span>
          </div>
          <div v-if="form.seedContent" class="confirm-item">
            <span class="confirm-label">{{ $t('simulation.seedContent') }}</span>
            <span class="confirm-value">{{ form.seedContent }}</span>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="wizard-nav">
        <NButton v-if="currentStep > 1" @click="currentStep--">{{ $t('common.previous') }}</NButton>
        <div class="wizard-nav-spacer" />
        <NButton
          v-if="currentStep < 3"
          type="primary"
          :disabled="!canProceed"
          @click="currentStep++"
        >
          {{ $t('common.next') }}
        </NButton>
        <NButton
          v-if="currentStep === 3"
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ $t('simulation.submit') }}
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
const { $t } = useI18n()

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

const businessTypes = computed(() => [
  { value: 'marketing_sim', label: $t('simulation.types.marketing_sim'), icon: 'carbon:bullhorn', desc: $t('simulation.typeDesc.marketing_sim') },
  { value: 'sentiment_predict', label: $t('simulation.types.sentiment_predict'), icon: 'carbon:warning-alt', desc: $t('simulation.typeDesc.sentiment_predict') },
  { value: 'recsys_test', label: $t('simulation.types.recsys_test'), icon: 'carbon:recommend', desc: $t('simulation.typeDesc.recsys_test') },
  { value: 'research', label: $t('simulation.types.research'), icon: 'carbon:research--bloch-sphere', desc: $t('simulation.typeDesc.research') },
  { value: 'digital_twin', label: $t('simulation.types.digital_twin'), icon: 'carbon:ibm-cloud-direct-link-2-dedicated', desc: $t('simulation.typeDesc.digital_twin') },
  { value: 'synthetic_data', label: $t('simulation.types.synthetic_data'), icon: 'carbon:data-base', desc: $t('simulation.typeDesc.synthetic_data') },
])

const platformOptions = [
  { label: 'Twitter', value: 'twitter' },
  { label: 'Reddit', value: 'reddit' },
  { label: $t('common.platforms.weibo'), value: 'weibo' },
  { label: $t('common.platforms.xiaohongshu'), value: 'xiaohongshu' },
  { label: $t('common.platforms.douyin'), value: 'douyin' },
  { label: $t('common.platforms.kuaishou'), value: 'kuaishou' },
  { label: $t('common.platforms.bilibili'), value: 'bilibili' },
  { label: $t('common.platforms.wechat_video'), value: 'wechat_video' },
]

const canProceed = computed(() => {
  if (currentStep.value === 1) return !!form.type
  if (currentStep.value === 2) return !!form.name && !!form.platform
  return true
})

function getTypeName(type: string) {
  return businessTypes.value.find(t => t.value === type)?.label || type
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
      message.success($t('simulation.submitSuccess'))
      await router.push(`/simulations/${res.data.id}`)
    } else {
      message.error(res.message)
    }
  } catch {
    message.error($t('common.submitFailed'))
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
  margin-bottom: 28px;
}

.wizard-content {
  background: #ffffff !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow-sm);
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
  gap: 14px;
}

.type-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 22px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-primary);
}

.type-card:hover {
  border-color: var(--accent-blue);
  box-shadow: var(--shadow-sm);
}

.type-card.selected {
  border-color: var(--accent-blue);
  background: #eef1fe;
  box-shadow: 0 0 0 1px var(--accent-blue);
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
  font-weight: 500;
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
