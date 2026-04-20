<template>
  <div v-if="genome">
    <PageHeader :title="genome.name" :subtitle="`来源: ${sourceLabels[genome.sourceType] || genome.sourceType}`">
      <template #actions>
        <n-space>
          <n-button @click="editing = !editing">{{ editing ? '取消编辑' : '编辑' }}</n-button>
          <n-button type="primary" v-if="editing" :loading="saving" @click="handleSave">保存</n-button>
        </n-space>
      </template>
    </PageHeader>

    <n-grid :cols="2" :x-gap="24">
      <n-gi>
        <n-card title="人格特质">
          <GenomeRadar :traits="genome.genomeData.traits" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="基本信息">
          <n-descriptions bordered :column="1" label-placement="left">
            <n-descriptions-item label="职业">{{ genome.genomeData.demographics?.profession }}</n-descriptions-item>
            <n-descriptions-item label="MBTI">{{ genome.genomeData.demographics?.mbti || '未知' }}</n-descriptions-item>
            <n-descriptions-item label="年龄范围">{{ genome.genomeData.demographics?.age_range?.join('-') }}</n-descriptions-item>
            <n-descriptions-item label="兴趣">{{ genome.genomeData.demographics?.interests?.join(', ') }}</n-descriptions-item>
            <n-descriptions-item label="活跃度">{{ genome.genomeData.social_behavior?.activity_level }}</n-descriptions-item>
            <n-descriptions-item label="影响力">{{ genome.genomeData.social_behavior?.influence_weight }}</n-descriptions-item>
            <n-descriptions-item label="信息茧房倾向">{{ genome.genomeData.social_behavior?.echo_chamber_tendency }}</n-descriptions-item>
          </n-descriptions>
        </n-card>
      </n-gi>
    </n-grid>

    <n-card title="原始数据" style="margin-top: 16px" v-if="!editing">
      <n-code :code="JSON.stringify(genome.genomeData, null, 2)" language="json" />
    </n-card>

    <n-card title="编辑基因组数据" style="margin-top: 16px" v-if="editing">
      <n-input
        v-model:value="editJson"
        type="textarea"
        :rows="20"
        font-family="monospace"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useGenomesStore } from '~/stores/genomes'

const route = useRoute()
const message = useMessage()
const store = useGenomesStore()

const genome = ref<any>(null)
const editing = ref(false)
const saving = ref(false)
const editJson = ref('')

const sourceLabels: Record<string, string> = {
  manual: '手动创建', document: '文档提取', url: 'URL提取',
  csv: 'CSV导入', natural_language: '自然语言', breed: '繁殖生成',
}

onMounted(async () => {
  const res = await store.fetchOne(route.params.id as string)
  if (res.code === 0) {
    genome.value = res.data
    editJson.value = JSON.stringify(res.data.genomeData, null, 2)
  }
})

async function handleSave() {
  saving.value = true
  try {
    const parsed = JSON.parse(editJson.value)
    const res = await store.update(genome.value.id, { genomeData: parsed })
    if (res.code === 0) {
      genome.value.genomeData = parsed
      editing.value = false
      message.success('已保存')
    } else {
      message.error(res.message)
    }
  } catch (e: any) {
    message.error('JSON 格式错误')
  } finally {
    saving.value = false
  }
}
</script>
