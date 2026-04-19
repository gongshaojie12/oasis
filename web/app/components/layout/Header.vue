<template>
  <header class="app-header">
    <div class="header-left">
      <span class="enterprise-name">{{ enterpriseName }}</span>
    </div>
    <div class="header-right">
      <div class="quota-badge" v-if="quota !== null">
        <Icon name="carbon:cube" size="15" />
        <span>{{ quota }} 次配额</span>
      </div>
      <div class="header-divider" />
      <div class="user-menu" @click="handleLogout">
        <div class="user-avatar">
          <Icon name="carbon:user-avatar-filled" size="18" />
        </div>
        <span class="user-name">{{ userName }}</span>
        <Icon name="carbon:chevron-down" size="14" class="chevron-icon" />
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
  height: 60px;
  background: #ffffff;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
}

.enterprise-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
}

.quota-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--accent-blue);
  padding: 5px 14px;
  background: #eef1fe;
  border-radius: 20px;
  font-weight: 500;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s;
}

.user-menu:hover {
  background: var(--bg-hover);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #eef1fe;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-blue);
}

.user-name {
  font-weight: 500;
}

.chevron-icon {
  color: var(--text-secondary);
}
</style>
