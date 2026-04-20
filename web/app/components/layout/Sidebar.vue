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
        <span>{{ $t(item.labelKey) }}</span>
      </NuxtLink>
    </nav>

    <div class="sidebar-bottom">
      <div class="sidebar-help">
        <Icon name="carbon:help" size="16" />
        <span>{{ $t('common.helpCenter') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const menuItems = [
  { path: '/dashboard', icon: 'carbon:dashboard', labelKey: 'nav.dashboard' },
  { path: '/simulations', icon: 'carbon:play-outline', labelKey: 'nav.simulations' },
  { path: '/genomes', icon: 'carbon:dna', labelKey: 'nav.genomeList' },
  { path: '/genomes/create', icon: 'carbon:add', labelKey: 'nav.genomeCreate' },
  { path: '/genomes/breed', icon: 'carbon:network-4', labelKey: 'nav.genomeBreed' },
  { path: '/analysis', icon: 'carbon:data-vis-4', labelKey: 'nav.analysis' },
  { path: '/world-builder', icon: 'carbon:network-3-reference', labelKey: 'nav.worldBuilder' },
  { path: '/reports', icon: 'carbon:report', labelKey: 'nav.reports' },
  { path: '/templates', icon: 'carbon:template', labelKey: 'nav.templates' },
  { path: '/settings', icon: 'carbon:settings', labelKey: 'nav.settings' },
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
