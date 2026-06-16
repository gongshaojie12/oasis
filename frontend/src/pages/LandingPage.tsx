// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// P9c: LandingPage — anonymous-accessible home, but with ZERO mock data.
// - Anonymous: sidebar shows register/login CTAs, chat shows a welcome bubble,
//   data panel is a placeholder. Composer send → AuthGateModal.
// - Authenticated: sidebar fetches real workspaces + sandboxes; chat fetches
//   real messages; composer hits POST /v1/.../chat (auto-creates a default
//   sandbox on first send if none exists).
// 3-column chat.html visual layout preserved.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { I18nToggle } from '@/components/I18nToggle'
import { isAuthenticated } from '@/lib/auth'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { LandingSidebar } from '@/components/landing/LandingSidebar'
import { LandingChat } from '@/components/landing/LandingChat'
import { LandingDataPanel } from '@/components/landing/LandingDataPanel'
import { AuthGateModal } from '@/components/landing/AuthGateModal'
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
  const [pendingText, setPendingText] = useState<string | undefined>(undefined)

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
        // Auto-select first sandbox if none active or active belongs to old ws.
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

  async function handleSend(text: string) {
    if (!text.trim()) return
    if (!authed) {
      setPendingText(text)
      setGateOpen(true)
      return
    }
    if (!currentWs) {
      // Shouldn't normally happen; /me must have given at least the personal ws.
      nav('/workspaces')
      return
    }
    setLoading(true)
    try {
      // If no sandbox yet, create a default one.
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
      // Optimistic user message.
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

  async function createSandboxFromSidebar(name: string) {
    if (!authed || !currentWs) return
    const r = await api.post(`/workspaces/${currentWs.slug}/sandboxes`, {
      name,
      emoji: '🥤',
      population_size: 50,
    })
    const created = r.data as Sandbox
    setSandboxes((prev) => [created, ...prev])
    setActiveSandbox(created)
  }

  return (
    <>
      <div className="wx-app">
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
        />
        <LandingChat
          authed={authed}
          activeSandbox={activeSandbox}
          messages={messages}
          loading={loading}
          onSend={handleSend}
        />
        <LandingDataPanel
          authed={authed}
          activeSandbox={activeSandbox}
          messages={messages}
        />
      </div>

      <div
        style={{
          position: 'fixed', top: 14, right: 18, zIndex: 200,
          display: 'flex', alignItems: 'center', gap: 8,
        }}
      >
        <I18nToggle />
      </div>

      <AuthGateModal
        open={gateOpen}
        onClose={() => setGateOpen(false)}
        pendingText={pendingText}
      />
    </>
  )
}
