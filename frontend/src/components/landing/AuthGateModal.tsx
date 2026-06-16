// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Inline auth modal (ChatGPT-style): tabs for 登录 / 注册, full forms inside.
// Replaces the previous "click button to navigate to /login or /register" flow.
// On success: close modal, hydrate auth store, replay any pending action.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Lock, X } from 'lucide-react'
import toast from 'react-hot-toast'

import { api } from '@/lib/api'
import { setTokens } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'

interface Props {
  open: boolean
  onClose: () => void
  pendingText?: string
  /** "register" or "login" — pre-select tab when opening. */
  initialTab?: 'login' | 'register'
  /** Called after successful auth, before modal closes. Useful for re-running
   *  the gated action. Receives the saved pending text (if any). */
  onAuthed?: (pendingText: string | undefined) => void
}

type Tab = 'login' | 'register'
type RegisterChannel = 'email' | 'phone'

export function AuthGateModal({
  open, onClose, pendingText, initialTab = 'register', onAuthed,
}: Props) {
  const { t, i18n } = useTranslation()
  const { setUser, setWorkspaces, setCurrentWorkspace } = useAuthStore()
  const [tab, setTab] = useState<Tab>(initialTab)
  const [submitting, setSubmitting] = useState(false)
  // Login form
  const [loginIdentifier, setLoginIdentifier] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  // Register form
  const [regChannel, setRegChannel] = useState<RegisterChannel>('email')
  const [regEmail, setRegEmail] = useState('')
  const [regPhone, setRegPhone] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regName, setRegName] = useState('')

  // Reset to initial tab whenever modal re-opens
  useEffect(() => {
    if (open) setTab(initialTab)
  }, [open, initialTab])

  if (!open) return null

  function close() {
    onClose()
  }

  async function applyAuthSuccess(data: {
    access_token: string
    refresh_token: string
    user: unknown
    workspaces?: unknown[]
    default_workspace?: unknown
  }) {
    setTokens({ access: data.access_token, refresh: data.refresh_token })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setUser(data.user as any)
    const wss = data.workspaces
      ?? (data.default_workspace ? [data.default_workspace] : [])
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setWorkspaces(wss as any)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (wss[0]) setCurrentWorkspace((wss[0] as any).slug)
    // Stash pending so DashboardPage / parent can pick it up
    if (pendingText) {
      try { localStorage.setItem('wanxiang.pending_chat', pendingText) }
      catch { /* quota / private mode */ }
    }
    toast.success(t(tab === 'login' ? 'auth.login_ok' : 'auth.register_ok'))
    onAuthed?.(pendingText)
    onClose()
  }

  async function submitLogin(e: React.FormEvent) {
    e.preventDefault()
    if (!loginIdentifier.trim() || !loginPassword) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    setSubmitting(true)
    try {
      const r = await api.post('/auth/login', {
        identifier: loginIdentifier.trim(),
        password: loginPassword,
      })
      await applyAuthSuccess(r.data)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(detail || t('auth.invalid_credentials'))
    } finally {
      setSubmitting(false)
    }
  }

  async function submitRegister(e: React.FormEvent) {
    e.preventDefault()
    if (!regName.trim() || !regPassword) {
      toast.error(t('auth.required_missing'))
      return
    }
    if (regChannel === 'email' && !regEmail.trim()) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    if (regChannel === 'phone' && !regPhone.trim()) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    setSubmitting(true)
    try {
      const payload: Record<string, unknown> = {
        password: regPassword,
        display_name: regName.trim(),
        locale: i18n.language === 'en' ? 'en' : 'zh',
      }
      if (regChannel === 'email') payload.email = regEmail.trim()
      else payload.phone = regPhone.trim()
      const r = await api.post('/auth/register', payload)
      await applyAuthSuccess(r.data)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(detail || t('auth.register_failed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[9999] grid place-items-center"
      style={{
        background: 'var(--wx-bg-overlay)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
      }}
      onClick={close}
      role="dialog"
      aria-modal="true"
      aria-labelledby="wx-auth-title"
    >
      <div
        className="wx-glass"
        style={{
          padding: '32px 28px 26px',
          maxWidth: 420,
          width: '92%',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        <button
          type="button"
          onClick={close}
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

        {/* Header */}
        <div
          style={{
            display: 'grid', placeItems: 'center',
            width: 48, height: 48, margin: '0 auto 10px',
            borderRadius: 12, background: 'var(--wx-grad-blue)',
          }}
        >
          <Lock size={22} color="var(--wx-text-on-primary)" />
        </div>
        <h2
          id="wx-auth-title"
          style={{
            fontSize: 19, fontWeight: 700, color: 'var(--wx-text-primary)',
            textAlign: 'center', marginBottom: 6,
          }}
        >
          {t('auth.modal_title')}
        </h2>
        <p
          style={{
            fontSize: 12.5, color: 'var(--wx-text-secondary)',
            textAlign: 'center', marginBottom: 18, lineHeight: 1.5,
          }}
        >
          {t('auth.modal_subtitle')}
        </p>

        {/* Tabs */}
        <div
          role="tablist"
          style={{
            display: 'flex', gap: 4, padding: 4,
            background: 'var(--wx-bg-subtle)',
            borderRadius: 10, marginBottom: 18,
            border: '1px solid var(--wx-border)',
          }}
        >
          <TabButton active={tab === 'login'} onClick={() => setTab('login')}>
            {t('auth.login')}
          </TabButton>
          <TabButton active={tab === 'register'} onClick={() => setTab('register')}>
            {t('auth.register')}
          </TabButton>
        </div>

        {tab === 'login' ? (
          <form onSubmit={submitLogin} style={{ display: 'grid', gap: 12 }}>
            <Field label={t('auth.identifier')}>
              <input
                className="wx-input"
                value={loginIdentifier}
                onChange={(e) => setLoginIdentifier(e.target.value)}
                placeholder="alice@example.com / 13800138000"
                autoFocus
                autoComplete="username"
              />
            </Field>
            <Field label={t('auth.password')}>
              <input
                className="wx-input"
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                autoComplete="current-password"
              />
            </Field>
            <button
              type="submit"
              className="wx-btn-primary"
              disabled={submitting}
              style={{ marginTop: 4 }}
            >
              {submitting ? t('common.loading') : t('auth.login')}
            </button>
            <p
              style={{
                fontSize: 12, color: 'var(--wx-text-tertiary)',
                textAlign: 'center', marginTop: 2,
              }}
            >
              {t('auth.no_account')}{' '}
              <button
                type="button"
                onClick={() => setTab('register')}
                style={{
                  background: 'transparent', border: 'none',
                  color: 'var(--wx-accent-cyan)', cursor: 'pointer',
                  font: 'inherit', padding: 0,
                }}
              >
                {t('auth.signup_now')}
              </button>
            </p>
          </form>
        ) : (
          <form onSubmit={submitRegister} style={{ display: 'grid', gap: 12 }}>
            {/* Email / Phone channel toggle */}
            <div
              role="tablist"
              style={{
                display: 'flex', gap: 4, padding: 3,
                background: 'var(--wx-bg-subtle)',
                borderRadius: 8,
                border: '1px solid var(--wx-border)',
              }}
            >
              <ChannelTab active={regChannel === 'email'} onClick={() => setRegChannel('email')}>
                {t('auth.tab_email')}
              </ChannelTab>
              <ChannelTab active={regChannel === 'phone'} onClick={() => setRegChannel('phone')}>
                {t('auth.tab_phone')}
              </ChannelTab>
            </div>
            {regChannel === 'email' ? (
              <Field label={t('auth.email')}>
                <input
                  className="wx-input"
                  type="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="alice@example.com"
                  autoComplete="email"
                />
              </Field>
            ) : (
              <Field label={t('auth.phone')}>
                <input
                  className="wx-input"
                  value={regPhone}
                  onChange={(e) => setRegPhone(e.target.value)}
                  placeholder="13800138000"
                  autoComplete="tel"
                />
              </Field>
            )}
            <Field label={t('auth.display_name')}>
              <input
                className="wx-input"
                value={regName}
                onChange={(e) => setRegName(e.target.value)}
                placeholder={t('auth.display_name')}
                autoComplete="name"
              />
            </Field>
            <Field label={t('auth.password')}>
              <input
                className="wx-input"
                type="password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder={t('auth.password_hint')}
                autoComplete="new-password"
              />
            </Field>
            <button
              type="submit"
              className="wx-btn-primary"
              disabled={submitting}
              style={{ marginTop: 4 }}
            >
              {submitting ? t('common.loading') : t('auth.register')}
            </button>
            <p
              style={{
                fontSize: 12, color: 'var(--wx-text-tertiary)',
                textAlign: 'center', marginTop: 2,
              }}
            >
              {t('auth.have_account')}{' '}
              <button
                type="button"
                onClick={() => setTab('login')}
                style={{
                  background: 'transparent', border: 'none',
                  color: 'var(--wx-accent-cyan)', cursor: 'pointer',
                  font: 'inherit', padding: 0,
                }}
              >
                {t('auth.signin_now')}
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}

function TabButton(props: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      role="tab"
      aria-selected={props.active}
      style={{
        flex: 1,
        padding: '8px 12px',
        background: props.active ? 'var(--wx-grad-blue)' : 'transparent',
        color: props.active ? 'var(--wx-text-on-primary)' : 'var(--wx-text-secondary)',
        border: 'none',
        borderRadius: 8,
        cursor: 'pointer',
        font: 'inherit',
        fontWeight: 600,
        fontSize: 13,
        transition: 'background 0.15s, color 0.15s',
      }}
    >
      {props.children}
    </button>
  )
}

function ChannelTab(props: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      role="tab"
      aria-selected={props.active}
      style={{
        flex: 1,
        padding: '6px 10px',
        background: props.active ? 'var(--wx-bg-active)' : 'transparent',
        color: props.active ? 'var(--wx-text-primary)' : 'var(--wx-text-tertiary)',
        border: 'none',
        borderRadius: 6,
        cursor: 'pointer',
        font: 'inherit',
        fontSize: 12,
        fontWeight: 500,
      }}
    >
      {props.children}
    </button>
  )
}

function Field(props: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'block' }}>
      <span
        style={{
          fontSize: 11.5, fontWeight: 600, letterSpacing: 0.5,
          color: 'var(--wx-text-secondary)',
          display: 'block', marginBottom: 5,
          textTransform: 'uppercase',
        }}
      >
        {props.label}
      </span>
      {props.children}
    </label>
  )
}
