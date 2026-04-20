<template>
  <div>
    <PageHeader title="人格基因组" subtitle="管理和生成 Agent 人格基因组">
      <template #actions>
        <n-space>
          <n-button type="primary" @click="$router.push('/genomes/create')">新建基因组</n-button>
          <n-button @click="$router.push('/genomes/breed')">群体繁殖</n-button>
        </n-space>
      </template>
    </PageHeader>

    <n-card>
      <n-space justify="space-between" align="center" style="margin-bottom: 16px">
        <n-select
          v-model:value="filterSource"
          :options="sourceOptions"
          placeholder="按来源筛选"
          clearable
          style="width: 200px"
          @update:value="loadList"
        />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="store.items"
        :loading="store.loading"
        :row-key="(row: any) => row.id"
      />

      <n-space justify="center" style="margin-top: 16px">
        <n-pagination
          v-model:page="currentPage"
          :page-count="store.pagination.totalPages"
          @update:page="loadList"
        />
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NSpace, NTag } from 'naive-ui'
import { useRouter } from 'vue-router'
import { useGenomesStore } from '~/stores/genomes'

const router = useRouter()
const store = useGenomesStore()
const currentPage = ref(1)
const filterSource = ref<string | null>(null)

const sourceOptions = [
  { label: '手动创建', value: 'manual' },
  { label: '文档提取', value: 'document' },
  { label: 'URL提取', value: 'url' },
  { label: 'CSV导入', value: 'csv' },
  { label: '自然语言', value: 'natural_language' },
  { label: '繁殖生成', value: 'breed' },
]

const sourceLabels: Record<string, string> = Object.fromEntries(sourceOptions.map(o => [o.value, o.label]))

const columns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  {
    title: '来源',
    key: 'sourceType',
    width: 120,
    render: (row: any) => h(NTag, { size: 'small', type: 'info' }, () => sourceLabels[row.sourceType] || row.sourceType),
  },
  {
    title: '标签',
    key: 'tags',
    width: 200,
    render: (row: any) => {
      const tags = row.tags || []
      return h(NSpace, { size: 'small' }, () => tags.slice(0, 3).map((t: string) => h(NTag, { size: 'tiny' }, () => t)))
    },
  },
  { title: '创建时间', key: 'createdAt', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { text: true, type: 'primary', onClick: () => router.push(`/genomes/${row.id}`) }, () => '查看'),
      h(NButton, { text: true, type: 'error', onClick: () => handleDelete(row.id) }, () => '删除'),
    ]),
  },
]

async function loadList() {
  await store.fetchList({
    page: currentPage.value,
    sourceType: filterSource.value || undefined,
  })
}

async function handleDelete(id: string) {
  await store.remove(id)
  await loadList()
}

onMounted(() => loadList())
</script>
