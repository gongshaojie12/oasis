// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Light/dark theme toggle button — mirrors I18nToggle styling so the chat
// header keeps a tight, ChatGPT-style cluster of utility buttons.
import { Moon, Sun } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useThemeStore } from '@/stores/themeStore'

export function ThemeToggle() {
  const { t } = useTranslation()
  const theme = useThemeStore((s) => s.theme)
  const toggle = useThemeStore((s) => s.toggle)
  const Icon = theme === 'light' ? Moon : Sun
  const label = theme === 'light'
    ? t('theme.switch_to_dark')
    : t('theme.switch_to_light')
  return (
    <button
      type="button"
      className="wx-btn-ghost text-sm flex items-center gap-1 opacity-70 hover:opacity-100"
      onClick={toggle}
      title={label}
      aria-label={label}
    >
      <Icon size={14} />
    </button>
  )
}
