// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Reusable workspace dashboard view — sandbox list + create CTA. NO outer
// header chrome (logo / logout / lang toggle), since the host (WorkspaceLayout
// or LandingSidebar) already owns that. Used by /w/:slug route (via the
// thin DashboardPage wrapper) AND by LandingPage when activeView==='dashboard'.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { GlassCard } from '@/components/GlassCard'
import { NewSandboxModal } from '@/components/chat/NewSandboxModal'
import { useAuthStore } from '@/stores/authStore'
import { useSandboxStore } from '@/stores/sandboxStore'
import type { Sandbox } from '@/types/api'

interface Props {
  slug: string
}

export function DashboardView({ slug }: Props) {
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const user = useAuthStore((s) => s.user)
  const workspaces = useAuthStore((s) => s.workspaces)
  const sandboxes = useSandboxStore((s) => s.sandboxes)
  const setSandboxes = useSandboxStore((s) => s.setSandboxes)

  const [modalOpen, setModalOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)

  const current = workspaces.find((w) => w.slug === slug) ?? null

  useEffect(() => {
    if (!current) return
    let active = true
    setLoading(true)
    api
      .get(`/workspaces/${current.slug}/sandboxes`)
      .then((r) => {
        if (!active) return
        setSandboxes((r.data.sandboxes ?? []) as Sandbox[])
      })
      .catch(() => active && toast.error(t('common.error')))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [current, setSandboxes, t])

  async function handleCreateSandbox(payload: {
    name: string
    emoji: string
    description: string
    population_size: number
    distribution_path: string
  }) {
    if (!current) return
    setCreating(true)
    try {
      const r = await api.post<Sandbox>(
        `/workspaces/${current.slug}/sandboxes`, payload)
      setSandboxes([r.data, ...sandboxes])
      setModalOpen(false)
      nav(`/w/${current.slug}/sandboxes/${r.data.sandbox_id}`)
    } catch {
      toast.error(t('common.error'))
    } finally {
      setCreating(false)
    }
  }

  function fmtDate(iso: string): string {
    try {
      return new Date(iso).toLocaleDateString(
        i18n.language === 'en' ? 'en-US' : 'zh-CN')
    } catch { return iso }
  }

  if (!current) {
    return (
      <div style={{ padding: '28px 36px' }}>
        <GlassCard>
          <p style={{ color: 'var(--wx-text-secondary)' }}>
            {t('workspaces.empty')}
          </p>
        </GlassCard>
      </div>
    )
  }

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="mb-6 flex items-end justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-wider"
               style={{ color: 'var(--wx-text-tertiary)' }}>
            {t('dashboard.current_workspace')}
          </div>
          <h1 className="text-2xl font-semibold">
            {t('dashboard.hello', { name: user?.display_name ?? '' })}
          </h1>
          <div className="text-sm"
               style={{ color: 'var(--wx-text-secondary)' }}>
            {current.name} · {t('workspaces.balance')}:{' '}
            {t('workspaces.units', { n: current.balance_cost_units })}
          </div>
        </div>
        <button
          type="button"
          className="wx-btn-primary"
          onClick={() => setModalOpen(true)}
        >
          + {t('sandbox.new')}
        </button>
      </div>

      {loading ? (
        <GlassCard>
          <p style={{ color: 'var(--wx-text-tertiary)' }}>
            {t('common.loading')}
          </p>
        </GlassCard>
      ) : sandboxes.length === 0 ? (
        <GlassCard>
          <p style={{ color: 'var(--wx-text-secondary)' }}>
            {t('sandbox.empty')}
          </p>
          <p className="text-sm mt-2"
             style={{ color: 'var(--wx-text-tertiary)' }}>
            {t('sandbox.empty_hint')}
          </p>
        </GlassCard>
      ) : (
        <div className="grid gap-4"
             style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>
          {sandboxes.map((s) => (
            <button
              key={s.sandbox_id}
              type="button"
              className="wx-glass text-left p-4 cursor-pointer"
              style={{ display: 'block', color: 'inherit',
                       transition: 'transform .15s' }}
              onClick={() => nav(`/w/${current.slug}/sandboxes/${s.sandbox_id}`)}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="wx-sb-emoji" style={{ width: 36, height: 36, fontSize: 18 }}>
                  {s.emoji}
                </span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="font-semibold truncate">{s.name}</div>
                  <div className="text-xs"
                       style={{ color: 'var(--wx-text-tertiary)' }}>
                    {fmtDate(s.last_active_at)}
                  </div>
                </div>
              </div>
              {s.description && (
                <p className="text-sm" style={{ color: 'var(--wx-text-secondary)' }}>
                  {s.description}
                </p>
              )}
              <div className="text-xs mt-3"
                   style={{ color: 'var(--wx-text-tertiary)' }}>
                {t('sandbox.population')}: {s.population_size.toLocaleString()}
              </div>
            </button>
          ))}
        </div>
      )}

      <NewSandboxModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreateSandbox}
        submitting={creating}
      />
    </div>
  )
}
