<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div class="app-layout">
        <LayoutSidebar />
        <div class="app-main">
          <LayoutHeader
            :enterprise-name="authStore.enterprise?.name || ''"
            :user-name="authStore.user?.name || ''"
            :quota="authStore.enterprise?.simQuota ?? null"
            @logout="handleLogout"
          />
          <main class="app-content">
            <slot />
          </main>
          <footer class="app-footer">
            <span>{{ authStore.enterprise?.planType || 'basic' }} 版</span>
            <span>·</span>
            <span>剩余 {{ authStore.enterprise?.simQuota ?? 0 }} 次模拟</span>
          </footer>
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { useAuthStore } from '~/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#3b82f6',
    primaryColorHover: '#60a5fa',
    primaryColorPressed: '#2563eb',
    bodyColor: '#0a0e1a',
    cardColor: '#1a1f36',
    modalColor: '#1a1f36',
    popoverColor: '#1a1f36',
    borderColor: '#2a3158',
    textColorBase: '#e2e8f0',
    inputColor: '#111827',
    borderRadius: '8px',
  },
  Button: {
    borderRadiusMedium: '8px',
  },
  Card: {
    borderRadius: '12px',
    borderColor: '#2a3158',
  },
  Input: {
    borderRadius: '8px',
  },
}

async function handleLogout() {
  authStore.logout()
  await router.push('/login')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.app-footer {
  height: 36px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
}
</style>
