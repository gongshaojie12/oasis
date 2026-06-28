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
import toast from 'react-hot-toast'
import { isAuthenticated } from '@/lib/auth'
import { api } from '@/lib/api'
import { streamSse } from '@/lib/sse'
import { useAuthStore } from '@/stores/authStore'
import { useSandboxStore } from '@/stores/sandboxStore'
import { LandingSidebar, type ViewKey } from '@/components/landing/LandingSidebar'
import { LandingChat } from '@/components/landing/LandingChat'
import { LandingDataPanel } from '@/components/landing/LandingDataPanel'
import { CockpitOverlay } from '@/components/chat/CockpitOverlay'
import { AuthGateModal } from '@/components/landing/AuthGateModal'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import { DashboardView } from '@/views/DashboardView'
import { ReportsView } from '@/views/ReportsView'
import { BillingView } from '@/views/BillingView'
import { MembersView } from '@/views/MembersView'
import { ApiKeysView } from '@/views/ApiKeysView'
import { SettingsView } from '@/views/SettingsView'
import { useTranslation } from 'react-i18next'
import type { ChatMessage, Sandbox, SandboxGroup, SimProgress } from '@/types/api'

export function LandingPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const {
    user, workspaces, currentWorkspaceSlug,
    setUser, setWorkspaces, setCurrentWorkspace,
  } = useAuthStore()

  const [authed, setAuthed] = useState(false)
  const [sandboxes, setSandboxes] = useState<Sandbox[]>([])
  const [groups, setGroups] = useState<SandboxGroup[]>([])
  const [activeSandbox, setActiveSandbox] = useState<Sandbox | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [liveProgress, setLiveProgress] = useState<SimProgress | null>(null)
  const [cockpitOpen, setCockpitOpen] = useState(false)
  // feed 统一走 store,供 CockpitOverlay 跨页读取;liveProgress 仍按页 local。
  const pushFeedItem = useSandboxStore((s) => s.pushFeedItem)
  const clearFeed = useSandboxStore((s) => s.clearFeed)
  const [gateOpen, setGateOpen] = useState(false)
  const [gateTab, setGateTab] = useState<'login' | 'register'>('register')
  const [pendingDelete, setPendingDelete] = useState<Sandbox | null>(null)
  const [deleting, setDeleting] = useState(false)
  // 上传文档:提炼后的素材 + 文件名 + 解析中状态
  const [attachMaterial, setAttachMaterial] = useState<string | null>(null)
  const [attachName, setAttachName] = useState<string | null>(null)
  const [attaching, setAttaching] = useState(false)
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

  // Load sandboxes + groups for current workspace.
  useEffect(() => {
    if (!authed || !currentWs) { setSandboxes([]); setGroups([]); return }
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
    api.get(`/workspaces/${currentWs.slug}/sandboxes/groups`)
      .then((r) => setGroups(r.data.groups || []))
      .catch(() => setGroups([]))
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

  // 「+ 新对话」: 清空进入空白聊天态。不立即建任务——用户发首条消息时
  // handleSend 会兜底自动建任务（人群规模可在对话里指定）。
  function handleNewChat() {
    if (!authed) {
      setGateTab('register')
      setGateOpen(true)
      return
    }
    setActiveSandbox(null)
    setMessages([])
    setActiveView('chat')
  }

  // 选历史对话：切任务 + 切回聊天视图（message 加载副作用会拉历史）
  function handlePickSandbox(sb: Sandbox) {
    setActiveSandbox(sb)
    setActiveView('chat')
  }

  // 确保有一个 sandbox 可用(上传/聊天都需要),没有则自动建。
  async function ensureSandbox(): Promise<Sandbox | null> {
    if (!currentWs) return null
    if (activeSandbox) return activeSandbox
    const created = await api.post(
      `/workspaces/${currentWs.slug}/sandboxes`,
      { name: t('landing.default_sandbox_name'), emoji: '🔬',
        population_size: 50 })
    const sb = created.data as Sandbox
    setActiveSandbox(sb)
    setSandboxes((prev) => [sb, ...prev])
    return sb
  }

  async function handleAttach(file: File) {
    if (!authed) { setGateTab('register'); setGateOpen(true); return }
    if (!currentWs) { nav('/workspaces'); return }
    setAttaching(true)
    setAttachName(file.name)
    try {
      const sb = await ensureSandbox()
      if (!sb) return
      const form = new FormData()
      form.append('file', file)
      const r = await api.post(
        `/workspaces/${currentWs.slug}/sandboxes/${sb.sandbox_id}/documents`,
        form)
      setAttachMaterial(r.data.material as string)
      toast.success(t('chat.attach_done'))
    } catch (e: unknown) {
      let detail = t('chat.attach_failed')
      if (typeof e === 'object' && e && 'response' in e) {
        const d = (e as { response?: { data?: { detail?: string } } })
          .response?.data?.detail
        if (d) detail = d
      }
      toast.error(detail)
      setAttachName(null)
      setAttachMaterial(null)
    } finally {
      setAttaching(false)
    }
  }

  function clearAttach() {
    setAttachName(null)
    setAttachMaterial(null)
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

      const body: { text: string; document_context?: string } = { text }
      if (attachMaterial) body.document_context = attachMaterial
      const r = await api.post(
        `/workspaces/${currentWs.slug}/sandboxes/${sb.sandbox_id}/chat/stream`,
        body,
      )
      clearAttach()
      setMessages((prev) => {
        const without = prev.filter((m) => m.message_id !== tempUserMsg.message_id)
        return [
          ...without,
          r.data.user_message,
          ...((r.data.assistant_messages as ChatMessage[]) || []),
        ]
      })

      if (r.data.streaming && r.data.run_id) {
        const total = (r.data.n as number) ?? sb.population_size
        // 用户在对话里指定了人数 → 后端已更新任务规模；前端同步本地状态，
        // 让右侧「样本规模」面板和左侧列表显示一致。
        if (typeof r.data.n === 'number' && r.data.n !== sb.population_size) {
          const newN = r.data.n as number
          const sbId2 = sb.sandbox_id
          setActiveSandbox((prev) =>
            prev && prev.sandbox_id === sbId2
              ? { ...prev, population_size: newN } : prev)
          setSandboxes((prev) => prev.map((s) =>
            s.sandbox_id === sbId2 ? { ...s, population_size: newN } : s))
        }
        clearFeed()
        setLiveProgress({ done: 0, total, status: 'running',
                          kind: r.data.kind })
        const sbId = sb.sandbox_id
        await streamSse(
          `/workspaces/${currentWs.slug}/sandboxes/${sbId}/runs/${r.data.run_id}/events`,
          {
            onEvent: (event, data) => {
              const d = (data ?? {}) as Record<string, unknown>
              if (event === 'progress') {
                setLiveProgress({
                  done: Number(d.done ?? 0),
                  total: Number(d.total ?? total),
                  mean: d.mean as number | null | undefined,
                  kind: d.kind as string | undefined,
                  status: 'running',
                })
                const feed = d.feed as Record<string, unknown> | undefined
                if (feed) {
                  pushFeedItem({
                    agent_id: Number(feed.agent_id ?? 0),
                    name: feed.name as string | undefined,
                    city: feed.city as string | null | undefined,
                    gender: feed.gender as string | null | undefined,
                    age: feed.age as string | null | undefined,
                    kind: String(feed.kind ?? ''),
                    value: (feed.value ?? null) as number | string | null,
                    error: feed.error as string | null | undefined,
                  })
                }
              } else if (event === 'done') {
                const card = d.report_card as ChatMessage | undefined
                if (card) setMessages((prev) => [...prev, card])
                setLiveProgress(null)
              } else if (event === 'error') {
                setLiveProgress(null)
                const em: ChatMessage = {
                  message_id: 'err-' + Date.now(),
                  sandbox_id: sbId, role: 'assistant',
                  content: String(d.error ?? 'error'), kind: 'error',
                  metadata: {}, user_id: null,
                  created_at: new Date().toISOString(),
                }
                setMessages((prev) => [...prev, em])
              }
            },
            onError: () => setLiveProgress(null),
          },
        )
      }
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

  async function handleConfirmDelete() {
    if (!currentWs || !pendingDelete) return
    const target = pendingDelete
    setDeleting(true)
    try {
      await api.delete(
        `/workspaces/${currentWs.slug}/sandboxes/${target.sandbox_id}`)
      setSandboxes((prev) => {
        const remaining = prev.filter(
          (s) => s.sandbox_id !== target.sandbox_id)
        // 删的是当前激活沙盒 → 切到剩余第一个或清空
        if (activeSandbox?.sandbox_id === target.sandbox_id) {
          setActiveSandbox(remaining[0] ?? null)
        }
        return remaining
      })
      toast.success(t('sandbox.deleted'))
      setPendingDelete(null)
    } catch {
      toast.error(t('common.error'))
    } finally {
      setDeleting(false)
    }
  }

  // ---- 分组管理 ----
  async function handleCreateGroup(name: string) {
    if (!currentWs) return
    try {
      const r = await api.post(
        `/workspaces/${currentWs.slug}/sandboxes/groups`, { name })
      setGroups((prev) => [...prev, r.data as SandboxGroup])
    } catch {
      toast.error(t('common.error'))
    }
  }

  async function handleRenameGroup(group: SandboxGroup, name: string) {
    if (!currentWs) return
    try {
      await api.patch(
        `/workspaces/${currentWs.slug}/sandboxes/groups/${group.group_id}`,
        { name })
      setGroups((prev) => prev.map((g) =>
        g.group_id === group.group_id ? { ...g, name } : g))
    } catch {
      toast.error(t('common.error'))
    }
  }

  async function handleDeleteGroup(group: SandboxGroup) {
    if (!currentWs) return
    try {
      await api.delete(
        `/workspaces/${currentWs.slug}/sandboxes/groups/${group.group_id}`)
      setGroups((prev) => prev.filter((g) => g.group_id !== group.group_id))
      // 其下任务解绑(后端已置 null),本地同步
      setSandboxes((prev) => prev.map((s) =>
        s.group_id === group.group_id ? { ...s, group_id: null } : s))
      toast.success(t('sandbox.group_deleted'))
    } catch {
      toast.error(t('common.error'))
    }
  }

  async function handleMoveSandbox(sb: Sandbox, groupId: string | null) {
    if (!currentWs) return
    try {
      await api.patch(
        `/workspaces/${currentWs.slug}/sandboxes/${sb.sandbox_id}`,
        { group_id: groupId })
      setSandboxes((prev) => prev.map((s) =>
        s.sandbox_id === sb.sandbox_id ? { ...s, group_id: groupId } : s))
    } catch {
      toast.error(t('common.error'))
    }
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
          onAttach={handleAttach}
          attachName={attachName}
          attaching={attaching}
          onRemoveAttach={clearAttach}
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
          groups={groups}
          activeSandbox={activeSandbox}
          onSelectWorkspace={setCurrentWorkspace}
          onSelectSandbox={handlePickSandbox}
          onDeleteSandbox={(s) => setPendingDelete(s)}
          onNewChat={handleNewChat}
          onCreateGroup={handleCreateGroup}
          onRenameGroup={handleRenameGroup}
          onDeleteGroup={handleDeleteGroup}
          onMoveSandbox={handleMoveSandbox}
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
            liveProgress={liveProgress}
            collapsed={rightCollapsed}
            onToggleCollapse={toggleRight}
            onExpandCockpit={() => setCockpitOpen(true)}
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
      <CockpitOverlay open={cockpitOpen}
                      onClose={() => setCockpitOpen(false)}
                      liveProgress={liveProgress} />
      <ConfirmDialog
        isOpen={pendingDelete !== null}
        title={t('sandbox.delete')}
        message={t('sandbox.delete_confirm',
                   { name: pendingDelete?.name ?? '' })}
        destructive
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  )
}
