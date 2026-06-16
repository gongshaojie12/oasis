// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useTranslation } from 'react-i18next'
import { useBrandStore } from '@/stores/brandStore'

interface Props {
  size?: 'sm' | 'md' | 'lg'
}

export function BrandLogo({ size = 'md' }: Props) {
  const { brand } = useBrandStore()
  const { i18n } = useTranslation()
  const lang: 'zh' | 'en' = i18n.language === 'en' ? 'en' : 'zh'
  const avatar = brand?.avatar?.[lang] ?? (lang === 'en' ? 'W' : '象')
  const name = brand?.name?.[lang] ?? (lang === 'en' ? 'WANXIANG' : '万象')
  const tagline = brand?.tagline?.[lang] ?? ''
  const dims = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-10 h-10 text-base',
    lg: 'w-14 h-14 text-2xl',
  }[size]
  return (
    <div className="flex items-center gap-3">
      <div className={`wx-brand-avatar ${dims}`} aria-hidden="true">{avatar}</div>
      <div className="leading-tight">
        <div className="font-semibold text-base">{name}</div>
        {tagline && (
          <div className="text-xs" style={{ color: 'var(--wx-text-tertiary)' }}>{tagline}</div>
        )}
      </div>
    </div>
  )
}
