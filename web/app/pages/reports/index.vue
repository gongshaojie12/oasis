<template>
  <div class="reports-page">
    <CommonPageHeader :title="$t('report.title')" />

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
      <NEmpty :description="$t('report.noData')" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { NDataTable, NPagination, NButton, NEmpty } from 'naive-ui'
import { useReportsStore } from '~/stores/reports'

const store = useReportsStore()
const router = useRouter()
const { $t } = useI18n()

const columns = computed(() => [
  { title: $t('report.reportTitle'), key: 'title', ellipsis: { tooltip: true },
    render: (row: any) => h('a', {
      style: 'color: #4f6ef7; cursor: pointer; text-decoration: none; font-weight: 500;',
      onClick: () => router.push(`/reports/${row.id}`),
    }, row.title),
  },
  { title: $t('report.summary'), key: 'summary', ellipsis: { tooltip: true } },
  { title: $t('common.createdAt'), key: 'createdAt', width: 180,
    render: (row: any) => new Date(row.createdAt).toLocaleString('zh-CN'),
  },
  { title: $t('common.actions'), key: 'actions', width: 120,
    render: (row: any) => h(NButton, {
      size: 'tiny', quaternary: true,
      onClick: () => router.push(`/reports/${row.id}`),
    }, () => $t('common.viewDetails')),
  },
])

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
