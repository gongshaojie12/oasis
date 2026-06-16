// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Left sidebar: brand, "new sandbox" CTA, sandbox list, user/logout.
// Mirrors chat.html .sb / .sandbox / .usr.
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { BrandLogo } from '@/components/BrandLogo'
import { useAuthStore } from '@/stores/authStore'
import { clearTokens } from '@/lib/auth'
import { api } from '@/lib/api'
import type { Sandbox } from '@/types/api'

interface Props {
  workspaceSlug: string
  sandboxes: Sandbox[]
  activeSandboxId: string | null
  onPickSandbox: (id: string) => void
  onCreateSandbox: () => void
}

function fmtTime(iso: string, lang: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString(lang === 'en' ? 'en-US' : 'zh-CN', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function Sidebar({
  workspaceSlug,
  sandboxes,
  activeSandboxId,
  onPickSandbox,
  onCreateSandbox,
}: Props) {
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logoutStore = useAuthStore((s) => s.logout)

  async function logout() {
    try { await api.post('/auth/logout') } catch { /* stateless */ }
    clearTokens()
    logoutStore()
    nav('/login', { replace: true })
  }

  const firstChar = (user?.display_name ?? '?').trim().charAt(0).toUpperCase()

  return (
    <aside className="wx-sb">
      <div className="wx-sb-brand">
        <BrandLogo size="sm" />
      </div>
      <button
        type="button"
        className="wx-new-btn"
        onClick={onCreateSandbox}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2.4"
             strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12h14" />
          <path d="M12 5v14" />
        </svg>
        {t('sandbox.new')}
      </button>
      <div className="wx-sb-label">{t('nav.sandboxes')}</div>
      <div className="wx-sb-scroll">
        {sandboxes.length === 0 && (
          <div style={{ padding: '12px', fontSize: 12,
                         color: 'var(--wx-text-tertiary)' }}>
            {t('sandbox.empty')}
          </div>
        )}
        {sandboxes.map((s) => (
          <button
            key={s.sandbox_id}
            type="button"
            className={`wx-sandbox ${s.sandbox_id === activeSandboxId ? 'on' : ''}`}
            onClick={() => onPickSandbox(s.sandbox_id)}
          >
            <span className="wx-sb-emoji" aria-hidden="true">{s.emoji}</span>
            <span className="wx-sb-txt">
              <b>{s.name}</b>
              <small>{fmtTime(s.last_active_at, i18n.language)}</small>
            </span>
          </button>
        ))}
      </div>
      <div className="wx-sb-foot">
        <button type="button" className="wx-usr" onClick={() => nav(`/w/${workspaceSlug}`)}>
          <span className="wx-usr-av" aria-hidden="true">{firstChar}</span>
          <span style={{ flex: 1, minWidth: 0 }}>
            <b style={{ display: 'block', fontSize: 12.5, lineHeight: 1.3 }}>
              {user?.display_name ?? ''}
            </b>
            <small style={{ fontSize: 10.5, color: 'var(--wx-text-tertiary)' }}>
              {user?.email ?? ''}
            </small>
          </span>
        </button>
        <button
          type="button"
          className="wx-btn-ghost"
          style={{ width: '100%', marginTop: 8, fontSize: 12.5 }}
          onClick={logout}
        >
          {t('auth.logout')}
        </button>
      </div>
    </aside>
  )
}
