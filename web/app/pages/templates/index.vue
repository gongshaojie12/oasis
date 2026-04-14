<template>
  <div class="templates-page">
    <CommonPageHeader title="模板管理" />

    <NTabs type="line" v-model:value="activeTab">
      <!-- Agent Templates Tab -->
      <NTabPane name="agents" tab="Agent 画像模板">
        <div class="tab-header">
          <NButton type="primary" size="small" @click="showAgentModal = true">
            <template #icon><Icon name="carbon:add" /></template>
            新建 Agent 模板
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
      <NTabPane name="simulations" tab="模拟配置模板">
        <div class="tab-header">
          <NButton type="primary" size="small" @click="showSimModal = true">
            <template #icon><Icon name="carbon:add" /></template>
            新建模拟模板
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
    <NModal v-model:show="showAgentModal" preset="dialog" title="新建 Agent 模板" style="width: 500px">
      <NForm label-placement="left" label-width="80">
        <NFormItem label="模板名称">
          <NInput v-model:value="agentForm.name" placeholder="模板名称" />
        </NFormItem>
        <NFormItem label="平台">
          <NSelect v-model:value="agentForm.platform" :options="platformOptions" placeholder="选择平台" />
        </NFormItem>
        <NFormItem label="画像配置">
          <NInput v-model:value="agentForm.profileConfigStr" type="textarea" :rows="6" placeholder='JSON 格式，例如 {"age": 25, "interest": "科技"}' />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="showAgentModal = false">取消</NButton>
        <NButton type="primary" :loading="savingAgent" @click="saveAgentTemplate">保存</NButton>
      </template>
    </NModal>

    <!-- Simulation Template Modal -->
    <NModal v-model:show="showSimModal" preset="dialog" title="新建模拟模板" style="width: 500px">
      <NForm label-placement="left" label-width="80">
        <NFormItem label="模板名称">
          <NInput v-model:value="simForm.name" placeholder="模板名称" />
        </NFormItem>
        <NFormItem label="业务类型">
          <NSelect v-model:value="simForm.type" :options="typeOptions" placeholder="选择类型" />
        </NFormItem>
        <NFormItem label="平台">
          <NSelect v-model:value="simForm.platform" :options="platformOptions" placeholder="选择平台" />
        </NFormItem>
        <NFormItem label="配置">
          <NInput v-model:value="simForm.configStr" type="textarea" :rows="6" placeholder='JSON 格式' />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="showSimModal = false">取消</NButton>
        <NButton type="primary" :loading="savingSim" @click="saveSimTemplate">保存</NButton>
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

const typeOptions = [
  { label: '社交营销', value: 'marketing_sim' },
  { label: '舆情预测', value: 'sentiment_predict' },
  { label: '推荐算法', value: 'recsys_test' },
  { label: '社会研究', value: 'research' },
  { label: '数字孪生', value: 'digital_twin' },
  { label: '合成数据', value: 'synthetic_data' },
]

const agentColumns = [
  { title: '名称', key: 'name' },
  { title: '平台', key: 'platform', width: 100 },
  { title: '类型', key: 'isPublic', width: 80,
    render: (row: any) => row.isPublic ? '公共' : '私有',
  },
  { title: '创建时间', key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
  { title: '操作', key: 'actions', width: 100,
    render: (row: any) => row.isPublic ? '-' : h(NButton, {
      size: 'tiny', quaternary: true, type: 'error',
      onClick: () => deleteAgentTemplate(row.id),
    }, () => '删除'),
  },
]

const simColumns = [
  { title: '名称', key: 'name' },
  { title: '类型', key: 'type', width: 100 },
  { title: '平台', key: 'platform', width: 100 },
  { title: '创建时间', key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
  { title: '操作', key: 'actions', width: 100,
    render: (row: any) => row.isPublic ? '-' : h(NButton, {
      size: 'tiny', quaternary: true, type: 'error',
      onClick: () => deleteSimTemplate(row.id),
    }, () => '删除'),
  },
]

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
      message.success('模板已创建')
      showAgentModal.value = false
      agentForm.name = ''; agentForm.platform = ''; agentForm.profileConfigStr = '{}'
      await loadAgentTemplates()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('配置格式错误，请输入有效的 JSON')
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
      message.success('模板已创建')
      showSimModal.value = false
      simForm.name = ''; simForm.type = ''; simForm.platform = ''; simForm.configStr = '{}'
      await loadSimTemplates()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('配置格式错误，请输入有效的 JSON')
  } finally {
    savingSim.value = false
  }
}

async function deleteAgentTemplate(id: string) {
  const res = await $api<any>(`/api/templates/agents/${id}`, { method: 'DELETE' })
  if (res.code === 0) {
    message.success('已删除')
    await loadAgentTemplates()
  } else {
    message.error(res.message)
  }
}

async function deleteSimTemplate(id: string) {
  const res = await $api<any>(`/api/templates/simulations/${id}`, { method: 'DELETE' })
  if (res.code === 0) {
    message.success('已删除')
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
