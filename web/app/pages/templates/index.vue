<template>
  <div class="templates-page">
    <CommonPageHeader :title="$t('template.title')" />

    <NTabs type="line" v-model:value="activeTab">
      <!-- Agent Templates Tab -->
      <NTabPane name="agents" :tab="$t('template.agentTemplates')">
        <div class="tab-header">
          <NButton type="primary" size="small" @click="showAgentModal = true">
            <template #icon><Icon name="carbon:add" /></template>
            {{ $t('template.createAgent') }}
          </NButton>
        </div>

        <NDataTable
          :columns="agentColumns"
          :data="agentTemplates"
          :loading="loadingAgents"
          :row-key="(row: any) => row.id"
          :bordered="false"
        />
      </NTabPane>

      <!-- Simulation Templates Tab -->
      <NTabPane name="simulations" :tab="$t('template.simulationTemplates')">
        <div class="tab-header">
          <NButton type="primary" size="small" @click="showSimModal = true">
            <template #icon><Icon name="carbon:add" /></template>
            {{ $t('template.createSimulation') }}
          </NButton>
        </div>

        <NDataTable
          :columns="simColumns"
          :data="simTemplates"
          :loading="loadingSims"
          :row-key="(row: any) => row.id"
          :bordered="false"
        />
      </NTabPane>
    </NTabs>

    <!-- Agent Template Modal -->
    <NModal v-model:show="showAgentModal" preset="dialog" :title="$t('template.createAgent')" style="width: 500px">
      <NForm label-placement="left" label-width="80">
        <NFormItem :label="$t('template.name')">
          <NInput v-model:value="agentForm.name" :placeholder="$t('template.name')" />
        </NFormItem>
        <NFormItem :label="$t('common.platform')">
          <NSelect v-model:value="agentForm.platform" :options="platformOptions" :placeholder="$t('template.selectPlatform')" />
        </NFormItem>
        <NFormItem :label="$t('template.profileConfig')">
          <NInput v-model:value="agentForm.profileConfigStr" type="textarea" :rows="6" :placeholder="$t('template.profileConfigPlaceholder')" />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="showAgentModal = false">{{ $t('common.cancel') }}</NButton>
        <NButton type="primary" :loading="savingAgent" @click="saveAgentTemplate">{{ $t('common.save') }}</NButton>
      </template>
    </NModal>

    <!-- Simulation Template Modal -->
    <NModal v-model:show="showSimModal" preset="dialog" :title="$t('template.createSimulation')" style="width: 500px">
      <NForm label-placement="left" label-width="80">
        <NFormItem :label="$t('template.name')">
          <NInput v-model:value="simForm.name" :placeholder="$t('template.name')" />
        </NFormItem>
        <NFormItem :label="$t('simulation.businessType')">
          <NSelect v-model:value="simForm.type" :options="typeOptions" :placeholder="$t('template.selectType')" />
        </NFormItem>
        <NFormItem :label="$t('common.platform')">
          <NSelect v-model:value="simForm.platform" :options="platformOptions" :placeholder="$t('template.selectPlatform')" />
        </NFormItem>
        <NFormItem :label="$t('template.config')">
          <NInput v-model:value="simForm.configStr" type="textarea" :rows="6" :placeholder="$t('template.configPlaceholder')" />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="showSimModal = false">{{ $t('common.cancel') }}</NButton>
        <NButton type="primary" :loading="savingSim" @click="saveSimTemplate">{{ $t('common.save') }}</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import {
  NTabs, NTabPane, NDataTable, NButton, NModal, NForm, NFormItem,
  NInput, NSelect, NPopconfirm, NSpace,
} from 'naive-ui'

const { $api } = useApi()
const message = useMessage()
const { $t } = useI18n()

const activeTab = ref('agents')
const agentTemplates = ref<any[]>([])
const simTemplates = ref<any[]>([])
const loadingAgents = ref(false)
const loadingSims = ref(false)
const showAgentModal = ref(false)
const showSimModal = ref(false)
const savingAgent = ref(false)
const savingSim = ref(false)

const agentForm = reactive({ name: '', platform: '', profileConfigStr: '{}' })
const simForm = reactive({ name: '', type: '', platform: '', configStr: '{}' })

