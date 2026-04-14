<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div class="guest-layout">
        <div class="guest-bg">
          <div class="grid-lines"></div>
        </div>
        <div class="guest-container">
          <div class="guest-logo">
            <Icon name="carbon:analytics" size="36" />
            <span>OASIS</span>
          </div>
          <p class="guest-tagline">AI 社交模拟平台</p>
          <slot />
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { NConfigProvider, NMessageProvider } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#3b82f6',
    primaryColorHover: '#60a5fa',
    primaryColorPressed: '#2563eb',
    bodyColor: '#0a0e1a',
    cardColor: '#1a1f36',
    borderColor: '#2a3158',
    textColorBase: '#e2e8f0',
    inputColor: '#111827',
    borderRadius: '8px',
  },
}
</script>

<style scoped>
.guest-layout {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.guest-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 60%);
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}

.guest-container {
  position: relative;
  z-index: 1;
  width: 400px;
  text-align: center;
}

.guest-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 32px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}

.guest-logo :deep(svg) {
  color: var(--accent-blue);
}

.guest-tagline {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 32px;
}
</style>
