// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  return (
    <PageShell>
      <GlassCard>
        <h1 className="text-xl font-semibold mb-2">{t('auth.forgot_password_title')}</h1>
        <p className="text-sm mb-6" style={{ color: 'var(--wx-text-secondary)' }}>
          {t('auth.forgot_password_hint')}
        </p>
        <Link to="/login" className="wx-btn-primary inline-block text-center w-full"
          style={{ textDecoration: 'none' }}>
          {t('common.back')}
        </Link>
      </GlassCard>
    </PageShell>
  )
}