const platformOptions = [
  { label: 'Twitter', value: 'twitter' }, { label: 'Reddit', value: 'reddit' },
  { label: '微博', value: 'weibo' }, { label: '小红书', value: 'xiaohongshu' },
  { label: '抖音', value: 'douyin' }, { label: '快手', value: 'kuaishou' },
  { label: 'B站', value: 'bilibili' }, { label: '视频号', value: 'wechat_video' },
]

const typeOptions = computed(() => [
  { label: $t('simulation.types.marketing_sim'), value: 'marketing_sim' },
  { label: $t('simulation.types.sentiment_predict'), value: 'sentiment_predict' },
  { label: $t('simulation.types.recsys_test'), value: 'recsys_test' },
  { label: $t('simulation.types.research'), value: 'research' },
  { label: $t('simulation.types.digital_twin'), value: 'digital_twin' },
  { label: $t('simulation.types.synthetic_data'), value: 'synthetic_data' },
])

const agentColumns = computed(() => [
  { title: $t('common.name'), key: 'name' },
  { title: $t('common.platform'), key: 'platform', width: 100 },
  { title: $t('template.visibility'), key: 'isPublic', width: 80,
    render: (row: any) => row.isPublic ? $t('template.public') : $t('template.private'),
  },
  { title: $t('common.createdAt'), key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
  { title: $t('common.actions'), key: 'actions', width: 100,
    render: (row: any) => row.isPublic ? '-' : h(NButton, {
      size: 'tiny', quaternary: true, type: 'error',
      onClick: () => deleteAgentTemplate(row.id),
    }, () => $t('common.delete')),
  },
])

const simColumns = computed(() => [
  { title: $t('common.name'), key: 'name' },
  { title: $t('common.type'), key: 'type', width: 100 },
  { title: $t('common.platform'), key: 'platform', width: 100 },
  { title: $t('common.createdAt'), key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
  { title: $t('common.actions'), key: 'actions', width: 100,
    render: (row: any) => row.isPublic ? '-' : h(NButton, {
      size: 'tiny', quaternary: true, type: 'error',
      onClick: () => deleteSimTemplate(row.id),
    }, () => $t('common.delete')),
  },
])

async function loadAgentTemplates() {
  loadingAgents.value = true
  const res = await $api<any>('/api/templates/agents')
  if (res.code === 0) agentTemplates.value = res.data
  loadingAgents.value = false
}

async function loadSimTemplates() {
  loadingSims.value = true
  const res = await $api<any>('/api/templates/simulations')
  if (res.code === 0) simTemplates.value = res.data
  loadingSims.value = false
}

async function saveAgentTemplate() {
  try {
    const profileConfig = JSON.parse(agentForm.profileConfigStr)
    savingAgent.value = true
    const res = await $api<any>('/api/templates/agents', {
      method: 'POST',
      body: { name: agentForm.name, platform: agentForm.platform, profileConfig },
    })
    if (res.code === 0) {
      message.success($t('template.createSuccess'))
      showAgentModal.value = false
      agentForm.name = ''; agentForm.platform = ''; agentForm.profileConfigStr = '{}'
      await loadAgentTemplates()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error($t('template.configError'))
  } finally {
    savingAgent.value = false
  }
}

async function saveSimTemplate() {
  try {
    const config = JSON.parse(simForm.configStr)
    savingSim.value = true
    const res = await $api<any>('/api/templates/simulations', {
      method: 'POST',
      body: { name: simForm.name, type: simForm.type, platform: simForm.platform, config },
    })
    if (res.code === 0) {
      message.success($t('template.createSuccess'))
      showSimModal.value = false
      simForm.name = ''; simForm.type = ''; simForm.platform = ''; simForm.configStr = '{}'
      await loadSimTemplates()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error($t('template.configError'))
  } finally {
    savingSim.value = false
  }
}

async function deleteAgentTemplate(id: string) {
  const res = await $api<any>(`/api/templates/agents/${id}`, { method: 'DELETE' })
  if (res.code === 0) {
    message.success($t('common.deleteSuccess'))
    await loadAgentTemplates()
  } else {
    message.error(res.message)
  }
}

async function deleteSimTemplate(id: string) {
  const res = await $api<any>(`/api/templates/simulations/${id}`, { method: 'DELETE' })
  if (res.code === 0) {
    message.success($t('common.deleteSuccess'))
    await loadSimTemplates()
  } else {
    message.error(res.message)
  }
}

onMounted(() => {
  loadAgentTemplates()
  loadSimTemplates()
})
</script>

<style scoped>
.templates-page {
  max-width: 1200px;
}

.tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}
</style>
