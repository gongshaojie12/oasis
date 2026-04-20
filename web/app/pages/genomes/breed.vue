<template>
  <div>
    <PageHeader title="群体繁殖" subtitle="从种子基因组批量生成多样化 Agent 群体" />

    <n-grid :cols="2" :x-gap="24">
      <n-gi>
        <n-card title="繁殖配置">
          <n-form label-placement="left" label-width="100">
            <n-form-item label="批次名称">
              <n-input v-model:value="batchName" placeholder="例如：科技博主群体" />
            </n-form-item>

            <n-form-item label="种子基因组">
              <n-select
                v-model:value="selectedSeeds"
                :options="seedOptions"
                multiple
                placeholder="选择种子基因组（至少1个）"
                :loading="loadingSeeds"
              />
            </n-form-item>

            <n-form-item label="目标数量">
              <n-input-number v-model:value="targetCount" :min="1" :max="10000" />
            </n-form-item>

            <n-form-item label="突变率">
              <n-slider v-model:value="mutationRate" :min="0" :max="0.5" :step="0.01" />
              <n-text depth="3" style="margin-left: 8px">{{ mutationRate }}</n-text>
            </n-form-item>

            <n-form-item label="繁殖策略">
              <n-radio-group v-model:value="strategy">
                <n-space>
                  <n-radio value="crossover">交叉繁殖</n-radio>
                  <n-radio value="clone_mutate">克隆突变</n-radio>
                  <n-radio value="distribution">分布采样</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-space justify="end">
              <n-button type="primary" :loading="breeding" @click="handleBreed" :disabled="selectedSeeds.length === 0">
                开始繁殖
              </n-button>
            </n-space>
          </n-form>
        </n-card>
      </n-gi>

      <n-gi>
        <PopulationPreview :data="previewData" />

        <n-card title="繁殖结果" v-if="breedResult" style="margin-top: 16px">
          <n-space vertical>
            <n-statistic label="生成数量" :value="breedResult.count" />
            <n-statistic label="多样性指数" :value="breedResult.diversity" />
            <n-button type="primary" @click="$router.push('/genomes')">查看基因组列表</n-button>
          </n-space>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useGenomesStore } from '~/stores/genomes'

const message = useMessage()
const store = useGenomesStore()

const batchName = ref('')
const selectedSeeds = ref<string[]>([])
const targetCount = ref(50)
const mutationRate = ref(0.15)
const strategy = ref('crossover')
const breeding = ref(false)
const loadingSeeds = ref(false)
const seedOptions = ref<any[]>([])
const previewData = ref<any>(null)
const breedResult = ref<any>(null)

onMounted(async () => {
  loadingSeeds.value = true
  await store.fetchList({ pageSize: 100 })
  seedOptions.value = store.items.map(g => ({ label: g.name, value: g.id }))
  loadingSeeds.value = false
})

async function handleBreed() {
  if (!batchName.value) { message.warning('请输入批次名称'); return }
  if (selectedSeeds.value.length === 0) { message.warning('请选择至少一个种子基因组'); return }

  breeding.value = true
  try {
    const res = await store.breed({
      name: batchName.value,
      seedGenomeIds: selectedSeeds.value,
      targetCount: targetCount.value,
      mutationRate: mutationRate.value,
      strategy: strategy.value,
    })
    if (res.code === 0) {
      breedResult.value = res.data
      message.success(`成功生成 ${res.data.count} 个基因组`)
      await loadPreview(res.data.genomeIds)
    } else {
      message.error(res.message)
    }
  } finally {
    breeding.value = false
  }
}

async function loadPreview(genomeIds: string[]) {
  await store.fetchList({ pageSize: 100 })
  const genomes = store.items
    .filter(g => genomeIds.includes(g.id))
    .map(g => g.genomeData)
  if (genomes.length > 0) {
    const res = await store.preview(genomes)
    if (res.code === 0) {
      previewData.value = res.data
    }
  }
}
</script>
