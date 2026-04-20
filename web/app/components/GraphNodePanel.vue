<template>
  <n-drawer :show="!!node" :width="320" placement="right" @update:show="$emit('close')">
    <n-drawer-content :title="node ? `编辑: ${node.label}` : ''" closable>
      <n-form v-if="node" label-placement="top" size="small">
        <n-form-item label="名称">
          <n-input v-model:value="form.label" />
        </n-form-item>
        <n-form-item label="类型">
          <n-tag :type="typeColor(node.type)" size="small">{{ typeLabel(node.type) }}</n-tag>
        </n-form-item>
        <n-form-item label="自定义属性">
          <n-dynamic-input
            v-model:value="propEntries"
            :on-create="() => ({ key: '', value: '' })"
          >
            <template #default="{ value }">
              <n-space>
                <n-input v-model:value="value.key" placeholder="键" style="width: 100px" />
                <n-input v-model:value="value.value" placeholder="值" style="width: 120px" />
              </n-space>
            </template>
          </n-dynamic-input>
        </n-form-item>
        <n-space>
          <n-button type="primary" size="small" @click="save">保存</n-button>
          <n-button type="error" size="small" @click="$emit('delete', node.id)">删除节点</n-button>
        </n-space>
      </n-form>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ node: any | null }>()
const emit = defineEmits<{
  close: []
  save: [data: any]
  delete: [id: string]
}>()

const form = ref({ label: '' })
const propEntries = ref<{ key: string; value: string }[]>([])

watch(() => props.node, (n) => {
  if (n) {
    form.value.label = n.label
    propEntries.value = Object.entries(n.properties || {}).map(([key, value]) => ({
      key, value: String(value),
    }))
  }
}, { immediate: true })

const typeLabels: Record<string, string> = {
  person: '人物', organization: '组织', topic: '话题', community: '社区', content: '内容',
}

const typeColors: Record<string, string> = {
  person: 'info', organization: 'success', topic: 'warning', community: 'error', content: 'default',
}

function typeLabel(t: string) { return typeLabels[t] || t }
function typeColor(t: string): any { return typeColors[t] || 'default' }

function save() {
  const properties: Record<string, string> = {}
  for (const e of propEntries.value) {
    if (e.key) properties[e.key] = e.value
  }
  emit('save', { ...props.node, label: form.value.label, properties })
}
</script>
