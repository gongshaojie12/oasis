// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useTranslation } from 'react-i18next'
import { switchLang } from '@/lib/i18n'
import { Languages } from 'lucide-react'

export function I18nToggle() {
  const { i18n } = useTranslation()
  const cur: 'zh' | 'en' = i18n.language === 'en' ? 'en' : 'zh'
  return (
    <button
      type="button"
      className="wx-btn-ghost text-sm flex items-center gap-1 opacity-70 hover:opacity-100"
      onClick={() => switchLang(cur === 'zh' ? 'en' : 'zh')}
      title={cur === 'zh' ? 'Switch to English' : '切换到中文'}
      aria-label={cur === 'zh' ? 'Switch to English' : '切换到中文'}
    >
      <Languages size={14} />
      {cur === 'zh' ? 'EN' : '中'}
    </button>
  )
}
