<template>
  <div class="settings-page">
    <CommonPageHeader :title="$t('settings.title')" />

    <NTabs type="line" v-model:value="activeTab">
      <!-- Enterprise Info -->
      <NTabPane name="info" :tab="$t('settings.tabs.info')">
        <NCard class="settings-card">
          <NForm label-placement="left" label-width="100">
            <NFormItem :label="$t('settings.enterpriseName')">
              <NInput v-model:value="enterpriseForm.name" />
            </NFormItem>
            <NFormItem :label="$t('settings.contactPhone')">
              <NInput v-model:value="enterpriseForm.contactPhone" />
            </NFormItem>
            <NFormItem>
              <NButton type="primary" :loading="savingEnterprise" @click="saveEnterprise">
                {{ $t('common.saveChanges') }}
              </NButton>
            </NFormItem>
          </NForm>

          <NDivider />

          <h3 class="section-title">{{ $t('settings.teamMembers') }}</h3>
          <NDataTable
            :columns="memberColumns"
            :data="members"
            :bordered="false"
            size="small"
          />
        </NCard>
      </NTabPane>

      <!-- Plan & Quota -->
      <NTabPane name="plan" :tab="$t('settings.tabs.plan')">
        <NCard class="settings-card">
          <div class="quota-grid">
            <CommonStatCard icon="carbon:cube" :label="$t('settings.currentPlan')" :value="authStore.enterprise?.planType || 'basic'" icon-bg="rgba(59,130,246,0.15)" />
            <CommonStatCard icon="carbon:calculator" :label="$t('settings.remainingQuota')" :value="String(authStore.enterprise?.simQuota ?? 0)" icon-bg="rgba(139,92,246,0.15)" />
            <CommonStatCard icon="carbon:calendar" :label="$t('settings.expiryDate')" :value="authStore.enterprise?.quotaExpires ? new Date(authStore.enterprise.quotaExpires).toLocaleDateString('zh-CN') : $t('settings.unlimited')" icon-bg="rgba(245,158,11,0.15)" />
          </div>

          <NDivider />

          <h3 class="section-title">{{ $t('settings.usageStats') }}</h3>
          <div v-if="usageStats" class="usage-grid">
            <div class="usage-item"><span class="usage-label">{{ $t('settings.usage.totalSims') }}</span><span class="usage-value">{{ usageStats.simulations.total }}</span></div>
            <div class="usage-item"><span class="usage-label">{{ $t('settings.usage.completed') }}</span><span class="usage-value">{{ usageStats.simulations.completed }}</span></div>
            <div class="usage-item"><span class="usage-label">{{ $t('settings.usage.running') }}</span><span class="usage-value">{{ usageStats.simulations.running }}</span></div>
            <div class="usage-item"><span class="usage-label">{{ $t('settings.usage.failed') }}</span><span class="usage-value">{{ usageStats.simulations.failed }}</span></div>
            <div class="usage-item"><span class="usage-label">{{ $t('settings.usage.reports') }}</span><span class="usage-value">{{ usageStats.reports }}</span></div>
            <div class="usage-item"><span class="usage-label">{{ $t('settings.usage.llmCost') }}</span><span class="usage-value">{{ usageStats.llm.totalCost }} {{ $t('settings.currency') }}</span></div>
          </div>
        </NCard>
      </NTabPane>

      <!-- LLM Keys -->
      <NTabPane name="keys" :tab="$t('settings.tabs.keys')">
        <NCard class="settings-card">
          <p class="hint-text">{{ $t('settings.keyHint') }}</p>
          <div class="keys-list">
            <div v-for="provider in providers" :key="provider.id" class="key-item">
              <div class="key-info">
                <strong>{{ provider.name }}</strong>
                <NTag v-if="provider.hasKey" type="success" size="small">{{ $t('settings.configured') }}</NTag>
                <NTag v-else type="default" size="small">{{ $t('settings.notConfigured') }}</NTag>
              </div>
              <div class="key-actions">
                <NButton size="small" @click="openKeyModal(provider)">
                  {{ provider.hasKey ? $t('settings.update') : $t('settings.configure') }}
                </NButton>
                <NButton v-if="provider.hasKey" size="small" type="error" quaternary @click="deleteKey(provider.id)">
                  {{ $t('common.delete') }}
                </NButton>
              </div>
            </div>
          </div>
        </NCard>

        <!-- Key Modal -->
        <NModal v-model:show="showKeyModal" preset="dialog" :title="$t('settings.configureKey', { provider: keyForm.providerName })" style="width: 450px">
          <NForm label-placement="top">
            <NFormItem :label="$t('settings.apiKey')">
              <NInput v-model:value="keyForm.apiKey" type="password" show-password-on="click" :placeholder="$t('settings.apiKeyPlaceholder')" />
            </NFormItem>
          </NForm>
          <template #action>
            <NButton @click="showKeyModal = false">{{ $t('common.cancel') }}</NButton>
            <NButton :loading="testingKey" @click="testKey">{{ $t('settings.testConnection') }}</NButton>
            <NButton type="primary" :loading="savingKey" @click="saveKey">{{ $t('common.save') }}</NButton>
          </template>
        </NModal>
      </NTabPane>

      <!-- Logs -->
      <NTabPane name="logs" :tab="$t('settings.tabs.logs')">
        <NCard class="settings-card">
          <NDataTable
            :columns="logColumns"
            :data="logs"
            :loading="loadingLogs"
            :bordered="false"
            size="small"
          />
        </NCard>
      </NTabPane>
    </NTabs>
  </div>
</template>

<script setup lang="ts">
import {
  NTabs, NTabPane, NCard, NForm, NFormItem, NInput, NButton,
  NDataTable, NDivider, NTag, NModal,
} from 'naive-ui'

