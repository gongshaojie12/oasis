// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// P9b: Anonymous-action gate modal. Shown when an unauthenticated visitor on
// LandingPage tries to interact with a gated control (composer send, run-real-sim).
// Login/register CTAs preserve any pending composer text via return_to.
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Lock, X } from 'lucide-react'

interface Props {
  open: boolean
  onClose: () => void
  pendingText?: string
}

export function AuthGateModal({ open, onClose, pendingText }: Props) {
  const { t } = useTranslation()
  const nav = useNavigate()
  if (!open) return null

  const returnTo = pendingText
    ? `/?pending=${encodeURIComponent(pendingText)}`
    : '/'

  // Persist pending text in localStorage so DashboardPage can surface it
  // after the login/register flow completes.
  function stashPending() {
    if (pendingText) {
      try {
        localStorage.setItem('wanxiang.pending_chat', pendingText)
      } catch { /* quota / private mode */ }
    }
  }
  function goLogin() {
    stashPending()
    nav(`/login?return_to=${encodeURIComponent(returnTo)}`)
  }
  function goRegister() {
    stashPending()
    nav(`/register?return_to=${encodeURIComponent(returnTo)}`)
  }

  return (
    <div
      className="fixed inset-0 z-[9999] grid place-items-center"
      style={{
        background: 'rgba(5,10,28,0.85)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
      }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="wx-gate-title"
    >
      <div
        className="wx-glass"
        style={{
          padding: '36px 32px',
          maxWidth: 420,
          width: '90%',
          textAlign: 'center',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label={t('common.cancel')}
          style={{
            position: 'absolute', top: 12, right: 12,
            background: 'transparent', border: 'none',
            color: 'var(--wx-text-tertiary)', cursor: 'pointer',
            padding: 4,
          }}
        >
          <X size={18} />
        </button>
        <div
          style={{
            display: 'grid', placeItems: 'center',
            width: 56, height: 56, margin: '0 auto 12px',
            borderRadius: 16,
            background: 'var(--wx-grad-blue)',
          }}
        >
          <Lock size={26} color="#fff" />
        </div>
        <h2 id="wx-gate-title"
            style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginBottom: 8 }}>
          {t('landing.gate_title')}
        </h2>
        <p style={{
          fontSize: 13.5,
          color: 'var(--wx-text-secondary)',
          marginBottom: 22,
          lineHeight: 1.55,
        }}>
          {t('landing.gate_subtitle')}
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button type="button" className="wx-btn-ghost" onClick={goLogin}>
            {t('auth.login')}
          </button>
          <button type="button" className="wx-btn-primary" onClick={goRegister}>
            {t('auth.register')}
          </button>
        </div>
        <button
          type="button"
          onClick={onClose}
          style={{
            marginTop: 16,
            background: 'transparent', border: 'none',
            color: 'var(--wx-text-tertiary)',
            fontSize: 12, cursor: 'pointer',
          }}
        >
          {t('landing.gate_later')}
        </button>
      </div>
    </div>
  )
}
