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
