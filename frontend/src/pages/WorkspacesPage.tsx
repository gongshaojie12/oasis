// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'

export function WorkspacesPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const workspaces = useAuthStore((s) => s.workspaces)
  const setCurrentWorkspace = useAuthStore((s) => s.setCurrentWorkspace)

  function enter(slug: string) {
    setCurrentWorkspace(slug)
    nav(`/w/${slug}`)
  }

  return (
    <PageShell>
      <GlassCard>
        <div className="flex items-center justify-between mb-5">
          <h1 className="text-xl font-semibold">{t('workspaces.title')}</h1>
          <button type="button" className="wx-btn-ghost text-sm" disabled title="P6">
            {t('workspaces.create_new')}
          </button>
        </div>
        {workspaces.length === 0 ? (
          <p className="text-sm text-center py-8" style={{ color: 'var(--wx-text-tertiary)' }}>
            {t('workspaces.empty')}
          </p>
        ) : (
          <ul className="space-y-3">
            {workspaces.map((w) => (
              <li key={w.workspace_id}
                  className="flex items-center justify-between p-3 rounded"
                  style={{ background: 'rgba(0,0,0,0.22)', border: '1px solid var(--wx-glass-border)' }}>
                <div>
                  <div className="font-semibold">{w.name}</div>
                  <div className="text-xs" style={{ color: 'var(--wx-text-tertiary)' }}>
                    {w.type} · {t('workspaces.balance')}: {t('workspaces.units', { n: w.balance_cost_units })}
                  </div>
                </div>
                <button type="button" className="wx-btn-primary text-sm"
                  onClick={() => enter(w.slug)}>
                  {t('workspaces.enter')}
                </button>
              </li>
            ))}
          </ul>
        )}
      </GlassCard>
    </PageShell>
  )
}
