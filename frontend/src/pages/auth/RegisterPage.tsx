// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { setTokens } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'
import type { RegisterResponse } from '@/types/api'

type Tab = 'email' | 'phone'

export function RegisterPage() {
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)
  const setWorkspaces = useAuthStore((s) => s.setWorkspaces)
  const setCurrentWorkspace = useAuthStore((s) => s.setCurrentWorkspace)

  const [tab, setTab] = useState<Tab>('email')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [smsCode, setSmsCode] = useState('')
  const [sendingCode, setSendingCode] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const [loading, setLoading] = useState(false)

  function startCooldown(seconds = 60) {
    setCooldown(seconds)
    const handle = window.setInterval(() => {
      setCooldown((s) => {
        if (s <= 1) {
          window.clearInterval(handle)
          return 0
        }
        return s - 1
      })
    }, 1000)
  }

  async function sendSmsCode() {
    if (!phone) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    setSendingCode(true)
    try {
      await api.post('/auth/send-sms-code', { identifier: phone, purpose: 'verify' })
      toast.success(t('auth.code_sent'))
      startCooldown(60)
    } catch (err) {
      toast.error(errorDetail(err) ?? t('auth.code_send_failed'))
    } finally {
      setSendingCode(false)
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (tab === 'email' && !email) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    if (tab === 'phone' && !phone) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    if (!displayName) {
      toast.error(t('common.required'))
      return
    }
    if (!password || password.length < 8) {
      toast.error(t('auth.password_too_short'))
      return
    }
    if (password !== confirm) {
      toast.error(t('auth.password_mismatch'))
      return
    }
    setLoading(true)
    try {
      if (tab === 'phone') {
        if (!smsCode) {
          toast.error(t('common.required'))
          setLoading(false)
          return
        }
        await api.post('/auth/verify-sms-code', {
          identifier: phone,
          code: smsCode,
          purpose: 'verify',
        })
      }
      const body: Record<string, string> = {
        password,
        display_name: displayName,
        locale: i18n.language === 'en' ? 'en' : 'zh',
      }
      if (tab === 'email') body.email = email
      else body.phone = phone
      const r = await api.post<RegisterResponse>('/auth/register', body)
      setTokens({ access: r.data.access_token, refresh: r.data.refresh_token })
      setUser(r.data.user)
      setWorkspaces([r.data.default_workspace])
      setCurrentWorkspace(r.data.default_workspace.slug)
      toast.success(t('auth.register_success'))
      nav('/onboarding', { replace: true })
    } catch (err) {
      toast.error(errorDetail(err) ?? t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageShell>
      <GlassCard>
        <h1 className="text-xl font-semibold mb-2">{t('auth.create_account')}</h1>
        <p className="text-sm mb-5" style={{ color: 'var(--wx-text-secondary)' }}>
          {t('brand.subtitle')}
        </p>
        <div className="flex mb-5" style={{ borderBottom: '1px solid var(--wx-glass-border)' }}>
          <button type="button" className={`wx-tab ${tab === 'email' ? 'active' : ''}`} onClick={() => setTab('email')}>{t('auth.tab_email')}</button>
          <button type="button" className={`wx-tab ${tab === 'phone' ? 'active' : ''}`} onClick={() => setTab('phone')}>{t('auth.tab_phone')}</button>
        </div>
        <form onSubmit={submit} className="space-y-4">
          {tab === 'email' ? (
            <div>
              <label className="wx-label" htmlFor="reg-email">{t('auth.email')}</label>
              <input id="reg-email" className="wx-input" type="email"
                value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.email_placeholder')} autoComplete="email" />
            </div>
          ) : (
            <>
              <div>
                <label className="wx-label" htmlFor="reg-phone">{t('auth.phone')}</label>
                <input id="reg-phone" className="wx-input" type="tel"
                  value={phone} onChange={(e) => setPhone(e.target.value)}
                  placeholder={t('auth.phone_placeholder')} autoComplete="tel" />
              </div>
              <div>
                <label className="wx-label" htmlFor="reg-code">{t('auth.code')}</label>
                <div className="flex gap-2">
                  <input id="reg-code" className="wx-input" inputMode="numeric"
                    value={smsCode} onChange={(e) => setSmsCode(e.target.value)}
                    placeholder={t('auth.code_placeholder')} maxLength={8} />
                  <button type="button" className="wx-btn-ghost whitespace-nowrap"
                    disabled={sendingCode || cooldown > 0} onClick={sendSmsCode}>
                    {cooldown > 0
                      ? t('auth.resend_in_sec', { seconds: cooldown })
                      : t('auth.send_code')}
                  </button>
                </div>
              </div>
            </>
          )}
          <div>
            <label className="wx-label" htmlFor="reg-name">{t('auth.display_name')}</label>
            <input id="reg-name" className="wx-input"
              value={displayName} onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="nickname" />
          </div>
          <div>
            <label className="wx-label" htmlFor="reg-pw">{t('auth.password')}</label>
            <input id="reg-pw" className="wx-input" type="password"
              value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password" />
          </div>
          <div>
            <label className="wx-label" htmlFor="reg-pw2">{t('auth.confirm_password')}</label>
            <input id="reg-pw2" className="wx-input" type="password"
              value={confirm} onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password" />
          </div>
          <button type="submit" className="wx-btn-primary w-full" disabled={loading}>
            {loading ? t('common.loading') : t('auth.register')}
          </button>
        </form>
        <div className="mt-6 text-sm text-center" style={{ color: 'var(--wx-text-secondary)' }}>
          {t('auth.have_account')}{' '}
          <Link to="/login" className="wx-link">{t('auth.signin_now')}</Link>
        </div>
      </GlassCard>
    </PageShell>
  )
}

function errorDetail(err: unknown): string | null {
  if (typeof err !== 'object' || err === null) return null
  const maybe = err as { response?: { data?: { detail?: unknown } } }
  const d = maybe.response?.data?.detail
  return typeof d === 'string' ? d : null
}
