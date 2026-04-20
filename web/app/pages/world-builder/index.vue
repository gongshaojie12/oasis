<template>
  <div>
    <CommonPageHeader :title="$t('worldBuilder.title')" :subtitle="$t('worldBuilder.subtitle')">
      <template #actions>
        <n-space>
          <n-button type="primary" @click="showCreate = true">{{ $t('worldBuilder.create') }}</n-button>
          <n-button @click="showImport = true">{{ $t('worldBuilder.import') }}</n-button>
        </n-space>
      </template>
    </CommonPageHeader>

    <n-spin :show="store.loading">
      <n-empty v-if="!store.items.length && !store.loading" :description="$t('worldBuilder.noData')">
        <template #extra>
          <n-button type="primary" @click="showCreate = true">{{ $t('worldBuilder.create') }}</n-button>
        </template>
      </n-empty>

      <n-grid v-if="store.items.length" :cols="3" :x-gap="16" :y-gap="16">
        <n-gi v-for="g in store.items" :key="g.id">
          <n-card hoverable style="cursor: pointer" @click="router.push(`/world-builder/${g.id}`)">
            <template #header>{{ g.name }}</template>
            <template #header-extra>
              <n-popconfirm @positive-click="handleDelete(g.id)">
                <template #trigger>
                  <n-button size="tiny" quaternary type="error" @click.stop>{{ $t('common.delete') }}</n-button>
                </template>
                {{ $t('worldBuilder.deleteConfirm') }}
              </n-popconfirm>
            </template>
            <n-space vertical>
              <n-text v-if="g.description" depth="3">{{ g.description }}</n-text>
              <n-space>
                <n-tag size="small" type="info">{{ $t('worldBuilder.nodeCount', { count: g.nodeCount }) }}</n-tag>
                <n-tag size="small" type="success">{{ $t('worldBuilder.edgeCount', { count: g.edgeCount }) }}</n-tag>
              </n-space>
              <n-text depth="3" style="font-size: 12px">{{ formatTime(g.updatedAt) }}</n-text>
            </n-space>
          </n-card>
        </n-gi>
      </n-grid>
    </n-spin>

    <n-modal v-model:show="showCreate" :title="$t('worldBuilder.create')" preset="card" style="width: 450px">
      <n-form>
        <n-form-item :label="$t('common.name')">
          <n-input v-model:value="createForm.name" :placeholder="$t('worldBuilder.namePlaceholder')" />
        </n-form-item>
        <n-form-item :label="$t('worldBuilder.description')">
          <n-input v-model:value="createForm.description" type="textarea" :placeholder="$t('worldBuilder.descriptionPlaceholder')" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="handleCreate" :loading="creating">{{ $t('common.create') }}</n-button>
      </template>
    </n-modal>

    <n-modal v-model:show="showImport" :title="$t('worldBuilder.import')" preset="card" style="width: 500px">
      <n-form>
        <n-form-item :label="$t('common.name')">
          <n-input v-model:value="importForm.name" :placeholder="$t('worldBuilder.namePlaceholder')" />
        </n-form-item>
        <n-form-item :label="$t('worldBuilder.jsonData')">
          <n-input v-model:value="importForm.json" type="textarea" :rows="8" :placeholder="$t('worldBuilder.jsonPlaceholder')" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="handleImport" :loading="importing">{{ $t('worldBuilder.import') }}</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWorldBuilderStore } from '~/stores/world-builder'

const router = useRouter()
const message = useMessage()
const store = useWorldBuilderStore()
const { $t } = useI18n()

const showCreate = ref(false)
const showImport = ref(false)
const creating = ref(false)
const importing = ref(false)
const createForm = ref({ name: '', description: '' })
const importForm = ref({ name: '', json: '' })

function formatTime(t: string) { return t ? new Date(t).toLocaleString('zh-CN') : '-' }

async function handleCreate() {
  if (!createForm.value.name) return message.warning($t('worldBuilder.nameRequired'))
  creating.value = true
  const res = await store.create(createForm.value.name, createForm.value.description)
  creating.value = false
  if (res.code === 0) {
    showCreate.value = false
    router.push(`/world-builder/${res.data.id}`)
  } else {
    message.error(res.message)
  }
}

async function handleImport() {
  if (!importForm.value.name || !importForm.value.json) return message.warning($t('worldBuilder.fillComplete'))
  importing.value = true
  try {
    const graphData = JSON.parse(importForm.value.json)
    const res = await store.importGraph(importForm.value.name, graphData)
    if (res.code === 0) {
      showImport.value = false
      message.success($t('worldBuilder.importSuccess', { count: res.data.nodeCount }))
      await store.fetchList()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error($t('worldBuilder.jsonError'))
  }
  importing.value = false
}

async function handleDelete(id: string) {
  const res = await store.remove(id)
  if (res.code === 0) {
    message.success($t('common.deleteSuccess'))
    await store.fetchList()
  }
}

onMounted(() => store.fetchList())
</script>