const { $api } = useApi()
const authStore = useAuthStore()
const message = useMessage()
const { $t } = useI18n()

const activeTab = ref('info')

// Enterprise Info
const enterpriseForm = reactive({ name: '', contactPhone: '' })
const members = ref<any[]>([])
const savingEnterprise = ref(false)

const memberColumns = computed(() => [
  { title: $t('settings.memberName'), key: 'name' },
  { title: $t('settings.memberPhone'), key: 'phone' },
  { title: $t('settings.memberRole'), key: 'role', width: 80 },
  { title: $t('settings.lastLogin'), key: 'lastLoginAt', width: 180,
    render: (row: any) => row.lastLoginAt ? new Date(row.lastLoginAt).toLocaleString('zh-CN') : '-',
  },
])

// Usage Stats
const usageStats = ref<any>(null)

// LLM Keys
const providers = ref<any[]>([])
const showKeyModal = ref(false)
const keyForm = reactive({ provider: '', providerName: '', apiKey: '' })
const savingKey = ref(false)
const testingKey = ref(false)

// Logs
const logs = ref<any[]>([])
const loadingLogs = ref(false)

const actionNameMap = computed<Record<string, string>>(() => ({
  create: $t('settings.actions.create'), update: $t('settings.actions.update'), delete: $t('common.delete'), cancel: $t('common.cancel'), retry: $t('common.retry'),
}))

const resourceNameMap = computed<Record<string, string>>(() => ({
  simulation: $t('simulation.title'), template: $t('template.title'), enterprise: $t('settings.enterpriseInfo'), llm_key: $t('settings.apiKey'),
}))

const logColumns = computed(() => [
  { title: $t('settings.operator'), key: 'userName', width: 100 },
  { title: $t('settings.action'), key: 'action', width: 80,
    render: (row: any) => actionNameMap.value[row.action] || row.action,
  },
  { title: $t('settings.resource'), key: 'resourceType', width: 100,
    render: (row: any) => resourceNameMap.value[row.resourceType] || row.resourceType,
  },
  { title: $t('settings.details'), key: 'details', ellipsis: { tooltip: true },
    render: (row: any) => row.details ? JSON.stringify(row.details) : '-',
  },
  { title: $t('common.time'), key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
])

async function loadEnterpriseInfo() {
  const res = await $api<any>('/api/enterprises/current')
  if (res.code === 0) {
    enterpriseForm.name = res.data.name
    enterpriseForm.contactPhone = res.data.contactPhone || ''
    members.value = res.data.members || []
  }
}

async function saveEnterprise() {
  savingEnterprise.value = true
  const res = await $api<any>('/api/enterprises/current', {
    method: 'PUT',
    body: { name: enterpriseForm.name, contactPhone: enterpriseForm.contactPhone || undefined },
  })
  savingEnterprise.value = false
  if (res.code === 0) {
    message.success($t('common.updateSuccess'))
    await authStore.fetchMe()
  } else {
    message.error(res.message)
  }
}

async function loadUsage() {
  const res = await $api<any>('/api/enterprises/usage')
  if (res.code === 0) usageStats.value = res.data
}

async function loadProviders() {
  const res = await $api<any>('/api/llm/providers')
  if (res.code === 0) providers.value = res.data
}

function openKeyModal(provider: any) {
  keyForm.provider = provider.id
  keyForm.providerName = provider.name
  keyForm.apiKey = ''
  showKeyModal.value = true
}

async function testKey() {
  if (!keyForm.apiKey) { message.warning($t('settings.apiKeyRequired')); return }
  testingKey.value = true
  const res = await $api<any>('/api/llm/keys/test', {
    method: 'POST',
    body: { provider: keyForm.provider, apiKey: keyForm.apiKey },
  })
  testingKey.value = false
  if (res.code === 0 && res.data.connected) {
    message.success($t('settings.connectionSuccess'))
  } else {
    message.error(res.data?.reason || $t('settings.connectionFailed'))
  }
}

async function saveKey() {
  if (!keyForm.apiKey) { message.warning($t('settings.apiKeyRequired')); return }
  savingKey.value = true
  const res = await $api<any>('/api/llm/keys', {
    method: 'POST',
    body: { provider: keyForm.provider, apiKey: keyForm.apiKey },
  })
  savingKey.value = false
  if (res.code === 0) {
    message.success($t('common.saveSuccess'))
    showKeyModal.value = false
    await loadProviders()
  } else {
    message.error(res.message)
  }
}

async function deleteKey(provider: string) {
  const res = await $api<any>(`/api/llm/keys/${provider}`, { method: 'DELETE' })
  if (res.code === 0) {
    message.success($t('common.deleteSuccess'))
    await loadProviders()
  } else {
    message.error(res.message)
  }
}

async function loadLogs() {
  loadingLogs.value = true
  const res = await $api<any>('/api/enterprises/logs')
  if (res.code === 0) logs.value = res.data.items || []
  loadingLogs.value = false
}

onMounted(() => {
  loadEnterpriseInfo()
  loadUsage()
  loadProviders()
  loadLogs()
})
</script>

<style scoped>
.settings-page {
  max-width: 1000px;
}

.settings-card {
  background: #ffffff !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow-sm);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.hint-text {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.quota-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.usage-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.usage-item {
  display: flex;
  justify-content: space-between;
  padding: 14px;
  background: #f8f9fc;
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.usage-label { font-size: 13px; color: var(--text-secondary); }
.usage-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }

.keys-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.key-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: #f8f9fc;
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.key-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.key-actions {
  display: flex;
  gap: 8px;
}
</style>
