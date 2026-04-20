<template>
  <NCard class="post-stream">
    <h3>{{ t('liveControl.postStream') }}</h3>
    <div v-if="posts.length === 0" class="empty-stream">
      <Icon name="carbon:chat-bot" size="32" />
      <span>{{ t('liveControl.noPosts') }}</span>
    </div>
    <div v-else class="stream-list" ref="listRef">
      <div v-for="(post, idx) in posts" :key="idx" class="stream-item" :class="{ 'new-item': idx === 0 }">
        <div class="post-header">
          <span class="post-agent">{{ post.agent_name || `Agent #${post.agent_id}` }}</span>
          <span class="post-time">{{ formatTime(post.created_at || post.timestamp) }}</span>
        </div>
        <div class="post-content">{{ post.content || post.text }}</div>
        <div v-if="post.action" class="post-action">
          <NTag size="tiny" :bordered="false">{{ post.action }}</NTag>
        </div>
      </div>
    </div>
  </NCard>
</template>

<script setup lang="ts">
import { NCard, NTag } from 'naive-ui'

const { t } = useI18n()

defineProps<{
  posts: any[]
}>()

const listRef = ref<HTMLElement>()

function formatTime(ts: any) {
  if (!ts) return ''
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  return d.toLocaleTimeString()
}
</script>

<style scoped>
.post-stream {
  background: #ffffff !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow-sm);
}

.post-stream h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.empty-stream {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px;
  color: var(--text-secondary);
}

.stream-list {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stream-item {
  padding: 10px 12px;
  background: var(--bg-secondary, #f9f9f9);
  border-radius: 10px;
  transition: background 0.3s;
}

.stream-item.new-item {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.post-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.post-agent {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-blue);
}

.post-time {
  font-size: 11px;
  color: var(--text-secondary);
}

.post-content {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
}

.post-action {
  margin-top: 4px;
}
</style>
