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
