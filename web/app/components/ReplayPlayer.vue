<template>
  <n-card :title="$t('timeMachine.replay')" size="small" v-if="data">
    <template #header-extra>
      <n-space>
        <n-button size="tiny" @click="togglePlay">
          {{ playing ? $t('timeMachine.pause') : $t('timeMachine.play') }}
        </n-button>
        <n-select
          v-model:value="speed"
          size="tiny"
          style="width: 80px"
          :options="speedOptions"
        />
      </n-space>
    </template>

    <n-text depth="3" style="font-size: 12px">
      {{ $t('timeMachine.round') }} {{ currentRound }} / {{ data.totalRounds }} | {{ data.platform }} | {{ data.agentCount }} Agents
    </n-text>

    <n-progress
      :percentage="(currentRound / data.totalRounds) * 100"
      :show-indicator="false"
      :height="4"
      style="margin: 8px 0"
    />

    <div v-if="currentRoundData" style="max-height: 300px; overflow-y: auto">
      <n-list :show-divider="false">
        <n-list-item v-for="(p, idx) in (currentRoundData.posts || []).slice(0, 10)" :key="idx">
          <n-text depth="3" style="font-size: 12px">Agent {{ p.user_id }}:</n-text>
          <n-text>{{ p.content }}</n-text>
        </n-list-item>
      </n-list>
      <n-empty v-if="!currentRoundData.posts?.length" :description="$t('timeMachine.noPostsThisRound')" size="small" />
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'

const props = defineProps<{ data: any }>()
const emit = defineEmits<{ roundChange: [round: number] }>()

const currentRound = ref(1)
const playing = ref(false)
const speed = ref(1)
let timer: ReturnType<typeof setInterval> | null = null

const speedOptions = [
  { label: '0.5x', value: 0.5 },
  { label: '1x', value: 1 },
  { label: '2x', value: 2 },
  { label: '4x', value: 4 },
]

const currentRoundData = computed(() => {
  if (!props.data?.rounds) return null
  return props.data.rounds.find((r: any) => r.round === currentRound.value || r.round_number === currentRound.value)
})

function togglePlay() {
  if (playing.value) {
    stopPlay()
  } else {
    startPlay()
  }
}

function startPlay() {
  playing.value = true
  timer = setInterval(() => {
    if (currentRound.value >= (props.data?.totalRounds || 1)) {
      stopPlay()
      return
    }
    currentRound.value++
    emit('roundChange', currentRound.value)
  }, 2000 / speed.value)
}

function stopPlay() {
  playing.value = false
  if (timer) { clearInterval(timer); timer = null }
}

watch(speed, () => {
  if (playing.value) {
    stopPlay()
    startPlay()
  }
})

onUnmounted(stopPlay)
</script>
