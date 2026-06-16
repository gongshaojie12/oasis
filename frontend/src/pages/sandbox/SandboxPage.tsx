// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Sandbox detail page: 3-column layout (sidebar | chat | data panel).
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { useSandboxStore } from '@/stores/sandboxStore'
import { ChatBubble } from '@/components/chat/ChatBubble'
import { Composer } from '@/components/chat/Composer'
import { Sidebar } from '@/components/chat/Sidebar'
import { DataPanel } from '@/components/chat/DataPanel'
import { SandboxHeader } from '@/components/chat/SandboxHeader'
import { NewSandboxModal } from '@/components/chat/NewSandboxModal'
import type {
  ChatMessage,
  ChatSimulateResponse,
  Sandbox,
  Workspace,
} from '@/types/api'

export function SandboxPage() {
  const { t } = useTranslation()
  const { slug, sandboxId } = useParams<{ slug: string; sandboxId: string }>()
  const nav = useNavigate()

  const workspaces = useAuthStore((s) => s.workspaces)
  const workspace: Workspace | undefined = workspaces.find((w) => w.slug === slug)

  const sandboxes = useSandboxStore((s) => s.sandboxes)
  const setSandboxes = useSandboxStore((s) => s.setSandboxes)
  const currentSandbox = useSandboxStore((s) => s.currentSandbox)
  const setCurrentSandbox = useSandboxStore((s) => s.setCurrentSandbox)
  const messages = useSandboxStore((s) => s.messages)
  const setMessages = useSandboxStore((s) => s.setMessages)
  const appendMessages = useSandboxStore((s) => s.appendMessages)
  const isSending = useSandboxStore((s) => s.isSending)
  const setSending = useSandboxStore((s) => s.setSending)

  const [modalOpen, setModalOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  // Load sandbox list whenever workspace changes
  useEffect(() => {
    if (!slug) return
    let active = true
    api.get(`/workspaces/${slug}/sandboxes`)
      .then((r) => {
        if (!active) return
        const list: Sandbox[] = r.data.sandboxes ?? []
        setSandboxes(list)
      })
      .catch(() => toast.error(t('common.error')))
    return () => { active = false }
  }, [slug, setSandboxes, t])

  // Load sandbox + messages when sandboxId changes
  useEffect(() => {
    if (!slug || !sandboxId) return
    let active = true
    Promise.all([
      api.get(`/workspaces/${slug}/sandboxes/${sandboxId}`),
      api.get(`/workspaces/${slug}/sandboxes/${sandboxId}/messages`),
    ])
      .then(([sb, ms]) => {
        if (!active) return
        setCurrentSandbox(sb.data as Sandbox)
        setMessages((ms.data.messages ?? []) as ChatMessage[])
      })
      .catch((err) => {
        if (!active) return
        if (err?.response?.status === 404) {
          toast.error(t('sandbox.not_found'))
          nav(`/w/${slug}`)
        } else {
          toast.error(t('common.error'))
        }
      })
    return () => { active = false }
  }, [slug, sandboxId, setCurrentSandbox, setMessages, nav, t])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  const recentMessages = useMemo(() => messages, [messages])

  if (!workspace) {
    return (
      <div style={{ padding: 40, color: 'var(--wx-text-secondary)' }}>
        {t('workspaces.empty')}
      </div>
    )
  }

  async function handleSend(text: string) {
    if (!slug || !sandboxId) return
    setSending(true)
    try {
      const r = await api.post<ChatSimulateResponse>(
        `/workspaces/${slug}/sandboxes/${sandboxId}/chat`,
        { text },
      )
      const all: ChatMessage[] = [
        r.data.user_message,
        ...(r.data.assistant_messages ?? []),
      ]
      appendMessages(all)
      if (r.data.error) toast.error(r.data.error)
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? t('common.error')
      toast.error(detail)
    } finally {
      setSending(false)
    }
  }

  async function handleCreateSandbox(payload: {
    name: string; emoji: string; description: string
    population_size: number; distribution_path: string
  }) {
    if (!slug) return
    setCreating(true)
    try {
      const r = await api.post<Sandbox>(
        `/workspaces/${slug}/sandboxes`, payload)
      setSandboxes([r.data, ...sandboxes])
      setModalOpen(false)
      nav(`/w/${slug}/sandboxes/${r.data.sandbox_id}`)
    } catch {
      toast.error(t('common.error'))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="wx-app">
      <Sidebar
        workspaceSlug={slug ?? ''}
        sandboxes={sandboxes}
        activeSandboxId={sandboxId ?? null}
        onPickSandbox={(id) => nav(`/w/${slug}/sandboxes/${id}`)}
        onCreateSandbox={() => setModalOpen(true)}
      />
      <section className="wx-chat-col">
        {currentSandbox && (
          <SandboxHeader sandbox={currentSandbox} workspace={workspace} />
        )}
        <div ref={scrollRef} className="wx-msgs">
          <div className="wx-msg-wrap">
            {recentMessages.length === 0 && (
              <div style={{ textAlign: 'center', padding: '40px 20px',
                            color: 'var(--wx-text-tertiary)' }}>
                {t('sandbox.empty_hint')}
              </div>
            )}
            {recentMessages.map((m) => (
              <ChatBubble key={m.message_id} msg={m} />
            ))}
            {isSending && (
              <div style={{ color: 'var(--wx-text-tertiary)',
                            fontSize: 13, padding: '8px 0' }}>
                {t('chat.thinking')}…
              </div>
            )}
          </div>
        </div>
        <Composer onSend={handleSend} disabled={isSending} />
      </section>
      {currentSandbox && (
        <DataPanel sandbox={currentSandbox} messages={messages} />
      )}
      <NewSandboxModal
        isOpen={modalOpen}
        defaultDistribution={currentSandbox?.distribution_path}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreateSandbox}
        submitting={creating}
      />
    </div>
  )
}
