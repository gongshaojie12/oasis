<template>
  <div>
    <PageHeader title="新建基因组" subtitle="从多种数据源创建人格基因组" />

    <n-card>
      <n-steps :current="step" style="margin-bottom: 24px">
        <n-step title="选择来源" />
        <n-step title="输入内容" />
        <n-step title="确认结果" />
      </n-steps>

      <!-- Step 1: 选择来源 -->
      <div v-if="step === 1">
        <n-radio-group v-model:value="sourceType" size="large">
          <n-space vertical :size="12">
            <n-radio value="natural_language">自然语言描述 — 用一段话描述人物画像</n-radio>
            <n-radio value="manual">手动配置 — 逐项填写人格参数</n-radio>
            <n-radio value="csv">CSV/JSON 导入 — 从结构化数据导入</n-radio>
          </n-space>
        </n-radio-group>
        <n-space justify="end" style="margin-top: 24px">
          <n-button type="primary" @click="step = 2">下一步</n-button>
        </n-space>
      </div>

      <!-- Step 2: 输入内容 -->
      <div v-if="step === 2">
        <n-form-item label="名称">
          <n-input v-model:value="name" placeholder="为这个基因组起个名字" />
        </n-form-item>

        <!-- 自然语言模式 -->
        <div v-if="sourceType === 'natural_language'">
          <n-form-item label="人物描述">
            <n-input
              v-model:value="textContent"
              type="textarea"
              :rows="6"
              placeholder="描述这个人物的性格、职业、兴趣、社交习惯等。例如：一个30岁的科技记者，性格外向，喜欢追踪AI和新能源领域的前沿动态，在社交媒体上非常活跃..."
            />
          </n-form-item>
        </div>

        <!-- 手动模式 -->
        <div v-if="sourceType === 'manual'">
          <n-h4>五大人格特质</n-h4>
          <n-grid :cols="2" :x-gap="16" :y-gap="8">
            <n-gi v-for="(label, key) in traitLabels" :key="key">
              <n-form-item :label="label">
                <n-slider v-model:value="manualGenome.traits[key]" :min="0" :max="1" :step="0.05" />
              </n-form-item>
            </n-gi>
          </n-grid>
          <n-h4>人口统计</n-h4>
          <n-grid :cols="2" :x-gap="16">
            <n-gi>
              <n-form-item label="职业">
                <n-input v-model:value="manualGenome.demographics.profession" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="MBTI">
                <n-select v-model:value="manualGenome.demographics.mbti" :options="mbtiOptions" />
              </n-form-item>
            </n-gi>
          </n-grid>
          <n-form-item label="兴趣（用逗号分隔）">
            <n-input v-model:value="interestsStr" placeholder="科技, 游戏, 金融" />
          </n-form-item>
        </div>

        <!-- CSV 模式 -->
        <div v-if="sourceType === 'csv'">
          <n-form-item label="粘贴 JSON 数据">
            <n-input
              v-model:value="csvContent"
              type="textarea"
              :rows="8"
              placeholder='{"name": "张三", "age": 30, "interests": "科技,游戏", "personality": "内向理性"}'
            />
          </n-form-item>
        </div>

        <n-space justify="space-between" style="margin-top: 24px">
          <n-button @click="step = 1">上一步</n-button>
          <n-button type="primary" :loading="extracting" @click="handleExtract">
            {{ sourceType === 'manual' ? '下一步' : 'AI 分析生成' }}
          </n-button>
        </n-space>
      </div>

      <!-- Step 3: 确认结果 -->
      <div v-if="step === 3 && resultGenome">
        <n-grid :cols="2" :x-gap="24">
          <n-gi>
            <GenomeRadar :traits="resultGenome.traits" title="人格特质雷达图" />
          </n-gi>
          <n-gi>
            <n-descriptions bordered :column="1" label-placement="left">
              <n-descriptions-item label="职业">{{ resultGenome.demographics.profession }}</n-descriptions-item>
              <n-descriptions-item label="MBTI">{{ resultGenome.demographics.mbti || '未知' }}</n-descriptions-item>
              <n-descriptions-item label="年龄范围">{{ resultGenome.demographics.age_range?.join('-') }}</n-descriptions-item>
              <n-descriptions-item label="兴趣">{{ resultGenome.demographics.interests?.join(', ') }}</n-descriptions-item>
              <n-descriptions-item label="活跃度">{{ resultGenome.social_behavior.activity_level }}</n-descriptions-item>
              <n-descriptions-item label="影响力">{{ resultGenome.social_behavior.influence_weight }}</n-descriptions-item>
            </n-descriptions>
          </n-gi>
        </n-grid>

        <n-space justify="space-between" style="margin-top: 24px">
          <n-button @click="step = 2">返回修改</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">保存基因组</n-button>
        </n-space>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useGenomesStore } from '~/stores/genomes'

const router = useRouter()
const message = useMessage()
const store = useGenomesStore()

const step = ref(1)
const sourceType = ref('natural_language')
const name = ref('')
const textContent = ref('')
const csvContent = ref('')
const extracting = ref(false)
const saving = ref(false)
const resultGenome = ref<any>(null)

const traitLabels: Record<string, string> = {
  openness: '开放性', conscientiousness: '尽责性', extraversion: '外向性',
  agreeableness: '宜人性', neuroticism: '神经质',
}

const mbtiOptions = ['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP',
  'ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP'].map(v => ({ label: v, value: v }))

const manualGenome = ref({
  traits: { openness: 0.5, conscientiousness: 0.5, extraversion: 0.5, agreeableness: 0.5, neuroticism: 0.5 },
  social_behavior: { activity_level: 0.5, content_creation_ratio: 0.5, interaction_preference: 'balanced', influence_weight: 0.5, echo_chamber_tendency: 0.3 },
  opinion_spectrum: { topic_stances: {}, persuadability: 0.5, stance_volatility: 0.3 },
  demographics: { age_range: [20, 40], profession: '', interests: [] as string[], mbti: null as string | null },
  behavioral_patterns: { peak_activity_hours: [9, 12, 20], avg_post_length: 'medium', emoji_usage: 0.3, hashtag_usage: 0.3 },
})

const interestsStr = ref('')

async function handleExtract() {
  if (!name.value) { message.warning('请输入名称'); return }

  if (sourceType.value === 'manual') {
    manualGenome.value.demographics.interests = interestsStr.value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
    resultGenome.value = manualGenome.value
    step.value = 3
    return
  }

  extracting.value = true
  try {
    const payload: any = { sourceType: sourceType.value }
    if (sourceType.value === 'natural_language') {
      payload.content = textContent.value
    } else if (sourceType.value === 'csv') {
      payload.structuredData = JSON.parse(csvContent.value)
    }
    const res = await store.extract(payload)
    if (res.code === 0) {
      resultGenome.value = res.data.genome
      step.value = 3
    } else {
      message.error(res.message)
    }
  } catch (e: any) {
    message.error('提取失败: ' + e.message)
  } finally {
    extracting.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const res = await store.create({
      name: name.value,
      sourceType: sourceType.value,
      genomeData: resultGenome.value,
    })
    if (res.code === 0) {
      message.success('基因组已保存')
      router.push('/genomes')
    } else {
      message.error(res.message)
    }
  } finally {
    saving.value = false
  }
}
</script>
