<template>
  <div style="display: flex; flex-direction: column; height: calc(100vh - 120px)">
    <CommonPageHeader :title="store.current?.name || '图谱编辑器'">
      <template #actions>
        <GraphToolbar
          @add-node="addNode"
          @auto-layout="autoLayout"
          @analyze="runAnalyze"
          @export-json="exportJson"
          @to-simulation="toSimulation"
        />
      </template>
    </CommonPageHeader>

    <n-spin :show="store.loading" style="flex: 1; min-height: 0">
      <div style="display: flex; height: 100%">
        <div style="flex: 1; position: relative">
          <GraphEditor
            :nodes="nodes"
            :edges="edges"
            @node-click="selectedNode = $event"
          />

          <div v-if="analysisResult" style="position: absolute; bottom: 16px; left: 16px; z-index: 10">
            <n-card size="small" style="max-width: 300px; opacity: 0.95">
              <template #header>{{ $t('worldBuilder.analysisResult') }}</template>
              <n-space vertical size="small">
                <n-text>{{ $t('worldBuilder.nodeCount', { count: analysisResult.node_count }) }} | {{ $t('worldBuilder.edgeCount', { count: analysisResult.edge_count }) }}</n-text>
                <n-text>{{ $t('worldBuilder.density') }}: {{ analysisResult.density }}</n-text>
                <n-text>{{ $t('worldBuilder.communities') }}: {{ analysisResult.communities?.length || 0 }}</n-text>
              </n-space>
            </n-card>
          </div>
        </div>
      </div>
    </n-spin>

    <GraphNodePanel
      :node="selectedNode"
      @close="selectedNode = null"
      @save="updateNode"
      @delete="deleteNode"
    />

    <n-modal v-model:show="showEdgeModal" :title="$t('worldBuilder.addEdge')" preset="card" style="width: 400px">
      <n-form>
        <n-form-item :label="$t('worldBuilder.source')">
          <n-select v-model:value="edgeForm.source" :options="nodeSelectOptions" />
        </n-form-item>
        <n-form-item :label="$t('worldBuilder.target')">
          <n-select v-model:value="edgeForm.target" :options="nodeSelectOptions" />
        </n-form-item>
        <n-form-item :label="$t('worldBuilder.edgeType')">
          <n-select v-model:value="edgeForm.type" :options="edgeTypeOptions" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="addEdge">{{ $t('common.add') }}</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWorldBuilderStore } from '~/stores/world-builder'

const route = useRoute()
const message = useMessage()
const store = useWorldBuilderStore()
const { $t } = useI18n()

const id = route.params.id as string
const selectedNode = ref<any>(null)
const analysisResult = ref<any>(null)
const showEdgeModal = ref(false)
const edgeForm = ref({ source: '', target: '', type: 'follows' })

const nodes = computed(() => store.current?.graphData?.nodes || [])
const edges = computed(() => store.current?.graphData?.edges || [])

const nodeSelectOptions = computed(() =>
  nodes.value.map((n: any) => ({ label: n.label, value: n.id }))
)

const edgeTypeOptions = computed(() => [
  { label: $t('worldBuilder.edgeTypes.follows'), value: 'follows' },
  { label: $t('worldBuilder.edgeTypes.opposes'), value: 'opposes' },
  { label: $t('worldBuilder.edgeTypes.belongs_to'), value: 'belongs_to' },
  { label: $t('worldBuilder.edgeTypes.interested_in'), value: 'interested_in' },
  { label: $t('worldBuilder.edgeTypes.influences'), value: 'influences' },
  { label: $t('worldBuilder.edgeTypes.publishes'), value: 'publishes' },
])

let counter = 0

function addNode(type: string) {
  counter++
  const typeLabels: Record<string, string> = {
    person: '人物', organization: '组织', topic: '话题', community: '社区', content: '内容',
  }
  const node = {
    id: `n_${Date.now()}_${counter}`,
    type,
    label: `${typeLabels[type] || type} ${counter}`,
    x: 300 + Math.random() * 200,
    y: 200 + Math.random() * 200,
    properties: {},
  }
  const newNodes = [...nodes.value, node]
  saveGraph(newNodes, edges.value)
  showEdgeModal.value = true
  edgeForm.value.source = node.id
}

function addEdge() {
  if (!edgeForm.value.source || !edgeForm.value.target) return message.warning($t('worldBuilder.selectSourceTarget'))
  if (edgeForm.value.source === edgeForm.value.target) return message.warning($t('worldBuilder.noSelfLoop'))
  const edge = {
    id: `e_${Date.now()}`,
    source: edgeForm.value.source,
    target: edgeForm.value.target,
    type: edgeForm.value.type,
    weight: 1.0,
    properties: {},
  }
  saveGraph(nodes.value, [...edges.value, edge])
  showEdgeModal.value = false
}

function updateNode(data: any) {
  const newNodes = nodes.value.map((n: any) => n.id === data.id ? data : n)
  saveGraph(newNodes, edges.value)
  selectedNode.value = null
}

function deleteNode(nodeId: string) {
  const newNodes = nodes.value.filter((n: any) => n.id !== nodeId)
  const newEdges = edges.value.filter((e: any) => e.source !== nodeId && e.target !== nodeId)
  saveGraph(newNodes, newEdges)
  selectedNode.value = null
}

function autoLayout() {
  const newNodes = nodes.value.map((n: any, i: number) => ({
    ...n,
    x: 300 + Math.cos(i * 2 * Math.PI / nodes.value.length) * 200,
    y: 300 + Math.sin(i * 2 * Math.PI / nodes.value.length) * 200,
  }))
  saveGraph(newNodes, edges.value)
}

async function saveGraph(newNodes: any[], newEdges: any[]) {
  const res = await store.update(id, {
    graphData: { nodes: newNodes, edges: newEdges },
  })
  if (res.code === 0) {
    await store.fetchOne(id)
  }
}

async function runAnalyze() {
  const res = await store.analyze(id)
  if (res.code === 0) {
    analysisResult.value = res.data
    message.success($t('worldBuilder.analyzeComplete'))
  } else {
    message.error(res.message)
  }
}

function exportJson() {
  const data = JSON.stringify(store.current?.graphData || {}, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.current?.name || 'graph'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function toSimulation() {
  const res = await store.toSimulation(id)
  if (res.code === 0) {
    message.success($t('worldBuilder.toSimulationSuccess', { count: res.data.num_agents }))
  } else {
    message.error(res.message)
  }
}

onMounted(() => store.fetchOne(id))
</script>
