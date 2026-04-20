<template>
  <n-card :title="$t('analysis.debateLog')">
    <n-collapse>
      <n-collapse-item
        v-for="round in rounds"
        :key="round"
        :title="$t('analysis.debateRound', { round })"
      >
        <div v-for="(msg, i) in getMessagesForRound(round)" :key="i" style="margin-bottom: 12px">
          <n-card size="small" :bordered="true">
            <template #header>
              <n-space align="center">
                <n-tag :type="roleColor(msg.speaker)" size="small">{{ roleLabel(msg.speaker) }}</n-tag>
                <n-tag v-if="msg.message_type === 'challenge'" type="warning" size="tiny">{{ $t('analysis.challenge') }}</n-tag>
                <n-tag v-if="msg.target" size="tiny">→ {{ roleLabel(msg.target) }}</n-tag>
              </n-space>
            </template>
            <n-text>{{ msg.content }}</n-text>
          </n-card>
        </div>
      </n-collapse-item>
    </n-collapse>
    <n-empty v-if="!messages.length" :description="$t('analysis.noDebateLog')" />
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

import { useI18n } from 'vue-i18n'

const props = defineProps<{ messages: DebateMsg[] }>()
const { t } = useI18n()

const roleLabels = computed(() => ({
  data_analyst: t('analysis.roles.dataAnalyst'),
  sociologist: t('analysis.roles.sociologist'),
  psychologist: t('analysis.roles.psychologist'),
  devils_advocate: t('analysis.roles.devilsAdvocate'),
}))

const roleColors: Record<string, string> = {
  data_analyst: 'info',
  sociologist: 'success',
  psychologist: 'warning',
  devils_advocate: 'error',
}

function roleLabel(role: string) { return roleLabels.value[role] || role }
function roleColor(role: string): any { return roleColors[role] || 'default' }

const rounds = computed(() => [...new Set(props.messages.map(m => m.round_num))].sort())

function getMessagesForRound(round: number) {
  return props.messages.filter(m => m.round_num === round)
}
</script>
