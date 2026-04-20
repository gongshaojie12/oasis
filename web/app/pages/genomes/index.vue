<template>
  <div>
    <PageHeader :title="$t('genome.title')" :subtitle="$t('genome.subtitle')">
      <template #actions>
        <n-space>
          <n-button type="primary" @click="$router.push('/genomes/create')">{{ $t('genome.create') }}</n-button>
          <n-button @click="$router.push('/genomes/breed')">{{ $t('genome.breed') }}</n-button>
        </n-space>
      </template>
    </PageHeader>

    <n-card>
      <n-space justify="space-between" align="center" style="margin-bottom: 16px">
        <n-select
          v-model:value="filterSource"
          :options="sourceOptions"
          :placeholder="$t('genome.filterBySource')"
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
const { $t } = useI18n()

const sourceOptions = computed(() => [
  { label: $t('genome.sources.manual'), value: 'manual' },
  { label: $t('genome.sources.document'), value: 'document' },
  { label: $t('genome.sources.url'), value: 'url' },
  { label: $t('genome.sources.csv'), value: 'csv' },
  { label: $t('genome.sources.natural_language'), value: 'natural_language' },
  { label: $t('genome.sources.breed'), value: 'breed' },
])

const sourceLabels = computed<Record<string, string>>(() => Object.fromEntries(sourceOptions.value.map(o => [o.value, o.label])))

const columns = computed(() => [
  { title: $t('common.name'), key: 'name', ellipsis: { tooltip: true } },
  {
    title: $t('genome.source'),
    key: 'sourceType',
    width: 120,
    render: (row: any) => h(NTag, { size: 'small', type: 'info' }, () => sourceLabels.value[row.sourceType] || row.sourceType),
  },
  {
    title: $t('genome.tags'),
    key: 'tags',
    width: 200,
    render: (row: any) => {
      const tags = row.tags || []
      return h(NSpace, { size: 'small' }, () => tags.slice(0, 3).map((t: string) => h(NTag, { size: 'tiny' }, () => t)))
    },
  },
  { title: $t('common.createdAt'), key: 'createdAt', width: 180 },
  {
    title: $t('common.actions'),
    key: 'actions',
    width: 160,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { text: true, type: 'primary', onClick: () => router.push(`/genomes/${row.id}`) }, () => $t('common.view')),
      h(NButton, { text: true, type: 'error', onClick: () => handleDelete(row.id) }, () => $t('common.delete')),
    ]),
  },
])

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
