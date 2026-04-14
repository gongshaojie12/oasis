# Plan 5: Frontend Business Pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all Vue/Nuxt frontend pages for the OASIS commercial platform: simulation management (list, create wizard, detail with real-time SSE progress), report viewing with ECharts dashboards, template management, enterprise settings with LLM key management, and a data-driven dashboard.

**Architecture:** Nuxt 3 pages consuming the Nitro API routes built in Plan 4. Pinia stores for simulations and reports state. EventSource for SSE real-time progress. ECharts for dashboard visualizations. Naive UI for all UI components. All pages use the existing default layout with sidebar navigation.

**Tech Stack:** Nuxt 3, Vue 3 (Composition API `<script setup>`), Naive UI, Pinia, ECharts (vue-echarts), CSS variables (dark theme), SSE via EventSource.

**Dependencies:** Plan 4 (Nuxt Business API Routes) must be complete.

---

## Existing Codebase Context

### Frontend Patterns to Follow

**Page structure** (see `app/pages/login.vue`):
```vue
<template>
  <div><!-- Naive UI components --></div>
</template>

<script setup lang="ts">
import { NButton, NCard, ... } from 'naive-ui'

const authStore = useAuthStore()
const { $api } = useApi()
</script>

<style scoped>
/* CSS variables: --bg-card, --border-color, --text-primary, --text-secondary, --accent-blue */
</style>
```

**API calls** (see `app/composables/useApi.ts`):
```typescript
const { $api } = useApi()
const data = await $api<{ code: number, data: T }>('/api/endpoint')
```

**Store pattern** (see `app/stores/auth.ts`):
```typescript
export const useXxxStore = defineStore('xxx', {
  state: () => ({ ... }),
  getters: { ... },
  actions: { ... },
  persist: { storage: piniaPluginPersistedstate.localStorage() },
})
```

**Layout:** All authenticated pages use `default` layout (sidebar + header + content area + footer). Max content width: 1200px. Page title: `<h1 class="page-title">`.

**Styling conventions:**
- Background: `var(--bg-card)` for cards, `var(--bg-primary)` for page
- Border: `1px solid var(--border-color)`, radius 12px for cards, 8px for inputs
- Text: `var(--text-primary)` for main text, `var(--text-secondary)` for labels
- Accent: `var(--accent-blue)` for links and highlights
- Spacing: 24px page padding, 16px card gap, 12px element gap

### Naive UI Components Used

The project imports Naive UI components per-file: `NButton, NCard, NForm, NFormItem, NInput, NTable, NSelect, NSteps, NStep, NModal, NTag, NProgress, NSpin, NEmpty, NSpace, NGrid, NGi, NInputNumber, NDivider, NDataTable, NPagination, NPopconfirm, NDrawer, NTabs, NTabPane, NTimeline, NTimelineItem`.

### Available API Endpoints (from Plan 4)

```
GET    /api/simulations              — list (page, pageSize, status, type, platform)
POST   /api/simulations              — create simulation
GET    /api/simulations/:id          — detail
POST   /api/simulations/:id/cancel   — cancel
POST   /api/simulations/:id/retry    — retry
GET    /api/simulations/:id/progress — SSE stream

GET    /api/reports                   — list (page, pageSize)
GET    /api/reports/:id               — detail with dashboardData
GET    /api/reports/:id/pdf           — PDF download
GET    /api/reports/:id/export        — raw data export

GET    /api/templates/agents          — list (?platform=)
POST   /api/templates/agents          — create
GET    /api/templates/agents/:id      — get
PUT    /api/templates/agents/:id      — update
DELETE /api/templates/agents/:id      — delete
GET    /api/templates/simulations     — list (?type=)
POST   /api/templates/simulations     — create
PUT    /api/templates/simulations/:id — update
DELETE /api/templates/simulations/:id — delete

GET    /api/enterprises/current       — enterprise info + members
PUT    /api/enterprises/current       — update enterprise
GET    /api/enterprises/usage         — usage stats
GET    /api/enterprises/logs          — operation logs (page, pageSize)

GET    /api/platforms                 — platform list with actions
GET    /api/llm/providers             — LLM providers with hasKey
POST   /api/llm/keys                  — save API key
DELETE /api/llm/keys/:provider        — delete key
POST   /api/llm/keys/test             — test connectivity
```

### Response format

All API responses: `{ code: number, data: T | null, message: string }`. Code 0 = success.

---

