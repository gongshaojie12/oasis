<template>
  <n-drawer :show="!!agentId" :width="420" placement="right" @update:show="$emit('close')">
    <n-drawer-content :title="`与 ${agentName} 对话 (第${roundContext}轮)`" closable>
      <div class="chat-messages" ref="messagesRef">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['chat-bubble', msg.role === 'user' ? 'chat-user' : 'chat-agent']"
        >
          <n-text depth="3" style="font-size: 11px">{{ msg.role === 'user' ? '你' : msg.agent_name || agentName }}</n-text>
          <n-text>{{ msg.content }}</n-text>
        </div>
        <div v-if="loading" style="text-align: center; padding: 12px">
          <n-spin size="small" />
        </div>
      </div>

      <template #footer>
        <n-input-group>
          <n-input
            v-model:value="inputText"
            placeholder="输入消息..."
            :disabled="loading"
            @keydown.enter.prevent="send"
          />
          <n-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="send">
            发送
          </n-button>
        </n-input-group>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  agentId: number | null
  agentName: string
  roundContext: number
  messages: any[]
  loading: boolean
}>()

const emit = defineEmits<{
  close: []
  send: [message: string]
}>()

const inputText = ref('')
const messagesRef = ref<HTMLElement>()

function send() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
}

watch(() => props.messages.length, () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 12px;
}

.chat-bubble {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 85%;
}

.chat-user {
  align-self: flex-end;
  background: #e8f4fd;
}

.chat-agent {
  align-self: flex-start;
  background: #f5f5f5;
}
</style>
