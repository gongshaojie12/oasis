// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useTranslation } from 'react-i18next'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'

export function OnboardingPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const user = useAuthStore((s) => s.user)
  const workspaces = useAuthStore((s) => s.workspaces)
  const ws = workspaces[0]
  const wsName = ws?.name ?? t('onboarding.personal')
  return (
    <PageShell>
      <GlassCard>
        <h1 className="text-xl font-semibold mb-2">
          {t('onboarding.title', { name: user?.display_name ?? '' })}
        </h1>
        <p className="text-sm mb-6" style={{ color: 'var(--wx-text-secondary)' }}>
          {t('onboarding.subtitle', { ws: wsName })}
        </p>
        <button type="button" className="wx-btn-primary w-full mb-3"
          onClick={() => nav('/dashboard', { replace: true })}>
          {t('onboarding.enter_dashboard')}
        </button>
        <p className="text-xs text-center" style={{ color: 'var(--wx-text-tertiary)' }}>
          {t('onboarding.create_team_later')}{' '}
          <Link to="/workspaces" className="wx-link">{t('workspaces.title')}</Link>
        </p>
      </GlassCard>
    </PageShell>
  )
}