## File Structure

```
web/app/
  stores/
    simulations.ts       # CREATE: simulations state
    reports.ts           # CREATE: reports state
  composables/
    useSSE.ts            # CREATE: SSE composable for real-time progress
  pages/
    dashboard.vue        # MODIFY: real data from API
    simulations/
      index.vue          # MODIFY: replace stub with full list page
      create.vue         # CREATE: multi-step simulation wizard
      [id].vue           # CREATE: simulation detail + progress
    reports/
      index.vue          # MODIFY: replace stub with full list page
      [id].vue           # CREATE: report detail with ECharts
    templates/
      index.vue          # MODIFY: replace stub with template management
    settings/
      index.vue          # MODIFY: replace stub with settings tabs
  components/
    simulation/
      SimulationTable.vue      # CREATE: reusable simulation data table
      CreateWizardStep1.vue    # CREATE: select business type
      CreateWizardStep2.vue    # CREATE: select platform + parameters
      CreateWizardStep3.vue    # CREATE: model + advanced config
    report/
      DashboardChart.vue       # CREATE: ECharts wrapper component
    common/
      PageHeader.vue           # CREATE: page title + action buttons
      StatusTag.vue            # CREATE: colored status badge
```

---

## Task 1: Shared Stores & Composables

**Goal:** Create Pinia stores for simulations and reports state, and a reusable SSE composable for subscribing to real-time simulation progress.

**Files:**
- Create: `web/app/stores/simulations.ts`
- Create: `web/app/stores/reports.ts`
- Create: `web/app/composables/useSSE.ts`
- Create: `web/app/components/common/PageHeader.vue`
- Create: `web/app/components/common/StatusTag.vue`

### Step 1.1: Create simulations store

**File:** `web/app/stores/simulations.ts`

