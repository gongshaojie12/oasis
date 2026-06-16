// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { setTokens } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'
import type { LoginResponse } from '@/types/api'

interface LocationState {
  from?: string
}

export function LoginPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const loc = useLocation()
  const state = (loc.state ?? null) as LocationState | null
  const setUser = useAuthStore((s) => s.setUser)
  const setWorkspaces = useAuthStore((s) => s.setWorkspaces)
  const setCurrentWorkspace = useAuthStore((s) => s.setCurrentWorkspace)

  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!identifier || !password) {
      toast.error(t('auth.email_or_phone_required'))
      return
    }
    setLoading(true)
    try {
      const r = await api.post<LoginResponse>('/auth/login', { identifier, password })
      setTokens({ access: r.data.access_token, refresh: r.data.refresh_token })
      setUser(r.data.user)
      setWorkspaces(r.data.workspaces)
      const first = r.data.workspaces[0]
      if (first) setCurrentWorkspace(first.slug)
      const target = state?.from || '/dashboard'
      nav(target, { replace: true })
    } catch (err) {
      const detail = errorDetail(err) ?? t('auth.invalid_credentials')
      toast.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageShell>
      <GlassCard>
        <h1 className="text-xl font-semibold mb-2">
          {t('auth.welcome', { brand: `${t('brand.cn_name')} ${t('brand.en_name')}` })}
        </h1>
        <p className="text-sm mb-6" style={{ color: 'var(--wx-text-secondary)' }}>
          {t('auth.sign_in_to_continue')}
        </p>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="wx-label" htmlFor="login-id">{t('auth.identifier')}</label>
            <input
              id="login-id"
              className="wx-input"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="alice@example.com / 13800138000"
              autoComplete="username"
              autoFocus
            />
          </div>
          <div>
            <label className="wx-label" htmlFor="login-pw">{t('auth.password')}</label>
            <input
              id="login-pw"
              className="wx-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="wx-btn-primary w-full" disabled={loading}>
            {loading ? t('common.loading') : t('auth.login')}
          </button>
        </form>
        <div className="mt-6 flex justify-between text-sm" style={{ color: 'var(--wx-text-secondary)' }}>
          <Link to="/forgot-password" className="wx-link">{t('auth.forgot_password')}</Link>
          <span>
            {t('auth.no_account')}{' '}
            <Link to="/register" className="wx-link">{t('auth.signup_now')}</Link>
          </span>
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
