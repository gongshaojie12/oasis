// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Bottom chat input. Matches chat.html .composer. Enter = send,
// Shift+Enter = newline, Cmd/Ctrl+Enter also sends.
import { useState, useRef, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
}

const MAX_CHARS = 2000

export function Composer({ onSend, disabled = false }: Props) {
  const { t } = useTranslation()
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement | null>(null)

  function autoresize() {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  function send() {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
    requestAnimationFrame(autoresize)
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    const cmdEnter = (e.metaKey || e.ctrlKey) && e.key === 'Enter'
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    } else if (cmdEnter) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="wx-composer">
      <div className="wx-composer-inner">
        <textarea
          ref={ref}
          value={value}
          rows={1}
          placeholder={t('chat.placeholder')}
          maxLength={MAX_CHARS}
          aria-label={t('chat.placeholder')}
          disabled={disabled}
          onKeyDown={handleKey}
          onChange={(e) => { setValue(e.target.value); autoresize() }}
        />
        <button
          type="button"
          className="wx-composer-send"
          aria-label={t('chat.send')}
          onClick={send}
          disabled={disabled || value.trim().length === 0}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2"
               strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2 11 13" />
            <path d="m22 2-7 20-4-9-9-4 20-7Z" />
          </svg>
        </button>
      </div>
      <div className="wx-composer-counter">
        {value.length}/{MAX_CHARS}
        {disabled && (
          <span style={{ marginLeft: 8, color: 'var(--wx-accent-cyan)' }}>
            · {t('chat.thinking')}
          </span>
        )}
      </div>
    </div>
  )
}
