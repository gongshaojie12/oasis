<template>
  <div>
    <CommonPageHeader title="时间机器" :subtitle="simName">
      <template #actions>
        <n-space>
          <n-button @click="showRoundtable = true" :disabled="!store.snapshots.length">圆桌会议</n-button>
          <n-button @click="loadReplay" :disabled="!store.snapshots.length">情境重放</n-button>
          <n-button @click="router.push(`/simulations/${simId}`)">返回仿真</n-button>
        </n-space>
      </template>
    </CommonPageHeader>

    <n-spin :show="store.loading">
      <n-empty v-if="!store.snapshots.length && !store.loading" description="仿真未完成或快照数据不可用">
        <template #extra>
          <n-button @click="router.push(`/simulations/${simId}`)">返回仿真详情</n-button>
        </template>
      </n-empty>

      <div v-if="store.snapshots.length" style="display: flex; flex-direction: column; gap: 16px">
        <TimelineSlider v-model="store.currentRound" :max="totalRounds" @update:model-value="onRoundChange" />

        <SnapshotViewer
          :snapshot="store.currentSnapshot"
          @select-agent="openChat"
        />

        <ReplayPlayer
          v-if="store.replayData"
          :data="store.replayData"
          @round-change="onRoundChange"
        />
      </div>
    </n-spin>

    <AgentChatPanel
      :agent-id="chatAgentId"
      :agent-name="chatAgentName"
      :round-context="store.currentRound"
      :messages="store.chatMessages"
      :loading="store.chatLoading"
      @close="closeChat"
      @send="handleChatSend"
    />

    <n-modal v-model:show="showRoundtable" title="发起圆桌会议" preset="card" style="width: 500px">
      <n-form>
        <n-form-item label="讨论话题">
          <n-input v-model:value="roundtableForm.topic" placeholder="输入讨论话题" />
        </n-form-item>
        <n-form-item label="参与 Agent (点击选择)">
          <n-select
            v-model:value="roundtableForm.agentIds"
            multiple
            :options="agentOptions"
            placeholder="选择 2-8 个 Agent"
          />
        </n-form-item>
        <n-form-item label="讨论轮数">
          <n-input-number v-model:value="roundtableForm.numRounds" :min="1" :max="5" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" :loading="store.chatLoading" @click="startRoundtable">开始讨论</n-button>
      </template>
    </n-modal>

    <n-modal v-model:show="showRoundtableResult" title="圆桌会议记录" preset="card" style="width: 600px">
      <div style="max-height: 500px; overflow-y: auto">
        <div
          v-for="(msg, idx) in store.roundtableMessages"
          :key="idx"
          style="margin-bottom: 12px; padding: 10px; background: #f9f9f9; border-radius: 8px"
        >
          <n-text strong>{{ msg.agent_name }}</n-text>
          <n-text style="display: block; margin-top: 4px">{{ msg.content }}</n-text>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTimeMachineStore } from '~/stores/timemachine'
import { useSimulationsStore } from '~/stores/simulations'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const store = useTimeMachineStore()
const simStore = useSimulationsStore()

const simId = route.params.id as string

const chatAgentId = ref<number | null>(null)
const chatAgentName = ref('')
const showRoundtable = ref(false)
const showRoundtableResult = ref(false)
const roundtableForm = ref({ topic: '', agentIds: [] as number[], numRounds: 3 })

const simName = computed(() => simStore.currentSimulation?.name || '仿真')
const totalRounds = computed(() => store.snapshots.length || 1)

const agentOptions = computed(() => {
  if (!store.currentSnapshot?.agent_summaries) return []
  return store.currentSnapshot.agent_summaries.map((a: any) => ({
    label: a.user_name,
    value: a.agent_id,
  }))
})

function onRoundChange(round: number) {
  store.setRound(round)
}

function openChat(agentId: number, agentName: string) {
  store.clearChat()
  chatAgentId.value = agentId
  chatAgentName.value = agentName
}

function closeChat() {
  chatAgentId.value = null
}

async function handleChatSend(text: string) {
  if (!chatAgentId.value) return
  const res = await store.sendChat(simId, chatAgentId.value, store.currentRound, text)
  if (res.code !== 0) message.error(res.message)
}

async function startRoundtable() {
  if (!roundtableForm.value.topic) return message.warning('请输入讨论话题')
  if (roundtableForm.value.agentIds.length < 2) return message.warning('至少选择 2 个 Agent')

  const res = await store.startRoundtable(
    simId,
    roundtableForm.value.agentIds,
    store.currentRound,
    roundtableForm.value.topic,
    roundtableForm.value.numRounds,
  )
  if (res.code === 0) {
    showRoundtable.value = false
    showRoundtableResult.value = true
  } else {
    message.error(res.message)
  }
}

async function loadReplay() {
  const res = await store.fetchReplay(simId)
  if (res.code !== 0) message.error(res.message)
}

onMounted(async () => {
  await simStore.fetchOne(simId)
  await store.fetchSnapshots(simId)
})
</script>
