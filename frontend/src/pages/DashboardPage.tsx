// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Workspace home: lists sandboxes as cards + "new sandbox" CTA.
// URL: either /dashboard (uses currentWorkspaceSlug) or /w/:slug.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { clearTokens } from '@/lib/auth'
import { BrandLogo } from '@/components/BrandLogo'
import { GlassCard } from '@/components/GlassCard'
import { I18nToggle } from '@/components/I18nToggle'
import { NewSandboxModal } from '@/components/chat/NewSandboxModal'
import { useAuthStore } from '@/stores/authStore'
import { useSandboxStore } from '@/stores/sandboxStore'
import type { Sandbox } from '@/types/api'

export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const params = useParams<{ slug?: string }>()
  const user = useAuthStore((s) => s.user)
  const workspaces = useAuthStore((s) => s.workspaces)
  const currentSlug = useAuthStore((s) => s.currentWorkspaceSlug)
  const setCurrentWorkspace = useAuthStore((s) => s.setCurrentWorkspace)
  const logoutStore = useAuthStore((s) => s.logout)
  const sandboxes = useSandboxStore((s) => s.sandboxes)
  const setSandboxes = useSandboxStore((s) => s.setSandboxes)

  const [modalOpen, setModalOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)

  // P9: pick up any composer draft the user typed on chat.html before login.
  // chat.html stashes it in localStorage and redirects to /app/login → here.
  // Surface it as a toast so they see continuity (next iteration can route
  // straight to a sandbox composer prefill).
  useEffect(() => {
    const pending = localStorage.getItem('wanxiang.pending_chat')
    if (pending) {
      localStorage.removeItem('wanxiang.pending_chat')
      const preview = pending.length > 50 ? pending.slice(0, 50) + '…' : pending
      toast(
        i18n.language === 'en'
          ? `Restored your draft: ${preview}`
          : `已带回你的输入: ${preview}`,
        { icon: '💬', duration: 5000 },
      )
    }
  }, [i18n.language])

  // If route has explicit /w/:slug, pin it as current
  useEffect(() => {
    if (params.slug && params.slug !== currentSlug) {
      setCurrentWorkspace(params.slug)
    }
  }, [params.slug, currentSlug, setCurrentWorkspace])

  const activeSlug = params.slug ?? currentSlug
  const current = workspaces.find((w) => w.slug === activeSlug) ?? workspaces[0] ?? null

  // If user lands on /dashboard with no workspaces, route them to /workspaces
  useEffect(() => {
    if (!current && workspaces.length === 0) {
      // Try /me to refetch workspaces (P5 already populates on login)
      setLoading(false)
      return
    }
    if (current && !activeSlug) {
      setCurrentWorkspace(current.slug)
    }
  }, [current, activeSlug, workspaces, setCurrentWorkspace])

  useEffect(() => {
    if (!current) return
    let active = true
    setLoading(true)
    api.get(`/workspaces/${current.slug}/sandboxes`)
      .then((r) => {
        if (!active) return
        setSandboxes((r.data.sandboxes ?? []) as Sandbox[])
      })
      .catch(() => active && toast.error(t('common.error')))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [current, setSandboxes, t])

  async function logout() {
    try { await api.post('/auth/logout') } catch { /* stateless */ }
    clearTokens()
    logoutStore()
    nav('/login', { replace: true })
  }

  async function handleCreateSandbox(payload: {
    name: string; emoji: string; description: string
    population_size: number; distribution_path: string
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

  return (
    <div className="min-h-screen px-6 py-6">
      <header className="flex items-center justify-between mb-8">
        <BrandLogo size="md" />
        <div className="flex items-center gap-3">
          <I18nToggle />
          <button type="button" className="wx-btn-ghost text-sm"
                   onClick={() => nav('/workspaces')}>
            {t('dashboard.switch_workspace')}
          </button>
          <button type="button" className="wx-btn-ghost text-sm" onClick={logout}>
            {t('auth.logout')}
          </button>
        </div>
      </header>
      <main className="max-w-5xl mx-auto">
        {!current ? (
          <GlassCard>
            <p style={{ color: 'var(--wx-text-secondary)' }}>
              {t('workspaces.empty')}
            </p>
            <button
              type="button"
              className="wx-btn-primary text-sm mt-3"
              onClick={() => nav('/workspaces')}
            >
              {t('dashboard.switch_workspace')}
            </button>
          </GlassCard>
        ) : (
          <>
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
          </>
        )}
      </main>
      <NewSandboxModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreateSandbox}
        submitting={creating}
      />
    </div>
  )
}
