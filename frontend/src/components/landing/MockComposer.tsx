// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage composer — the primary gated action. Anonymous users typing here
// and pressing Send (or Enter) get the AuthGateModal with their draft preserved.
// Authenticated users get redirected to /dashboard with pending_chat stashed.
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Send } from 'lucide-react'

interface Props {
  /** Called when the user tries to send. Parent decides whether to gate or proxy. */
  onTrySend: (text: string) => void
}

export function MockComposer({ onTrySend }: Props) {
  const { t } = useTranslation()
  const [text, setText] = useState('')

  function handleSend() {
    const v = text.trim()
    if (!v) return
    onTrySend(v)
  }

  return (
    <div className="wx-composer">
      <div className="wx-composer-inner">
        <textarea
          aria-label={t('landing.composer_placeholder')}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder={t('landing.composer_placeholder')}
          rows={2}
        />
        <button
          type="button"
          className="wx-composer-send"
          onClick={handleSend}
          disabled={!text.trim()}
          aria-label={t('chat.send')}
        >
          <Send size={16} />
        </button>
      </div>
      <div className="wx-composer-counter" style={{ textAlign: 'center' }}>
        {t('landing.composer_hint')}
      </div>
    </div>
  )
}
