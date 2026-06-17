// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage — ChatGPT-style single-page layout.
// Sidebar holds 7 nav items. Main area swaps content based on activeView
// state (no page navigation). Right data panel is only visible on chat view.
//
// Anonymous:
//   - sidebar shows the nav menu + 登录/注册 CTAs at the BOTTOM
//   - clicking any requires-auth nav item opens AuthGateModal
//   - chat view still works with the welcome bubble + composer (gated send)
// Authenticated:
//   - sidebar shows nav menu + (when chat view) sandbox list + user pill
//   - main area can switch to dashboard / reports / billing / members /
//     api_keys / settings without leaving the SPA
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAuthenticated } from '@/lib/auth'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { LandingSidebar, type ViewKey, type CreateSandboxPayload } from '@/components/landing/LandingSidebar'
import { LandingChat } from '@/components/landing/LandingChat'
import { LandingDataPanel } from '@/components/landing/LandingDataPanel'
import { AuthGateModal } from '@/components/landing/AuthGateModal'
import { DashboardView } from '@/views/DashboardView'
import { ReportsView } from '@/views/ReportsView'
import { BillingView } from '@/views/BillingView'
import { MembersView } from '@/views/MembersView'
import { ApiKeysView } from '@/views/ApiKeysView'
import { SettingsView } from '@/views/SettingsView'
import { useTranslation } from 'react-i18next'
import type { ChatMessage, Sandbox } from '@/types/api'

