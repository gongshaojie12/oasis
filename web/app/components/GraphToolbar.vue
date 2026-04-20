<template>
  <n-space>
    <n-dropdown :options="nodeOptions" @select="$emit('addNode', $event)">
      <n-button type="primary" size="small">添加节点</n-button>
    </n-dropdown>
    <n-button size="small" @click="$emit('autoLayout')">自动布局</n-button>
    <n-button size="small" @click="$emit('analyze')">运行分析</n-button>
    <n-button size="small" @click="$emit('exportJson')">导出 JSON</n-button>
    <n-button size="small" type="info" @click="$emit('toSimulation')">转为仿真</n-button>
  </n-space>
</template>

<script setup lang="ts">
defineEmits<{
  addNode: [type: string]
  autoLayout: []
  analyze: []
  exportJson: []
  toSimulation: []
}>()

const nodeOptions = [
  { label: '人物 (Person)', key: 'person' },
  { label: '组织 (Organization)', key: 'organization' },
  { label: '话题 (Topic)', key: 'topic' },
  { label: '社区 (Community)', key: 'community' },
  { label: '内容 (Content)', key: 'content' },
]
</script>
