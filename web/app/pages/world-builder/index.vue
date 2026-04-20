<template>
  <div>
    <CommonPageHeader title="世界构建器" subtitle="通过知识图谱构建社交世界">
      <template #actions>
        <n-space>
          <n-button type="primary" @click="showCreate = true">新建图谱</n-button>
          <n-button @click="showImport = true">导入 JSON</n-button>
        </n-space>
      </template>
    </CommonPageHeader>

    <n-spin :show="store.loading">
      <n-empty v-if="!store.items.length && !store.loading" description="还没有图谱，创建一个开始构建世界">
        <template #extra>
          <n-button type="primary" @click="showCreate = true">新建图谱</n-button>
        </template>
      </n-empty>

      <n-grid v-if="store.items.length" :cols="3" :x-gap="16" :y-gap="16">
        <n-gi v-for="g in store.items" :key="g.id">
          <n-card hoverable style="cursor: pointer" @click="router.push(`/world-builder/${g.id}`)">
            <template #header>{{ g.name }}</template>
            <template #header-extra>
              <n-popconfirm @positive-click="handleDelete(g.id)">
                <template #trigger>
                  <n-button size="tiny" quaternary type="error" @click.stop>删除</n-button>
                </template>
                确定删除此图谱？
              </n-popconfirm>
            </template>
            <n-space vertical>
              <n-text v-if="g.description" depth="3">{{ g.description }}</n-text>
              <n-space>
                <n-tag size="small" type="info">{{ g.nodeCount }} 个节点</n-tag>
                <n-tag size="small" type="success">{{ g.edgeCount }} 条关系</n-tag>
              </n-space>
              <n-text depth="3" style="font-size: 12px">{{ formatTime(g.updatedAt) }}</n-text>
            </n-space>
          </n-card>
        </n-gi>
      </n-grid>
    </n-spin>

    <n-modal v-model:show="showCreate" title="新建图谱" preset="card" style="width: 450px">
      <n-form>
        <n-form-item label="名称">
          <n-input v-model:value="createForm.name" placeholder="输入图谱名称" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="createForm.description" type="textarea" placeholder="可选描述" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="handleCreate" :loading="creating">创建</n-button>
      </template>
    </n-modal>

    <n-modal v-model:show="showImport" title="导入图谱" preset="card" style="width: 500px">
      <n-form>
        <n-form-item label="名称">
          <n-input v-model:value="importForm.name" placeholder="图谱名称" />
        </n-form-item>
        <n-form-item label="JSON 数据">
          <n-input v-model:value="importForm.json" type="textarea" :rows="8" placeholder='{"nodes": [...], "edges": [...]}' />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="handleImport" :loading="importing">导入</n-button>
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

const showCreate = ref(false)
const showImport = ref(false)
const creating = ref(false)
const importing = ref(false)
const createForm = ref({ name: '', description: '' })
const importForm = ref({ name: '', json: '' })

function formatTime(t: string) { return t ? new Date(t).toLocaleString('zh-CN') : '-' }

async function handleCreate() {
  if (!createForm.value.name) return message.warning('请输入名称')
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
  if (!importForm.value.name || !importForm.value.json) return message.warning('请填写完整')
  importing.value = true
  try {
    const graphData = JSON.parse(importForm.value.json)
    const res = await store.importGraph(importForm.value.name, graphData)
    if (res.code === 0) {
      showImport.value = false
      message.success(`已导入 ${res.data.nodeCount} 个节点`)
      await store.fetchList()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('JSON 格式错误')
  }
  importing.value = false
}

async function handleDelete(id: string) {
  const res = await store.remove(id)
  if (res.code === 0) {
    message.success('已删除')
    await store.fetchList()
  }
}

onMounted(() => store.fetchList())
</script>
