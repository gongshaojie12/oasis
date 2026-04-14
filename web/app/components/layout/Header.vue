<template>
  <header class="app-header">
    <div class="header-left">
      <span class="enterprise-name">{{ enterpriseName }}</span>
    </div>
    <div class="header-right">
      <div class="quota-info" v-if="quota !== null">
        <Icon name="carbon:cube" size="16" />
        <span>剩余 {{ quota }} 次</span>
      </div>
      <div class="user-menu" @click="handleLogout">
        <Icon name="carbon:user-avatar" size="20" />
        <span>{{ userName }}</span>
        <Icon name="carbon:logout" size="16" class="logout-icon" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const props = defineProps<{
  enterpriseName: string
  userName: string
  quota: number | null
}>()

const emit = defineEmits<{
  logout: []
}>()

function handleLogout() {
  emit('logout')
}
</script>

<style scoped>
.app-header {
  height: 56px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.enterprise-name {
  font-size: 14px;
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.quota-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--accent-blue);
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.user-menu:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.logout-icon {
  color: var(--text-secondary);
}
</style>
