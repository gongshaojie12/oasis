<template>
  <div class="stat-card">
    <div class="stat-icon" :style="{ background: iconBgColor }">
      <Icon :name="icon" size="22" :style="{ color: iconColor }" />
    </div>
    <div class="stat-info">
      <span class="stat-label">{{ label }}</span>
      <span class="stat-value">{{ value }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  icon: string
  label: string
  value: string | number
  iconBg?: string
}>()

const colorMap: Record<string, { bg: string; fg: string }> = {
  'rgba(59, 130, 246, 0.15)': { bg: '#eef1fe', fg: '#4f6ef7' },
  'rgba(59,130,246,0.15)': { bg: '#eef1fe', fg: '#4f6ef7' },
  'rgba(34, 197, 94, 0.15)': { bg: '#ecfdf5', fg: '#22c55e' },
  'rgba(139, 92, 246, 0.15)': { bg: '#f3f0ff', fg: '#8b5cf6' },
  'rgba(139,92,246,0.15)': { bg: '#f3f0ff', fg: '#8b5cf6' },
  'rgba(245, 158, 11, 0.15)': { bg: '#fff8eb', fg: '#f59e0b' },
  'rgba(245,158,11,0.15)': { bg: '#fff8eb', fg: '#f59e0b' },
}

const iconBgColor = computed(() => {
  if (props.iconBg && colorMap[props.iconBg]) return colorMap[props.iconBg].bg
  return '#eef1fe'
})

const iconColor = computed(() => {
  if (props.iconBg && colorMap[props.iconBg]) return colorMap[props.iconBg].fg
  return '#4f6ef7'
})
</script>

<style scoped>
.stat-card {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s, transform 0.2s;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
}
</style>
