// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Placeholder dashboard. P6 will replace this with the full sandbox + chat UI.
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { clearTokens } from '@/lib/auth'
import { api } from '@/lib/api'
import { GlassCard } from '@/components/GlassCard'
import { BrandLogo } from '@/components/BrandLogo'
import { I18nToggle } from '@/components/I18nToggle'

export function DashboardPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const user = useAuthStore((s) => s.user)
  const workspaces = useAuthStore((s) => s.workspaces)
  const currentSlug = useAuthStore((s) => s.currentWorkspaceSlug)
  const logoutStore = useAuthStore((s) => s.logout)
  const current = workspaces.find((w) => w.slug === currentSlug) ?? workspaces[0] ?? null

  async function logout() {
    try { await api.post('/auth/logout') } catch { /* stateless */ }
    clearTokens()
    logoutStore()
    nav('/login', { replace: true })
  }

  return (
    <div className="min-h-screen px-6 py-6">
      <header className="flex items-center justify-between mb-8">
        <BrandLogo size="md" />
        <div className="flex items-center gap-3">
          <I18nToggle />
          <button type="button" className="wx-btn-ghost text-sm" onClick={logout}>
            {t('auth.logout')}
          </button>
        </div>
      </header>
      <main className="max-w-4xl mx-auto">
        <GlassCard>
          <h1 className="text-2xl font-semibold mb-1">
            {t('dashboard.hello', { name: user?.display_name ?? '' })}
          </h1>
          <p className="text-sm mb-6" style={{ color: 'var(--wx-text-secondary)' }}>
            {t('dashboard.placeholder')}
          </p>
          {current && (
            <div className="p-4 rounded mb-4"
                 style={{ background: 'rgba(0,0,0,0.22)', border: '1px solid var(--wx-glass-border)' }}>
              <div className="text-xs uppercase tracking-wide mb-1"
                   style={{ color: 'var(--wx-text-tertiary)' }}>
                {t('dashboard.current_workspace')}
              </div>
              <div className="font-semibold">{current.name}</div>
              <div className="text-sm" style={{ color: 'var(--wx-text-secondary)' }}>
                {current.type} · {t('workspaces.balance')}: {t('workspaces.units', { n: current.balance_cost_units })}
              </div>
            </div>
          )}
          <button type="button" className="wx-btn-ghost text-sm"
            onClick={() => nav('/workspaces')}>
            {t('dashboard.switch_workspace')}
          </button>
        </GlassCard>
      </main>
    </div>
  )
}
