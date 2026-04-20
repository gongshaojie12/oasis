<template>
  <n-card title="分析师辩论记录">
    <n-collapse>
      <n-collapse-item
        v-for="round in rounds"
        :key="round"
        :title="`第 ${round} 轮辩论`"
      >
        <div v-for="(msg, i) in getMessagesForRound(round)" :key="i" style="margin-bottom: 12px">
          <n-card size="small" :bordered="true">
            <template #header>
              <n-space align="center">
                <n-tag :type="roleColor(msg.speaker)" size="small">{{ roleLabel(msg.speaker) }}</n-tag>
                <n-tag v-if="msg.message_type === 'challenge'" type="warning" size="tiny">挑战</n-tag>
                <n-tag v-if="msg.target" size="tiny">→ {{ roleLabel(msg.target) }}</n-tag>
              </n-space>
            </template>
            <n-text>{{ msg.content }}</n-text>
          </n-card>
        </div>
      </n-collapse-item>
    </n-collapse>
    <n-empty v-if="!messages.length" description="暂无辩论记录" />
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface DebateMsg {
  round_num: number
  speaker: string
  target?: string
  content: string
  message_type: string
}

const props = defineProps<{ messages: DebateMsg[] }>()

const roleLabels: Record<string, string> = {
  data_analyst: '数据分析师',
  sociologist: '社会学家',
  psychologist: '心理学家',
  devils_advocate: '魔鬼代言人',
}

const roleColors: Record<string, string> = {
  data_analyst: 'info',
  sociologist: 'success',
  psychologist: 'warning',
  devils_advocate: 'error',
}

function roleLabel(role: string) { return roleLabels[role] || role }
function roleColor(role: string): any { return roleColors[role] || 'default' }

const rounds = computed(() => [...new Set(props.messages.map(m => m.round_num))].sort())

function getMessagesForRound(round: number) {
  return props.messages.filter(m => m.round_num === round)
}
</script>