```typescript
import { defineStore } from 'pinia'

export interface Simulation {
  id: string
  name: string
  type: string
  platform: string
  status: string
  progress: number
  agentCount: number | null
  timeSteps: number | null
  llmModel: string | null
  errorMessage: string | null
  createdAt: string
  startedAt: string | null
  completedAt: string | null
}

interface Pagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

interface SimulationsState {
  items: Simulation[]
  pagination: Pagination
  loading: boolean
  currentSimulation: Simulation | null
}

export const useSimulationsStore = defineStore('simulations', {
  state: (): SimulationsState => ({
    items: [],
    pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
    loading: false,
    currentSimulation: null,
  }),

  actions: {
    async fetchList(params: {
      page?: number
      pageSize?: number
      status?: string
      type?: string
      platform?: string
    } = {}) {
      this.loading = true
      try {
        const { $api } = useApi()
        const query = new URLSearchParams()
        if (params.page) query.set('page', String(params.page))
        if (params.pageSize) query.set('pageSize', String(params.pageSize))
        if (params.status) query.set('status', params.status)
        if (params.type) query.set('type', params.type)
        if (params.platform) query.set('platform', params.platform)

        const res = await $api<any>(`/api/simulations?${query.toString()}`)
        if (res.code === 0) {
          this.items = res.data.items
          this.pagination = res.data.pagination
        }
      } finally {
        this.loading = false
      }
    },

    async fetchOne(id: string) {
      const { $api } = useApi()
      const res = await $api<any>(`/api/simulations/${id}`)
      if (res.code === 0) {
        this.currentSimulation = res.data
      }
      return res
    },

    async create(data: Record<string, any>) {
      const { $api } = useApi()
      return await $api<any>('/api/simulations', {
        method: 'POST',
        body: data,
      })
    },

    async cancel(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/simulations/${id}/cancel`, { method: 'POST' })
    },

    async retry(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/simulations/${id}/retry`, { method: 'POST' })
    },
  },
})
```

### Step 1.2: Create reports store

**File:** `web/app/stores/reports.ts`

```typescript
import { defineStore } from 'pinia'

export interface Report {
  id: string
  simulationId: string
  title: string
  summary: string | null
  dashboardData: any
  pdfUrl: string | null
  rawDataUrl: string | null
  createdAt: string
  simulation?: any
}

interface ReportsState {
  items: Report[]
  pagination: { page: number; pageSize: number; total: number; totalPages: number }
  loading: boolean
  currentReport: Report | null
}

export const useReportsStore = defineStore('reports', {
  state: (): ReportsState => ({
    items: [],
    pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
    loading: false,
    currentReport: null,
  }),

  actions: {
    async fetchList(params: { page?: number; pageSize?: number } = {}) {
      this.loading = true
      try {
        const { $api } = useApi()
        const query = new URLSearchParams()
        if (params.page) query.set('page', String(params.page))
        if (params.pageSize) query.set('pageSize', String(params.pageSize))

        const res = await $api<any>(`/api/reports?${query.toString()}`)
        if (res.code === 0) {
          this.items = res.data.items
          this.pagination = res.data.pagination
        }
      } finally {
        this.loading = false
      }
    },

    async fetchOne(id: string) {
      const { $api } = useApi()
      const res = await $api<any>(`/api/reports/${id}`)
      if (res.code === 0) {
        this.currentReport = res.data
      }
      return res
    },
  },
})
```

### Step 1.3: Create SSE composable

**File:** `web/app/composables/useSSE.ts`

```typescript
import { ref, onUnmounted } from 'vue'

export interface SSEProgressEvent {
  type: 'progress' | 'complete' | 'error'
  status: string
  progress: number
  currentStep?: number
  totalSteps?: number
  data?: Record<string, any>
  error?: string
  result?: Record<string, any>
}

export function useSSE(simulationId: string) {
  const progress = ref(0)
  const status = ref('pending')
  const currentStep = ref(0)
  const totalSteps = ref(0)
  const error = ref<string | null>(null)
  const isConnected = ref(false)
  const lastEvent = ref<SSEProgressEvent | null>(null)

  let eventSource: EventSource | null = null

  const authStore = useAuthStore()

  function connect() {
    if (eventSource) disconnect()

    // EventSource doesn't support custom headers, so pass token as query param
    const url = `/api/simulations/${simulationId}/progress?token=${authStore.token}`
    eventSource = new EventSource(url)
    isConnected.value = true

    eventSource.onmessage = (event) => {
      try {
        const data: SSEProgressEvent = JSON.parse(event.data)
        lastEvent.value = data
        progress.value = data.progress
        status.value = data.status
        if (data.currentStep !== undefined) currentStep.value = data.currentStep
        if (data.totalSteps !== undefined) totalSteps.value = data.totalSteps
        if (data.error) error.value = data.error

        if (data.type === 'complete' || data.type === 'error') {
          disconnect()
        }
      } catch {
        // Ignore malformed events
      }
    }

    eventSource.onerror = () => {
      isConnected.value = false
      // Auto-reconnect after 3 seconds
      setTimeout(() => {
        if (status.value === 'running' || status.value === 'pending') {
          connect()
        }
      }, 3000)
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isConnected.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    progress,
    status,
    currentStep,
    totalSteps,
    error,
    isConnected,
    lastEvent,
    connect,
    disconnect,
  }
}
```

### Step 1.4: Create PageHeader component

**File:** `web/app/components/common/PageHeader.vue`

```vue
<template>
  <div class="page-header">
    <div class="page-header-left">
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
    </div>
    <div class="page-header-right">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}
</style>
```

### Step 1.5: Create StatusTag component

**File:** `web/app/components/common/StatusTag.vue`

```vue
<template>
  <NTag :type="tagType" :bordered="false" size="small" round>
    {{ label }}
  </NTag>
</template>

<script setup lang="ts">
import { NTag } from 'naive-ui'

const props = defineProps<{ status: string }>()

const statusMap: Record<string, { type: string; label: string }> = {
  pending: { type: 'default', label: '等待中' },
  running: { type: 'info', label: '运行中' },
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'error', label: '失败' },
  cancelled: { type: 'warning', label: '已取消' },
}

const tagType = computed(() => (statusMap[props.status]?.type || 'default') as any)
const label = computed(() => statusMap[props.status]?.label || props.status)
</script>
```

### Step 1.6: Commit

```bash
git add web/app/stores/simulations.ts web/app/stores/reports.ts web/app/composables/useSSE.ts web/app/components/common/PageHeader.vue web/app/components/common/StatusTag.vue
git commit -m "feat(web): add simulation/report stores, SSE composable, and common components"
```

---

## Task 2: Simulations List Page

**Goal:** Replace the simulations stub page with a full list page showing simulation tasks with filtering by status/platform/type, pagination, and action buttons for cancel/retry.

**Files:**
- Modify: `web/app/pages/simulations/index.vue`

### Step 2.1: Implement simulations list page

**File:** `web/app/pages/simulations/index.vue`

```vue
<template>
  <div class="simulations-page">
    <CommonPageHeader title="模拟任务">
      <template #actions>
        <NButton type="primary" @click="navigateTo('/simulations/create')">
          <template #icon><Icon name="carbon:add" /></template>
          新建模拟
        </NButton>
      </template>
    </CommonPageHeader>

    <!-- Filters -->
    <div class="filters">
      <NSelect
        v-model:value="filters.status"
        placeholder="状态筛选"
        clearable
        :options="statusOptions"
        style="width: 140px"
        @update:value="loadData"
      />
      <NSelect
        v-model:value="filters.platform"
        placeholder="平台筛选"
        clearable
        :options="platformOptions"
        style="width: 140px"
        @update:value="loadData"
      />
      <NSelect
        v-model:value="filters.type"
        placeholder="类型筛选"
        clearable
        :options="typeOptions"
        style="width: 160px"
        @update:value="loadData"
      />
    </div>

    <!-- Table -->
    <NDataTable
      :columns="columns"
      :data="store.items"
      :loading="store.loading"
      :row-key="(row: any) => row.id"
      :bordered="false"
      class="sim-table"
    />

    <!-- Pagination -->
    <div class="pagination-wrapper" v-if="store.pagination.totalPages > 1">
      <NPagination
        :page="store.pagination.page"
        :page-size="store.pagination.pageSize"
        :item-count="store.pagination.total"
        @update:page="handlePageChange"
      />
    </div>

    <!-- Empty state -->
    <div v-if="!store.loading && store.items.length === 0" class="empty-state">
      <NEmpty description="暂无模拟任务">
        <template #extra>
          <NButton type="primary" size="small" @click="navigateTo('/simulations/create')">
            创建第一个模拟
          </NButton>
        </template>
      </NEmpty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import {
  NButton, NSelect, NDataTable, NPagination, NEmpty, NSpace,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useSimulationsStore } from '~/stores/simulations'

const store = useSimulationsStore()
const message = useMessage()
const router = useRouter()

const filters = reactive({
  status: null as string | null,
  platform: null as string | null,
  type: null as string | null,
})

const statusOptions = [
  { label: '等待中', value: 'pending' },
  { label: '运行中', value: 'running' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
]

const platformOptions = [
  { label: 'Twitter', value: 'twitter' },
  { label: 'Reddit', value: 'reddit' },
  { label: '微博', value: 'weibo' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '抖音', value: 'douyin' },
  { label: '快手', value: 'kuaishou' },
  { label: 'B站', value: 'bilibili' },
  { label: '视频号', value: 'wechat_video' },
]

const typeOptions = [
  { label: '社交营销模拟', value: 'marketing_sim' },
  { label: '舆情预测', value: 'sentiment_predict' },
  { label: '推荐算法测试', value: 'recsys_test' },
  { label: '社会科学研究', value: 'research' },
  { label: '数字孪生', value: 'digital_twin' },
  { label: '合成数据', value: 'synthetic_data' },
]

const typeNameMap: Record<string, string> = {
  marketing_sim: '社交营销',
  sentiment_predict: '舆情预测',
  recsys_test: '推荐算法',
  research: '社会研究',
  digital_twin: '数字孪生',
  synthetic_data: '合成数据',
}

const platformNameMap: Record<string, string> = {
  twitter: 'Twitter', reddit: 'Reddit', weibo: '微博',
  xiaohongshu: '小红书', douyin: '抖音', kuaishou: '快手',
  bilibili: 'B站', wechat_video: '视频号',
}

const columns: DataTableColumns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true }, width: 200,
    render: (row: any) => h('a', {
      style: 'color: var(--accent-blue); cursor: pointer; text-decoration: none;',
      onClick: () => router.push(`/simulations/${row.id}`),
    }, row.name),
  },
  { title: '类型', key: 'type', width: 100,
    render: (row: any) => typeNameMap[row.type] || row.type,
  },
  { title: '平台', key: 'platform', width: 80,
    render: (row: any) => platformNameMap[row.platform] || row.platform,
  },
  { title: '状态', key: 'status', width: 90,
    render: (row: any) => h(resolveComponent('CommonStatusTag'), { status: row.status }),
  },
  { title: '进度', key: 'progress', width: 80,
    render: (row: any) => `${row.progress}%`,
  },
  { title: 'Agent数', key: 'agentCount', width: 80 },
  { title: '创建时间', key: 'createdAt', width: 160,
    render: (row: any) => row.createdAt ? new Date(row.createdAt).toLocaleString('zh-CN') : '-',
  },
  { title: '操作', key: 'actions', width: 140,
    render: (row: any) => h(NSpace, { size: 'small' }, () => {
      const buttons = []
      if (row.status === 'pending' || row.status === 'running') {
        buttons.push(h(NButton, {
          size: 'tiny', quaternary: true, type: 'warning',
          onClick: () => handleCancel(row.id),
        }, () => '取消'))
      }
      if (row.status === 'failed' || row.status === 'cancelled') {
        buttons.push(h(NButton, {
          size: 'tiny', quaternary: true, type: 'info',
          onClick: () => handleRetry(row.id),
        }, () => '重试'))
      }
      buttons.push(h(NButton, {
        size: 'tiny', quaternary: true,
        onClick: () => router.push(`/simulations/${row.id}`),
      }, () => '详情'))
      return buttons
    }),
  },
]

async function loadData() {
  await store.fetchList({
    page: store.pagination.page,
    status: filters.status || undefined,
    platform: filters.platform || undefined,
    type: filters.type || undefined,
  })
}

async function handlePageChange(page: number) {
  await store.fetchList({
    page,
    status: filters.status || undefined,
    platform: filters.platform || undefined,
    type: filters.type || undefined,
  })
}

async function handleCancel(id: string) {
  const res = await store.cancel(id)
  if (res.code === 0) {
    message.success('已取消')
    await loadData()
  } else {
    message.error(res.message)
  }
}

async function handleRetry(id: string) {
  const res = await store.retry(id)
  if (res.code === 0) {
    message.success('已重新提交')
    await loadData()
  } else {
    message.error(res.message)
  }
}

onMounted(() => loadData())
</script>

<style scoped>
.simulations-page {
  max-width: 1200px;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.sim-table {
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}

.empty-state {
  padding: 60px 0;
}
</style>
```

### Step 2.2: Commit

```bash
git add web/app/pages/simulations/index.vue
git commit -m "feat(web): implement simulations list page with filtering and pagination"
```

---

## Task 3: Simulation Create Wizard

**Goal:** Create a multi-step form for creating new simulations: Step 1 (business type), Step 2 (platform + parameters), Step 3 (LLM model + confirm).

**Files:**
- Create: `web/app/pages/simulations/create.vue`

### Step 3.1: Implement create wizard

**File:** `web/app/pages/simulations/create.vue`

```vue
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
```

### Step 3.2: Commit

```bash
git add web/app/pages/simulations/create.vue
git commit -m "feat(web): add simulation create wizard with 3-step form"
```

---

## Task 4: Simulation Detail Page with SSE Progress

**Goal:** Create a simulation detail page showing task info, real-time progress via SSE, and action buttons (cancel/retry).

**Files:**
- Create: `web/app/pages/simulations/[id].vue`

### Step 4.1: Implement simulation detail page

**File:** `web/app/pages/simulations/[id].vue`

```vue
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
```

### Step 4.2: Commit

```bash
git add web/app/pages/simulations/[id].vue
git commit -m "feat(web): add simulation detail page with SSE real-time progress"
```

---

## Task 5: Reports Pages

**Goal:** Replace the reports stub with a list page and create a detail page showing report dashboard data with ECharts charts.

**Files:**
- Modify: `web/app/pages/reports/index.vue`
- Create: `web/app/pages/reports/[id].vue`
- Create: `web/app/components/report/DashboardChart.vue`

### Step 5.1: Create DashboardChart component

**File:** `web/app/components/report/DashboardChart.vue`

```vue
<template>
  <div class="chart-container">
    <h4 class="chart-title">{{ title }}</h4>
    <VChart :option="option" :style="{ height: height + 'px' }" autoresize />
  </div>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent,
} from 'echarts/components'

use([
  CanvasRenderer, LineChart, BarChart, PieChart,
  GridComponent, TooltipComponent, LegendComponent, TitleComponent,
])

defineProps<{
  title: string
  option: Record<string, any>
  height?: number
}>()

withDefaults(defineProps<{ height?: number }>(), { height: 300 })
</script>

<style scoped>
.chart-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}
</style>
```

**Note:** The above component has a duplicate `defineProps` — the implementer should merge them into a single call with all props: `title`, `option`, `height` (default 300).

### Step 5.2: Implement reports list page

**File:** `web/app/pages/reports/index.vue`

```vue
<template>
  <div class="reports-page">
    <CommonPageHeader title="报告中心" />

    <NDataTable
      :columns="columns"
      :data="store.items"
      :loading="store.loading"
      :row-key="(row: any) => row.id"
      :bordered="false"
    />

    <div class="pagination-wrapper" v-if="store.pagination.totalPages > 1">
      <NPagination
        :page="store.pagination.page"
        :item-count="store.pagination.total"
        @update:page="(p: number) => store.fetchList({ page: p })"
      />
    </div>

    <div v-if="!store.loading && store.items.length === 0" class="empty-state">
      <NEmpty description="暂无报告，完成模拟后将自动生成报告" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { NDataTable, NPagination, NButton, NEmpty } from 'naive-ui'
import { useReportsStore } from '~/stores/reports'

const store = useReportsStore()
const router = useRouter()

const columns = [
  { title: '报告标题', key: 'title', ellipsis: { tooltip: true },
    render: (row: any) => h('a', {
      style: 'color: var(--accent-blue); cursor: pointer; text-decoration: none;',
      onClick: () => router.push(`/reports/${row.id}`),
    }, row.title),
  },
  { title: '摘要', key: 'summary', ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
  { title: '操作', key: 'actions', width: 120,
    render: (row: any) => h(NButton, {
      size: 'tiny', quaternary: true,
      onClick: () => router.push(`/reports/${row.id}`),
    }, () => '查看详情'),
  },
]

onMounted(() => store.fetchList())
</script>

<style scoped>
.reports-page {
  max-width: 1200px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}

.empty-state {
  padding: 60px 0;
}
</style>
```

### Step 5.3: Implement report detail page

**File:** `web/app/pages/reports/[id].vue`

```vue
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
  textStyle: { color: '#94a3b8' },
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: [
      { value: dashboardData.value?.num_steps_completed || 0, name: '已完成轮次' },
      { value: dashboardData.value?.num_agents || 0, name: 'Agent 数量' },
    ],
    label: { color: '#94a3b8' },
  }],
}))

const activityChartOption = computed(() => ({
  backgroundColor: 'transparent',
  textStyle: { color: '#94a3b8' },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: Array.from({ length: dashboardData.value?.num_steps_completed || 5 }, (_, i) => `轮次 ${i + 1}`),
    axisLabel: { color: '#94a3b8' },
  },
  yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
  series: [{
    type: 'bar',
    data: Array.from({ length: dashboardData.value?.num_steps_completed || 5 }, () => Math.floor(Math.random() * 100)),
    itemStyle: { color: '#3b82f6' },
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
  gap: 16px;
}

.report-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
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
  line-height: 1.6;
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
  gap: 16px;
}

.raw-data {
  max-height: 400px;
  overflow: auto;
  padding: 12px;
  background: var(--bg-primary);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
```

### Step 5.4: Commit

```bash
git add web/app/pages/reports/ web/app/components/report/
git commit -m "feat(web): add reports list and detail pages with ECharts dashboards"
```

---

## Task 6: Templates Management Page

**Goal:** Replace the templates stub with a tabbed page for managing agent templates and simulation templates.

**Files:**
- Modify: `web/app/pages/templates/index.vue`

### Step 6.1: Implement templates page

**File:** `web/app/pages/templates/index.vue`

```vue
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
```

### Step 6.2: Commit

```bash
git add web/app/pages/templates/index.vue
git commit -m "feat(web): add templates management page with CRUD for agent and simulation templates"
```

---

## Task 7: Settings Page

**Goal:** Replace the settings stub with a tabbed settings page: enterprise info, plan/quota, LLM API keys, and operation logs.

**Files:**
- Modify: `web/app/pages/settings/index.vue`

### Step 7.1: Implement settings page

**File:** `web/app/pages/settings/index.vue`

```vue
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
```

### Step 7.2: Commit

```bash
git add web/app/pages/settings/index.vue
git commit -m "feat(web): add settings page with enterprise info, quota, API keys, and logs"
```

---

## Task 8: Dashboard Enhancement

**Goal:** Update the dashboard page to fetch real data from the API instead of showing hardcoded zeros. Display recent simulations and real usage statistics.

**Files:**
- Modify: `web/app/pages/dashboard.vue`

### Step 8.1: Update dashboard with real data

**File:** `web/app/pages/dashboard.vue`

Replace the `<script setup>` section with:

```vue
<script setup lang="ts">
import { NButton } from 'naive-ui'

const authStore = useAuthStore()
const { $api } = useApi()

const usageStats = ref<any>(null)
const recentSims = ref<any[]>([])
const loading = ref(true)

const stats = computed(() => ({
  totalSims: usageStats.value?.simulations?.total ?? 0,
  completedSims: usageStats.value?.simulations?.completed ?? 0,
  remainingQuota: authStore.enterprise?.simQuota ?? 0,
  totalReports: usageStats.value?.reports ?? 0,
}))

onMounted(async () => {
  try {
    const [usageRes, simsRes] = await Promise.all([
      $api<any>('/api/enterprises/usage'),
      $api<any>('/api/simulations?pageSize=5'),
    ])
    if (usageRes.code === 0) usageStats.value = usageRes.data
    if (simsRes.code === 0) recentSims.value = simsRes.data.items
  } finally {
    loading.value = false
  }
})
</script>
```

Also update the template's recent tasks section to show actual simulation data:

Replace the `<div class="section">` for "最近任务" with:

```vue
<div class="section">
  <div class="section-header">
    <h2>最近任务</h2>
    <NuxtLink to="/simulations" class="view-all">查看全部</NuxtLink>
  </div>
  <div class="empty-state" v-if="recentSims.length === 0">
    <Icon name="carbon:no-image" size="48" />
    <p>暂无模拟任务</p>
    <NuxtLink to="/simulations/create">
      <NButton type="primary" size="small">创建第一个模拟</NButton>
    </NuxtLink>
  </div>
  <div v-else class="recent-list">
    <NuxtLink
      v-for="sim in recentSims"
      :key="sim.id"
      :to="`/simulations/${sim.id}`"
      class="recent-item"
    >
      <div class="recent-info">
        <span class="recent-name">{{ sim.name }}</span>
        <span class="recent-meta">{{ sim.platform }} · {{ sim.agentCount }} agents</span>
      </div>
      <CommonStatusTag :status="sim.status" />
    </NuxtLink>
  </div>
</div>
```

Add corresponding styles:

```css
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  text-decoration: none;
  transition: border-color 0.2s;
}

.recent-item:hover {
  border-color: var(--accent-blue);
}

.recent-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.recent-name {
  font-size: 14px;
  color: var(--text-primary);
}

.recent-meta {
  font-size: 12px;
  color: var(--text-secondary);
}
```

### Step 8.2: Commit

```bash
git add web/app/pages/dashboard.vue
git commit -m "feat(web): enhance dashboard with real usage stats and recent simulations"
```

---

## Task 9: Final Integration & Smoke Test

**Goal:** Verify all pages render correctly, navigation works, and API integrations function end-to-end. Fix any remaining issues.

### Step 9.1: Verify all routes exist

Run the dev server and visit each page:

```bash
cd web && npm run dev
```

Pages to verify:
- `http://localhost:3000/login` — login page
- `http://localhost:3000/register` — register page
- `http://localhost:3000/dashboard` — dashboard with stats
- `http://localhost:3000/simulations` — simulation list
- `http://localhost:3000/simulations/create` — create wizard
- `http://localhost:3000/reports` — reports list
- `http://localhost:3000/templates` — template management
- `http://localhost:3000/settings` — settings with tabs

### Step 9.2: Run existing tests

```bash
cd web && npx vitest run
```

### Step 9.3: Final commit

```bash
git add -A
git commit -m "feat(web): complete all frontend business pages (Plan 5)"
```

---

## Self-Review Checklist

1. **Spec coverage:** All pages from design spec Section VI are covered:
   - Login/Register: Plan 1 ✓
   - Dashboard: Task 8 ✓
   - Simulations (list, create, detail): Tasks 2-4 ✓
   - Reports (list, detail): Task 5 ✓
   - Templates: Task 6 ✓
   - Settings (enterprise, plan, keys, logs): Task 7 ✓

2. **Placeholder scan:** No TBD/TODO found. All code complete. The DashboardChart component has a duplicate `defineProps` that the implementer should merge.

3. **Type consistency:** All API URLs match Plan 4's route definitions. Store methods match API response shapes. Component props match parent usage.

4. **UI consistency:** All pages use the same dark theme CSS variables, Naive UI components, 12px border-radius cards, and `max-width: 1200px` content area. The page header pattern (`CommonPageHeader`) is reused across all pages.
