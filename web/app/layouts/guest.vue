<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div class="guest-layout">
        <div class="guest-left">
          <div class="guest-left-content">
            <div class="guest-brand">
              <div class="brand-icon">
                <Icon name="carbon:analytics" size="32" />
              </div>
              <h1>OASIS</h1>
            </div>
            <h2 class="guest-headline">AI 社交模拟平台</h2>
            <p class="guest-desc">为企业提供专业的社交媒体模拟与分析服务，<br>助力品牌营销决策与舆情管理</p>
            <div class="guest-features">
              <div class="feature-item">
                <Icon name="carbon:chart-line-smooth" size="20" />
                <span>多平台社交模拟</span>
              </div>
              <div class="feature-item">
                <Icon name="carbon:ai-results" size="20" />
                <span>AI 智能 Agent</span>
              </div>
              <div class="feature-item">
                <Icon name="carbon:dashboard" size="20" />
                <span>可视化分析报告</span>
              </div>
            </div>
          </div>
        </div>
        <div class="guest-right">
          <div class="guest-container">
            <slot />
          </div>
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import type { GlobalThemeOverrides } from 'naive-ui'
import { NConfigProvider, NMessageProvider } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#4f6ef7',
    primaryColorHover: '#6b85f9',
    primaryColorPressed: '#3a57d9',
    bodyColor: '#f5f7fa',
    cardColor: '#ffffff',
    borderColor: '#e8ecf1',
    textColorBase: '#1a2332',
    inputColor: '#ffffff',
    borderRadius: '8px',
  },
}
</script>

<style scoped>
.guest-layout {
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.guest-left {
  width: 45%;
  background: linear-gradient(135deg, #4f6ef7 0%, #7c5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  position: relative;
  overflow: hidden;
}

.guest-left::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(255,255,255,0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(255,255,255,0.06) 0%, transparent 50%);
}

.guest-left-content {
  position: relative;
  z-index: 1;
  color: #fff;
  max-width: 400px;
}

.guest-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.brand-icon {
  width: 48px;
  height: 48px;
  background: rgba(255,255,255,0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.guest-brand h1 {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 3px;
}

.guest-headline {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 12px;
  opacity: 0.95;
}

.guest-desc {
  font-size: 14px;
  line-height: 1.8;
  opacity: 0.8;
  margin-bottom: 32px;
}

.guest-features {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  opacity: 0.9;
}

.guest-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  padding: 48px;
}

.guest-container {
  width: 400px;
}
</style>