export function LandingPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const {
    user, workspaces, currentWorkspaceSlug,
    setUser, setWorkspaces, setCurrentWorkspace,
  } = useAuthStore()

  const [authed, setAuthed] = useState(false)
  const [sandboxes, setSandboxes] = useState<Sandbox[]>([])
  const [activeSandbox, setActiveSandbox] = useState<Sandbox | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [gateOpen, setGateOpen] = useState(false)
  const [gateTab, setGateTab] = useState<'login' | 'register'>('register')
  const [pendingText, setPendingText] = useState<string | undefined>(undefined)
  const [activeView, setActiveView] = useState<ViewKey>('chat')
  // Collapsible panels (default expanded). Persist user choice in localStorage.
  const [leftCollapsed, setLeftCollapsed] = useState<boolean>(
    () => localStorage.getItem('wanxiang.landing.left_collapsed') === '1',
  )
  const [rightCollapsed, setRightCollapsed] = useState<boolean>(
    () => localStorage.getItem('wanxiang.landing.right_collapsed') === '1',
  )
  function toggleLeft() {
    setLeftCollapsed((v) => {
      const nv = !v
      localStorage.setItem('wanxiang.landing.left_collapsed', nv ? '1' : '0')
      return nv
    })
  }
  function toggleRight() {
    setRightCollapsed((v) => {
      const nv = !v
      localStorage.setItem('wanxiang.landing.right_collapsed', nv ? '1' : '0')
      return nv
    })
  }

  const currentWs =
    workspaces.find((w) => w.slug === currentWorkspaceSlug) || workspaces[0]

  // Compute auth state on mount (avoid SSR/localStorage hydration mismatch).
  useEffect(() => { setAuthed(isAuthenticated()) }, [])

  // Re-hydrate pending text if user came back from login with ?pending=...
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const p = params.get('pending')
    if (p) setPendingText(p)
  }, [])

  // Bootstrap: fetch /me if logged in but user not yet loaded.
  useEffect(() => {
    if (!authed || user) return
    api.get('/me').then((r) => {
      setUser(r.data.user)
      setWorkspaces(r.data.workspaces || [])
      if (!currentWorkspaceSlug && r.data.workspaces?.[0]) {
        setCurrentWorkspace(r.data.workspaces[0].slug)
      }
    }).catch(() => { /* token may be stale; landing still renders */ })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed])

  // Load sandboxes for current workspace.
  useEffect(() => {
    if (!authed || !currentWs) { setSandboxes([]); return }
    api.get(`/workspaces/${currentWs.slug}/sandboxes`)
      .then((r) => {
        const list: Sandbox[] = r.data.sandboxes || []
        setSandboxes(list)
        setActiveSandbox((prev) => {
          if (prev && list.some((s) => s.sandbox_id === prev.sandbox_id)) {
            return prev
          }
          return list[0] || null
        })
      })
      .catch(() => setSandboxes([]))
  }, [authed, currentWs?.slug])

  // Load messages for active sandbox.
  useEffect(() => {
    if (!activeSandbox || !currentWs) { setMessages([]); return }
    api.get(
      `/workspaces/${currentWs.slug}/sandboxes/${activeSandbox.sandbox_id}/messages`,
    )
      .then((r) => setMessages(r.data.messages || []))
      .catch(() => setMessages([]))
  }, [activeSandbox?.sandbox_id, currentWs?.slug])

  function handleSelectView(view: ViewKey, requiresAuth: boolean) {
    if (requiresAuth && !authed) {
      setGateTab('register')
      setGateOpen(true)
      return
    }
    setActiveView(view)
  }

  async function handleSend(text: string) {
    if (!text.trim()) return
    if (!authed) {
      setPendingText(text)
      setGateTab('register')
      setGateOpen(true)
      return
    }
    if (!currentWs) {
      nav('/workspaces')
      return
    }
    setLoading(true)
    try {
      let sb = activeSandbox
      if (!sb) {
        const created = await api.post(`/workspaces/${currentWs.slug}/sandboxes`, {
          name: t('landing.default_sandbox_name'),
          emoji: '🔬',
          population_size: 50,
        })
        sb = created.data as Sandbox
        setActiveSandbox(sb)
        setSandboxes((prev) => [sb as Sandbox, ...prev])
      }
      const tempUserMsg: ChatMessage = {
        message_id: 'tmp-' + Date.now(),
        sandbox_id: sb.sandbox_id,
        role: 'user',
        content: text,
        kind: 'text',
        metadata: {},
        user_id: user?.user_id ?? null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, tempUserMsg])

      const r = await api.post(
        `/workspaces/${currentWs.slug}/sandboxes/${sb.sandbox_id}/chat`,
        { text, model: { provider: 'stub' } },
      )
      setMessages((prev) => {
        const without = prev.filter((m) => m.message_id !== tempUserMsg.message_id)
        return [
          ...without,
          r.data.user_message,
          ...((r.data.assistant_messages as ChatMessage[]) || []),
        ]
      })
    } catch (e: unknown) {
      // eslint-disable-next-line no-console
      console.error(e)
      let detail = String(e)
      if (typeof e === 'object' && e && 'response' in e) {
        const resp = (e as { response?: { data?: { detail?: string } } }).response
        if (resp?.data?.detail) detail = resp.data.detail
      }
      const errMsg: ChatMessage = {
        message_id: 'err-' + Date.now(),
        sandbox_id: activeSandbox?.sandbox_id || '',
        role: 'assistant',
        content: detail,
        kind: 'error',
        metadata: {},
        user_id: null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  async function createSandboxFromSidebar(payload: CreateSandboxPayload) {
    if (!authed || !currentWs) return
    const r = await api.post(`/workspaces/${currentWs.slug}/sandboxes`, payload)
    const created = r.data as Sandbox
    setSandboxes((prev) => [created, ...prev])
    setActiveSandbox(created)
  }

  // Right panel only renders on chat view → drop the 3rd grid column to give
  // the main area more room when a data-heavy view is active.
  const noPanel = activeView !== 'chat'
  const shellClass = [
    'wx-app',
    leftCollapsed ? 'left-c' : '',
    rightCollapsed ? 'right-c' : '',
    noPanel ? 'no-panel' : '',
  ].filter(Boolean).join(' ')

  function renderMain() {
    if (activeView === 'chat') {
      return (
        <LandingChat
          authed={authed}
          activeSandbox={activeSandbox}
          messages={messages}
          loading={loading}
          onSend={handleSend}
        />
      )
    }
    // All other views require auth + a workspace
    const slug = currentWs?.slug
    if (!slug) {
      return (
        <section className="wx-chat-col">
          <div style={{ padding: '28px 36px', color: 'var(--wx-text-secondary)' }}>
            {t('workspaces.empty')}
          </div>
        </section>
      )
    }
    let body: React.ReactNode = null
    switch (activeView) {
      case 'dashboard': body = <DashboardView slug={slug} />; break
      case 'reports':   body = <ReportsView   slug={slug} />; break
      case 'billing':   body = <BillingView   slug={slug} />; break
      case 'members':   body = <MembersView   slug={slug} />; break
      case 'api_keys':  body = <ApiKeysView   slug={slug} />; break
      case 'settings':  body = <SettingsView  slug={slug} />; break
    }
    return (
      <section className="wx-chat-col" style={{ overflowY: 'auto' }}>
        {body}
      </section>
    )
  }

  return (
    <>
      <div className={shellClass}>
        <LandingSidebar
          authed={authed}
          workspaces={workspaces}
          currentWs={currentWs}
          sandboxes={sandboxes}
          activeSandbox={activeSandbox}
          onSelectWorkspace={setCurrentWorkspace}
          onSelectSandbox={setActiveSandbox}
          onCreateSandbox={createSandboxFromSidebar}
          user={user}
          collapsed={leftCollapsed}
          onToggleCollapse={toggleLeft}
          onOpenAuth={(t) => { setGateTab(t); setGateOpen(true) }}
          activeView={activeView}
          onSelectView={handleSelectView}
        />
        {renderMain()}
        {!noPanel && (
          <LandingDataPanel
            authed={authed}
            activeSandbox={activeSandbox}
            messages={messages}
            collapsed={rightCollapsed}
            onToggleCollapse={toggleRight}
          />
        )}
      </div>

      <AuthGateModal
        open={gateOpen}
        onClose={() => setGateOpen(false)}
        initialTab={gateTab}
        onAuthed={() => {
          setAuthed(true)
        }}
        pendingText={pendingText}
      />
    </>
  )
}
