<template>
  <div class="settings-page">
    <CommonPageHeader title="企业设置" />

    <NTabs type="line" v-model:value="activeTab">
      <!-- Enterprise Info -->
      <NTabPane name="info" tab="企业信息">
        <NCard class="settings-card">
          <NForm label-placement="left" label-width="100">
            <NFormItem label="企业名称">
              <NInput v-model:value="enterpriseForm.name" />
            </NFormItem>
            <NFormItem label="联系电话">
              <NInput v-model:value="enterpriseForm.contactPhone" />
            </NFormItem>
            <NFormItem>
              <NButton type="primary" :loading="savingEnterprise" @click="saveEnterprise">
                保存修改
              </NButton>
            </NFormItem>
          </NForm>

          <NDivider />

          <h3 class="section-title">团队成员</h3>
          <NDataTable
            :columns="memberColumns"
            :data="members"
            :bordered="false"
            size="small"
          />
        </NCard>
      </NTabPane>

      <!-- Plan & Quota -->
      <NTabPane name="plan" tab="套餐与配额">
        <NCard class="settings-card">
          <div class="quota-grid">
            <CommonStatCard icon="carbon:cube" label="当前套餐" :value="authStore.enterprise?.planType || 'basic'" icon-bg="rgba(59,130,246,0.15)" />
            <CommonStatCard icon="carbon:calculator" label="剩余配额" :value="String(authStore.enterprise?.simQuota ?? 0)" icon-bg="rgba(139,92,246,0.15)" />
            <CommonStatCard icon="carbon:calendar" label="到期时间" :value="authStore.enterprise?.quotaExpires ? new Date(authStore.enterprise.quotaExpires).toLocaleDateString('zh-CN') : '无限期'" icon-bg="rgba(245,158,11,0.15)" />
          </div>

          <NDivider />

          <h3 class="section-title">用量统计</h3>
          <div v-if="usageStats" class="usage-grid">
            <div class="usage-item"><span class="usage-label">总模拟次数</span><span class="usage-value">{{ usageStats.simulations.total }}</span></div>
            <div class="usage-item"><span class="usage-label">已完成</span><span class="usage-value">{{ usageStats.simulations.completed }}</span></div>
            <div class="usage-item"><span class="usage-label">运行中</span><span class="usage-value">{{ usageStats.simulations.running }}</span></div>
            <div class="usage-item"><span class="usage-label">失败</span><span class="usage-value">{{ usageStats.simulations.failed }}</span></div>
            <div class="usage-item"><span class="usage-label">报告数量</span><span class="usage-value">{{ usageStats.reports }}</span></div>
            <div class="usage-item"><span class="usage-label">LLM 总消耗</span><span class="usage-value">{{ usageStats.llm.totalCost }} 元</span></div>
          </div>
        </NCard>
      </NTabPane>

      <!-- LLM Keys -->
      <NTabPane name="keys" tab="API Key 管理">
        <NCard class="settings-card">
          <p class="hint-text">配置自有 API Key 后，模拟将使用您的 Key 调用 LLM 服务</p>
          <div class="keys-list">
            <div v-for="provider in providers" :key="provider.id" class="key-item">
              <div class="key-info">
                <strong>{{ provider.name }}</strong>
                <NTag v-if="provider.hasKey" type="success" size="small">已配置</NTag>
                <NTag v-else type="default" size="small">未配置</NTag>
              </div>
              <div class="key-actions">
                <NButton size="small" @click="openKeyModal(provider)">
                  {{ provider.hasKey ? '更新' : '配置' }}
                </NButton>
                <NButton v-if="provider.hasKey" size="small" type="error" quaternary @click="deleteKey(provider.id)">
                  删除
                </NButton>
              </div>
            </div>
          </div>
        </NCard>

        <!-- Key Modal -->
        <NModal v-model:show="showKeyModal" preset="dialog" :title="`配置 ${keyForm.providerName} API Key`" style="width: 450px">
          <NForm label-placement="top">
            <NFormItem label="API Key">
              <NInput v-model:value="keyForm.apiKey" type="password" show-password-on="click" placeholder="输入 API Key" />
            </NFormItem>
          </NForm>
          <template #action>
            <NButton @click="showKeyModal = false">取消</NButton>
            <NButton :loading="testingKey" @click="testKey">测试连通性</NButton>
            <NButton type="primary" :loading="savingKey" @click="saveKey">保存</NButton>
          </template>
        </NModal>
      </NTabPane>

      <!-- Logs -->
      <NTabPane name="logs" tab="操作日志">
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

const activeTab = ref('info')

// Enterprise Info
const enterpriseForm = reactive({ name: '', contactPhone: '' })
const members = ref<any[]>([])
const savingEnterprise = ref(false)

const memberColumns = [
  { title: '姓名', key: 'name' },
  { title: '手机号', key: 'phone' },
  { title: '角色', key: 'role', width: 80 },
  { title: '最后登录', key: 'lastLoginAt', width: 180,
    render: (row: any) => row.lastLoginAt ? new Date(row.lastLoginAt).toLocaleString('zh-CN') : '-',
  },
]

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

const actionNameMap: Record<string, string> = {
  create: '创建', update: '更新', delete: '删除', cancel: '取消', retry: '重试',
}

const resourceNameMap: Record<string, string> = {
  simulation: '模拟任务', template: '模板', enterprise: '企业信息', llm_key: 'API Key',
}

const logColumns = [
  { title: '操作人', key: 'userName', width: 100 },
  { title: '操作', key: 'action', width: 80,
    render: (row: any) => actionNameMap[row.action] || row.action,
  },
  { title: '资源', key: 'resourceType', width: 100,
    render: (row: any) => resourceNameMap[row.resourceType] || row.resourceType,
  },
  { title: '详情', key: 'details', ellipsis: { tooltip: true },
    render: (row: any) => row.details ? JSON.stringify(row.details) : '-',
  },
  { title: '时间', key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
]

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
    message.success('已更新')
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
  if (!keyForm.apiKey) { message.warning('请输入 API Key'); return }
  testingKey.value = true
  const res = await $api<any>('/api/llm/keys/test', {
    method: 'POST',
    body: { provider: keyForm.provider, apiKey: keyForm.apiKey },
  })
  testingKey.value = false
  if (res.code === 0 && res.data.connected) {
    message.success('连接成功')
  } else {
    message.error(res.data?.reason || '连接失败')
  }
}

async function saveKey() {
  if (!keyForm.apiKey) { message.warning('请输入 API Key'); return }
  savingKey.value = true
  const res = await $api<any>('/api/llm/keys', {
    method: 'POST',
    body: { provider: keyForm.provider, apiKey: keyForm.apiKey },
  })
  savingKey.value = false
  if (res.code === 0) {
    message.success('已保存')
    showKeyModal.value = false
    await loadProviders()
  } else {
    message.error(res.message)
  }
}

async function deleteKey(provider: string) {
  const res = await $api<any>(`/api/llm/keys/${provider}`, { method: 'DELETE' })
  if (res.code === 0) {
    message.success('已删除')
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
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
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
  padding: 12px;
  background: var(--bg-primary);
  border-radius: 8px;
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
  padding: 12px 16px;
  background: var(--bg-primary);
  border-radius: 8px;
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
