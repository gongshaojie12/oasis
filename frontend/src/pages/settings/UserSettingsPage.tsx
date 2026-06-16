// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// /settings/account — display name, locale, identity, password reset stub.
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowLeft, LogOut, ShieldCheck, ShieldOff } from 'lucide-react'
import { api } from '@/lib/api'
import { clearTokens } from '@/lib/auth'
import { switchLang } from '@/lib/i18n'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'
import { FormField } from '@/components/forms/FormField'
import { Select } from '@/components/forms/Select'
import { useAuthStore } from '@/stores/authStore'

export function UserSettingsPage() {
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logoutStore = useAuthStore((s) => s.logout)

  async function handleLogout() {
    try {
      await api.post('/auth/logout')
    } catch {
      /* stateless */
    }
    clearTokens()
    logoutStore()
    toast.success(t('auth.logout'))
    nav('/login', { replace: true })
  }

  if (!user) {
    return (
      <PageShell>
        <GlassCard>{t('common.loading')}</GlassCard>
      </PageShell>
    )
  }

  return (
    <PageShell>
      <button
        type="button"
        className="wx-btn-ghost text-sm"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 14,
        }}
        onClick={() => nav(-1)}
      >
        <ArrowLeft size={14} />
        {t('common.back')}
      </button>
      <GlassCard>
        <h1
          style={{ fontSize: 20, fontWeight: 600, margin: 0 }}
        >
          {t('settings.account_title')}
        </h1>
        <p
          className="text-sm"
          style={{ color: 'var(--wx-text-secondary)', marginTop: 4 }}
        >
          {t('settings.account_subtitle')}
        </p>
        <div className="wx-divider-h" />

        <FormField label={t('auth.display_name')}>
          <input
            className="wx-input"
            value={user.display_name}
            readOnly
          />
        </FormField>
        <FormField
          label={t('auth.email')}
          hint={
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                color: user.email_verified
                  ? 'var(--wx-success)'
                  : 'var(--wx-text-tertiary)',
              }}
            >
              {user.email_verified ? (
                <>
                  <ShieldCheck size={12} /> {t('settings.verified')}
                </>
              ) : (
                <>
                  <ShieldOff size={12} /> {t('settings.unverified')}
                </>
              )}
            </span>
          }
        >
          <input
            className="wx-input"
            value={user.email ?? ''}
            readOnly
          />
        </FormField>
        {user.phone && (
          <FormField label={t('auth.phone')}>
            <input
              className="wx-input"
              value={user.phone}
              readOnly
            />
          </FormField>
        )}
        <FormField
          label={t('settings.locale')}
          hint={t('settings.locale_hint')}
        >
          <Select
            value={i18n.language === 'en' ? 'en' : 'zh'}
            options={[
              { value: 'zh', label: '中文' },
              { value: 'en', label: 'English' },
            ]}
            onChange={(v) => {
              switchLang(v === 'en' ? 'en' : 'zh')
              toast.success(t('settings.saved'))
            }}
          />
        </FormField>
      </GlassCard>

      <GlassCard className="mt-6">
        <div className="wx-stat-label" style={{ marginBottom: 8 }}>
          {t('settings.password_title')}
        </div>
        <p
          className="text-sm"
          style={{
            color: 'var(--wx-text-secondary)',
            marginBottom: 0,
          }}
        >
          {t('settings.password_mvp_hint')}
        </p>
      </GlassCard>

      <GlassCard className="mt-6">
        <button
          type="button"
          className="wx-btn-ghost"
          style={{
            color: 'var(--wx-danger)',
            borderColor: 'rgba(255, 77, 110, .35)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
          onClick={handleLogout}
        >
          <LogOut size={14} />
          {t('auth.logout')}
        </button>
      </GlassCard>
    </PageShell>
  )
}
