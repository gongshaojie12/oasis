<template>
  <div class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-icon">
        <Icon name="carbon:analytics" size="22" />
      </div>
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
        <div class="nav-icon">
          <Icon :name="item.icon" size="18" />
        </div>
        <span>{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <div class="sidebar-bottom">
      <div class="sidebar-help">
        <Icon name="carbon:help" size="16" />
        <span>帮助中心</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const menuItems = [
  { path: '/dashboard', icon: 'carbon:dashboard', label: '工作台' },
  { path: '/simulations', icon: 'carbon:play-outline', label: '模拟任务' },
  { path: '/genomes', icon: 'carbon:dna', label: '基因组列表' },
  { path: '/genomes/create', icon: 'carbon:add', label: '新建基因组' },
  { path: '/genomes/breed', icon: 'carbon:network-4', label: '群体繁殖' },
  { path: '/analysis', icon: 'carbon:data-vis-4', label: '深度分析' },
  { path: '/world-builder', icon: 'carbon:network-3-reference', label: '世界构建' },
  { path: '/reports', icon: 'carbon:report', label: '报告中心' },
  { path: '/templates', icon: 'carbon:template', label: '模板管理' },
  { path: '/settings', icon: 'carbon:settings', label: '企业设置' },
]
</script>

<style scoped>
.sidebar {
  width: 230px;
  height: 100%;
  background: #ffffff;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-logo {
  padding: 22px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--accent-gradient);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 2px;
}

.sidebar-nav {
  padding: 8px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 16px;
  border-radius: 10px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  font-weight: 500;
}

.nav-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: all 0.2s;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item--active {
  background: #eef1fe;
  color: var(--accent-blue);
}

.nav-item--active .nav-icon {
  background: var(--accent-blue);
  color: #fff;
}

.sidebar-bottom {
  padding: 16px 12px;
  border-top: 1px solid var(--border-color);
}

.sidebar-help {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 10px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar-help:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
</style>
