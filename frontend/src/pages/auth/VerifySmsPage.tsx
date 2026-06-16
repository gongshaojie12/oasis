// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'

export function VerifySmsPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const initialPhone = user?.phone ?? ''
  const [phone, setPhone] = useState(initialPhone)
  const [code, setCode] = useState('')
  const [sending, setSending] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [cooldown, setCooldown] = useState(0)

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

  async function send() {
    if (!phone) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    setSending(true)
    try {
      await api.post('/auth/send-sms-code', { identifier: phone, purpose: 'verify' })
      toast.success(t('auth.code_sent'))
      startCooldown(60)
    } catch (err) {
      toast.error(errorDetail(err) ?? t('auth.code_send_failed'))
    } finally {
      setSending(false)
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!phone || !code) {
      toast.error(t('common.required'))
      return
    }
    setVerifying(true)
    try {
      await api.post('/auth/verify-sms-code', { identifier: phone, code, purpose: 'verify' })
      if (user) setUser({ ...user, phone_verified: true })
      toast.success(t('auth.verify_success'))
      nav('/dashboard', { replace: true })
    } catch (err) {
      toast.error(errorDetail(err) ?? t('common.error'))
    } finally {
      setVerifying(false)
    }
  }

  return (
    <PageShell>
      <GlassCard>
        <h1 className="text-xl font-semibold mb-2">{t('auth.verify_sms_title')}</h1>
        <p className="text-sm mb-5" style={{ color: 'var(--wx-text-secondary)' }}>
          {t('auth.verify_subtitle', { identifier: phone || '—' })}
        </p>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="wx-label" htmlFor="vs-phone">{t('auth.phone')}</label>
            <input id="vs-phone" className="wx-input" type="tel"
              value={phone} onChange={(e) => setPhone(e.target.value)}
              placeholder={t('auth.phone_placeholder')} />
          </div>
          <div>
            <label className="wx-label" htmlFor="vs-code">{t('auth.code')}</label>
            <div className="flex gap-2">
              <input id="vs-code" className="wx-input" inputMode="numeric"
                value={code} onChange={(e) => setCode(e.target.value)}
                placeholder={t('auth.code_placeholder')} maxLength={8} />
              <button type="button" className="wx-btn-ghost whitespace-nowrap"
                onClick={send} disabled={sending || cooldown > 0}>
                {cooldown > 0
                  ? t('auth.resend_in_sec', { seconds: cooldown })
                  : t('auth.send_code')}
              </button>
            </div>
          </div>
          <button type="submit" className="wx-btn-primary w-full" disabled={verifying}>
            {verifying ? t('common.loading') : t('common.submit')}
          </button>
        </form>
        <div className="mt-6 text-center text-sm">
          <button type="button" className="wx-link"
            onClick={() => nav('/dashboard', { replace: true })}>
            {t('auth.skip_verify')}
          </button>
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
