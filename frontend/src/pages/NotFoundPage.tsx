// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'

export function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <PageShell>
      <GlassCard className="text-center">
        <div className="text-5xl font-bold mb-3 disp" style={{ color: 'var(--wx-accent-cyan)' }}>404</div>
        <h1 className="text-xl font-semibold mb-2">{t('error.404_title')}</h1>
        <p className="text-sm mb-6" style={{ color: 'var(--wx-text-secondary)' }}>
          {t('error.404_subtitle')}
        </p>
        <Link to="/" className="wx-btn-primary inline-block" style={{ textDecoration: 'none' }}>
          {t('error.go_home')}
        </Link>
      </GlassCard>
    </PageShell>
  )
}
