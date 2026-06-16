// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage center column: chat header + real message stream + composer.
// No hardcoded messages — empty state shows a welcome bubble (zh/en).
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send } from 'lucide-react'
import { useBrandStore } from '@/stores/brandStore'
import type { ChatMessage, Sandbox } from '@/types/api'

interface Props {
  authed: boolean
  activeSandbox: Sandbox | null
  messages: ChatMessage[]
  loading: boolean
  onSend: (text: string) => void
}

export function LandingChat(p: Props) {
  const { t, i18n } = useTranslation()
  const { brand } = useBrandStore()
  const lang: 'zh' | 'en' = i18n.language === 'en' ? 'en' : 'zh'
  const nav = useNavigate()
  const [text, setText] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [p.messages.length, p.loading])

  function handleSend(e?: React.FormEvent) {
    e?.preventDefault()
    const v = text.trim()
    if (!v || p.loading) return
    setText('')
    p.onSend(v)
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const avatar = brand?.avatar?.[lang] ?? (lang === 'en' ? 'W' : '象')
  const aiName = t('landing.ai_officer')

  return (
    <section className="wx-chat-col">
      <div className="wx-chat-top">
        <div className="wx-ct-ava" aria-hidden="true">{avatar}</div>
        <div className="wx-ct-name">
          <b>
            {aiName}
            <span className="wx-ct-badge">{t('landing.officer_online')}</span>
          </b>
          <small>
            {p.activeSandbox
              ? `${p.activeSandbox.emoji} ${p.activeSandbox.name}`
              : t('landing.no_active_sandbox')}
          </small>
        </div>
        <div style={{ flex: 1 }} />
        {p.authed && (
          <button
            type="button"
            className="wx-btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() => nav('/dashboard')}
          >
            {t('landing.go_dashboard')}
          </button>
        )}
      </div>

      <div className="wx-msgs" ref={scrollRef}>
        <div className="wx-msg-wrap">
          {p.messages.length === 0 ? (
            <div className="wx-msg">
              <div className="wx-m-av ai" aria-hidden="true">{avatar}</div>
              <div className="wx-m-body">
                <div className="wx-m-name">{aiName}</div>
                <div className="wx-m-text">
                  {p.authed
                    ? p.activeSandbox
                      ? t('landing.empty_chat_authed_sandbox')
                      : t('landing.empty_chat_authed_no_sandbox')
                    : t('landing.empty_chat_anon')}
                </div>
              </div>
            </div>
          ) : (
            p.messages.map((m) => (
              <div
                key={m.message_id}
                className={`wx-msg ${m.kind === 'error' ? 'wx-msg-error' : ''} ${m.kind === 'intent_parsed' ? 'wx-msg-intent' : ''}`}
              >
                <div
                  className={`wx-m-av ${m.role === 'user' ? 'u' : 'ai'}`}
                  aria-hidden="true"
                >
                  {m.role === 'user' ? t('landing.you_initial') : avatar}
                </div>
                <div className="wx-m-body">
                  <div className="wx-m-name">
                    {m.role === 'user' ? t('landing.you') : aiName}
                  </div>
                  {m.kind === 'report_card' ? (
                    <div className="wx-art-card">
                      <div className="wx-art-title">{t('landing.report_card_title')}</div>
                      <div className="wx-art-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  ) : (
                    <div className="wx-m-text">{m.content}</div>
                  )}
                </div>
              </div>
            ))
          )}
          {p.loading && (
            <div className="wx-msg">
              <div className="wx-m-av ai" aria-hidden="true">{avatar}</div>
              <div className="wx-m-body">
                <div
                  className="wx-m-text"
                  style={{ color: 'var(--wx-text-secondary)' }}
                >
                  {t('landing.thinking')}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <form className="wx-composer" onSubmit={handleSend}>
        <div className="wx-composer-inner">
          <textarea
            aria-label={t('landing.composer_placeholder')}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKey}
            placeholder={t('landing.composer_placeholder')}
            rows={2}
            disabled={p.loading}
          />
          <button
            type="submit"
            className="wx-composer-send"
            disabled={!text.trim() || p.loading}
            aria-label={t('chat.send')}
          >
            <Send size={16} />
          </button>
        </div>
        <div className="wx-composer-counter" style={{ textAlign: 'center' }}>
          {t('landing.composer_hint')}
        </div>
      </form>
    </section>
  )
}
