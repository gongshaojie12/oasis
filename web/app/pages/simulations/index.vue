<template>
  <div class="simulations-page">
    <CommonPageHeader :title="$t('simulation.title')">
      <template #actions>
        <NButton type="primary" @click="navigateTo('/simulations/create')">
          <template #icon><Icon name="carbon:add" /></template>
          {{ $t('simulation.create') }}
        </NButton>
      </template>
    </CommonPageHeader>

    <!-- Filters -->
    <div class="filters">
      <NSelect
        v-model:value="filters.status"
        :placeholder="$t('simulation.filters.status')"
        clearable
        :options="statusOptions"
        style="width: 140px"
        @update:value="loadData"
      />
      <NSelect
        v-model:value="filters.platform"
        :placeholder="$t('simulation.filters.platform')"
        clearable
        :options="platformOptions"
        style="width: 140px"
        @update:value="loadData"
      />
      <NSelect
        v-model:value="filters.type"
        :placeholder="$t('simulation.filters.type')"
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
      <NEmpty :description="$t('simulation.noData')">
        <template #extra>
          <NButton type="primary" size="small" @click="navigateTo('/simulations/create')">
            {{ $t('simulation.createFirst') }}
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

const { $t } = useI18n()

const statusOptions = computed(() => [
  { label: $t('simulation.status.pending'), value: 'pending' },
  { label: $t('simulation.status.running'), value: 'running' },
  { label: $t('simulation.status.completed'), value: 'completed' },
  { label: $t('simulation.status.failed'), value: 'failed' },
  { label: $t('simulation.status.cancelled'), value: 'cancelled' },
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

const typeOptions = computed(() => [
  { label: $t('simulation.types.marketing_sim'), value: 'marketing_sim' },
  { label: $t('simulation.types.sentiment_predict'), value: 'sentiment_predict' },
  { label: $t('simulation.types.recsys_test'), value: 'recsys_test' },
  { label: $t('simulation.types.research'), value: 'research' },
  { label: $t('simulation.types.digital_twin'), value: 'digital_twin' },
  { label: $t('simulation.types.synthetic_data'), value: 'synthetic_data' },
])

const typeNameMap = computed<Record<string, string>>(() => ({
  marketing_sim: $t('simulation.types.marketing_sim'),
  sentiment_predict: $t('simulation.types.sentiment_predict'),
  recsys_test: $t('simulation.types.recsys_test'),
  research: $t('simulation.types.research'),
  digital_twin: $t('simulation.types.digital_twin'),
  synthetic_data: $t('simulation.types.synthetic_data'),
}))

const platformNameMap = computed<Record<string, string>>(() => ({
  twitter: 'Twitter', reddit: 'Reddit', weibo: $t('common.platforms.weibo'),
  xiaohongshu: $t('common.platforms.xiaohongshu'), douyin: $t('common.platforms.douyin'), kuaishou: $t('common.platforms.kuaishou'),
  bilibili: $t('common.platforms.bilibili'), wechat_video: $t('common.platforms.wechat_video'),
}))

const columns = computed<DataTableColumns>(() => [
  { title: $t('common.name'), key: 'name', ellipsis: { tooltip: true }, width: 200,
    render: (row: any) => h('a', {
      style: 'color: #4f6ef7; cursor: pointer; text-decoration: none; font-weight: 500;',
      onClick: () => router.push(`/simulations/${row.id}`),
    }, row.name),
  },
  { title: $t('common.type'), key: 'type', width: 100,
    render: (row: any) => typeNameMap.value[row.type] || row.type,
  },
  { title: $t('common.platform'), key: 'platform', width: 80,
    render: (row: any) => platformNameMap.value[row.platform] || row.platform,
  },
  { title: $t('common.status'), key: 'status', width: 90,
    render: (row: any) => h(resolveComponent('CommonStatusTag'), { status: row.status }),
  },
  { title: $t('simulation.progress'), key: 'progress', width: 80,
    render: (row: any) => `${row.progress}%`,
  },
  { title: $t('simulation.agentCount'), key: 'agentCount', width: 80 },
  { title: $t('common.createdAt'), key: 'createdAt', width: 160,
    render: (row: any) => row.createdAt ? new Date(row.createdAt).toLocaleString('zh-CN') : '-',
  },
  { title: $t('common.actions'), key: 'actions', width: 140,
    render: (row: any) => h(NSpace, { size: 'small' }, () => {
      const buttons = []
      if (row.status === 'pending' || row.status === 'running') {
        buttons.push(h(NButton, {
          size: 'tiny', quaternary: true, type: 'warning',
          onClick: () => handleCancel(row.id),
        }, () => $t('common.cancel')))
      }
      if (row.status === 'failed' || row.status === 'cancelled') {
        buttons.push(h(NButton, {
          size: 'tiny', quaternary: true, type: 'info',
          onClick: () => handleRetry(row.id),
        }, () => $t('common.retry')))
      }
      buttons.push(h(NButton, {
        size: 'tiny', quaternary: true,
        onClick: () => router.push(`/simulations/${row.id}`),
      }, () => $t('common.details')))
      return buttons
    }),
  },
])

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
    message.success($t('common.cancelSuccess'))
    await loadData()
  } else {
    message.error(res.message)
  }
}

async function handleRetry(id: string) {
  const res = await store.retry(id)
  if (res.code === 0) {
    message.success($t('common.retrySuccess'))
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
