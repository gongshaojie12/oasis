// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage left sidebar.
// - Anonymous: only WANXIANG logo + 注册 / 登录 CTA buttons.
// - Authenticated: workspace picker (if >1), "+ 新建沙盒" button, list of real
//   sandboxes from GET /v1/workspaces/{slug}/sandboxes, empty state when none,
//   bottom user pill + 退出登录.
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { LogIn, LogOut, Plus, UserPlus } from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'
import { clearTokens } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'
import type { Sandbox, User, Workspace } from '@/types/api'

interface Props {
  authed: boolean
  workspaces: Workspace[]
  currentWs: Workspace | undefined
  sandboxes: Sandbox[]
  activeSandbox: Sandbox | null
  onSelectWorkspace: (slug: string) => void
  onSelectSandbox: (sb: Sandbox) => void
  onCreateSandbox: (name: string) => Promise<void>
  user: User | null
}

export function LandingSidebar(p: Props) {
  const { t } = useTranslation()
  const nav = useNavigate()
  const { logout } = useAuthStore()
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submitCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim() || submitting) return
    setSubmitting(true)
    try {
      await p.onCreateSandbox(newName.trim())
      setNewName('')
      setCreating(false)
    } finally {
      setSubmitting(false)
    }
  }

  if (!p.authed) {
    // Anonymous sidebar
    return (
      <aside className="wx-sb">
        <div className="wx-sb-brand">
          <BrandLogo size="md" />
        </div>
        <div className="wx-sb-empty">
          <p
            style={{
              fontSize: 12.5,
              color: 'var(--wx-text-secondary)',
              lineHeight: 1.6,
              marginBottom: 16,
            }}
          >
            {t('landing.anon_sidebar_intro')}
          </p>
          <button
            type="button"
            className="wx-btn-primary"
            style={{ width: '100%', marginBottom: 8 }}
            onClick={() => nav('/register')}
          >
            <UserPlus size={14} style={{ display: 'inline', marginRight: 6 }} />
            {t('auth.register')}
          </button>
          <button
            type="button"
            className="wx-btn-ghost"
            style={{ width: '100%' }}
            onClick={() => nav('/login')}
          >
            <LogIn size={14} style={{ display: 'inline', marginRight: 6 }} />
            {t('auth.login')}
          </button>
        </div>
      </aside>
    )
  }

  // Authenticated sidebar
  return (
    <aside className="wx-sb">
      <div className="wx-sb-brand">
        <BrandLogo size="md" />
      </div>

      {p.workspaces.length > 1 && (
        <div style={{ padding: '0 8px 8px' }}>
          <label
            style={{
              fontSize: 10,
              color: 'var(--wx-text-tertiary)',
              letterSpacing: 1.5,
              fontWeight: 700,
              display: 'block',
              marginBottom: 4,
              textTransform: 'uppercase',
            }}
          >
            {t('landing.workspace_switcher')}
          </label>
          <select
            className="wx-input"
            style={{ fontSize: 12.5, padding: '8px 10px' }}
            value={p.currentWs?.slug || ''}
            onChange={(e) => p.onSelectWorkspace(e.target.value)}
          >
            {p.workspaces.map((w) => (
              <option key={w.slug} value={w.slug}>{w.name}</option>
            ))}
          </select>
        </div>
      )}

      <button
        type="button"
        className="wx-new-btn"
        onClick={() => setCreating(true)}
      >
        <Plus size={14} />
        {t('landing.new_sandbox')}
      </button>

      {creating && (
        <form onSubmit={submitCreate} style={{ padding: '0 8px 12px' }}>
          <input
            className="wx-input"
            style={{ fontSize: 12.5 }}
            placeholder={t('landing.sandbox_name_placeholder')}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            autoFocus
          />
          <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
            <button
              type="submit"
              className="wx-btn-primary"
              style={{ fontSize: 11, padding: '6px 10px', flex: 1 }}
              disabled={submitting || !newName.trim()}
            >
              {t('common.create')}
            </button>
            <button
              type="button"
              className="wx-btn-ghost"
              style={{ fontSize: 11, padding: '6px 10px' }}
              onClick={() => { setCreating(false); setNewName('') }}
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      )}

      <div className="wx-sb-label">{t('landing.sandbox_label')}</div>
      <div className="wx-sb-scroll">
        {p.sandboxes.length === 0 ? (
          <div className="wx-sb-empty-state">
            <p
              style={{
                fontSize: 12,
                color: 'var(--wx-text-tertiary)',
                padding: '12px 12px',
                lineHeight: 1.5,
              }}
            >
              {t('landing.no_sandboxes')}
            </p>
          </div>
        ) : (
          p.sandboxes.map((sb) => (
            <button
              key={sb.sandbox_id}
              type="button"
              className={`wx-sandbox ${p.activeSandbox?.sandbox_id === sb.sandbox_id ? 'on' : ''}`}
              onClick={() => p.onSelectSandbox(sb)}
            >
              <span className="wx-sb-emoji" aria-hidden="true">{sb.emoji}</span>
              <span className="wx-sb-txt">
                <b>{sb.name}</b>
                <small>
                  {sb.population_size.toLocaleString()} {t('landing.people_suffix')}
                </small>
              </span>
            </button>
          ))
        )}
      </div>

      <div className="wx-sb-foot">
        <div
          className="wx-usr"
          style={{ cursor: 'default' }}
          role="presentation"
        >
          <span className="wx-usr-av" aria-hidden="true">
            {(p.user?.display_name || '?').slice(0, 1)}
          </span>
          <span style={{ flex: 1, minWidth: 0 }}>
            <b
              style={{
                display: 'block',
                fontSize: 12.5,
                lineHeight: 1.3,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {p.user?.display_name || '…'}
            </b>
            <small
              style={{
                fontSize: 10.5,
                color: 'var(--wx-text-tertiary)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: 'block',
              }}
            >
              {p.currentWs?.name || ''}
            </small>
          </span>
          <button
            type="button"
            title={t('auth.logout')}
            aria-label={t('auth.logout')}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--wx-text-tertiary)',
              padding: 4,
              display: 'inline-flex',
            }}
            onClick={() => {
              clearTokens()
              logout()
              window.location.assign('/')
            }}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  )
}
