<template>
  <NConfigProvider :theme-overrides="themeOverrides">
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
import type { GlobalThemeOverrides } from 'naive-ui'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { useAuthStore } from '~/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#4f6ef7',
    primaryColorHover: '#6b85f9',
    primaryColorPressed: '#3a57d9',
    bodyColor: '#f5f7fa',
    cardColor: '#ffffff',
    modalColor: '#ffffff',
    popoverColor: '#ffffff',
    borderColor: '#e8ecf1',
    textColorBase: '#1a2332',
    inputColor: '#ffffff',
    borderRadius: '8px',
  },
  Button: {
    borderRadiusMedium: '8px',
  },
  Card: {
    borderRadius: '12px',
    borderColor: '#e8ecf1',
  },
  Input: {
    borderRadius: '8px',
  },
  DataTable: {
    borderRadius: '12px',
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
  background: var(--bg-primary);
}

.app-content {
  flex: 1;
  padding: 28px 32px;
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
