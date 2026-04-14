<template>
  <div class="sidebar">
    <div class="sidebar-logo">
      <Icon name="carbon:analytics" size="28" />
      <span class="logo-text">OASIS</span>
    </div>

    <nav class="sidebar-nav">
      <NuxtLink
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        active-class="nav-item--active"
      >
        <Icon :name="item.icon" size="20" />
        <span>{{ item.label }}</span>
      </NuxtLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
const menuItems = [
  { path: '/dashboard', icon: 'carbon:dashboard', label: '工作台' },
  { path: '/simulations', icon: 'carbon:play-outline', label: '模拟任务' },
  { path: '/reports', icon: 'carbon:report', label: '报告中心' },
  { path: '/templates', icon: 'carbon:template', label: '模板管理' },
  { path: '/settings', icon: 'carbon:settings', label: '企业设置' },
]
</script>

<style scoped>
.sidebar {
  width: 220px;
  height: 100%;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-logo {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--border-color);
  color: var(--accent-blue);
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}

.sidebar-nav {
  padding: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item--active {
  background: rgba(59, 130, 246, 0.1);
  color: var(--accent-blue);
}
</style>
