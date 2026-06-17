// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage left sidebar — ChatGPT-style:
//  - top: brand row (logo + collapse button)
//  - nav: 7 nav items (Chat / Dashboard / Reports / Billing / Members /
//    API Keys / Settings). Click on a requires-auth item while anonymous
//    triggers AuthGateModal via onSelectView.
//  - sub-nav: sandbox list (shown when activeView === 'chat' AND authed)
//  - spacer (flex: 1) pushes the bottom area down
//  - bottom: anonymous → intro text + 登录 / 注册 CTAs;
//            authed → user pill + logout
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronLeft, ChevronRight,
  FileBarChart, Key, LayoutDashboard, LogIn, LogOut,
  MessageSquare, Plus, Settings, Shield, UserPlus, Users, Wallet,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'
import { NewSandboxModal } from '@/components/chat/NewSandboxModal'
import { clearTokens } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'
import type { Sandbox, User, Workspace } from '@/types/api'

export interface CreateSandboxPayload {
  name: string
  emoji: string
  description: string
  population_size: number
  distribution_path: string
}

export type ViewKey =
  | 'chat'
  | 'dashboard'
  | 'reports'
  | 'billing'
  | 'members'
  | 'api_keys'
  | 'settings'

interface NavItemCfg {
  key: ViewKey
  labelKey: string
  icon: LucideIcon
  requiresAuth: boolean
}

const NAV_ITEMS: NavItemCfg[] = [
  { key: 'chat',      labelKey: 'nav.chat',      icon: MessageSquare,   requiresAuth: false },
  { key: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, requiresAuth: true  },
  { key: 'reports',   labelKey: 'nav.reports',   icon: FileBarChart,    requiresAuth: true  },
  { key: 'billing',   labelKey: 'nav.billing',   icon: Wallet,          requiresAuth: true  },
  { key: 'members',   labelKey: 'nav.members',   icon: Users,           requiresAuth: true  },
  { key: 'api_keys',  labelKey: 'nav.api_keys',  icon: Key,             requiresAuth: true  },
  { key: 'settings',  labelKey: 'nav.settings',  icon: Settings,        requiresAuth: true  },
]

interface Props {
  authed: boolean
  workspaces: Workspace[]
  currentWs: Workspace | undefined
  sandboxes: Sandbox[]
  activeSandbox: Sandbox | null
  onSelectWorkspace: (slug: string) => void
  onSelectSandbox: (sb: Sandbox) => void
  onCreateSandbox: (payload: CreateSandboxPayload) => Promise<void>
  user: User | null
  collapsed: boolean
  onToggleCollapse: () => void
  /** Anonymous click on 登录/注册 — open the inline auth modal */
  onOpenAuth: (initialTab: 'login' | 'register') => void
  /** Currently-active main-area view */
  activeView: ViewKey
  /** Click a nav item. Sidebar passes requiresAuth so the page can
   *  decide to open the auth gate when an anon user tries a protected view. */
  onSelectView: (view: ViewKey, requiresAuth: boolean) => void
}

function CollapseToggle({ collapsed, onClick, side }: {
  collapsed: boolean; onClick: () => void; side: 'left' | 'right'
}) {
  const Arrow = side === 'left'
    ? (collapsed ? ChevronRight : ChevronLeft)
    : (collapsed ? ChevronLeft : ChevronRight)
  return (
    <button
      type="button"
      className="wx-collapse-btn"
      onClick={onClick}
      title={collapsed ? '展开 / Expand' : '收起 / Collapse'}
      aria-label={collapsed ? 'Expand panel' : 'Collapse panel'}
    >
      <Arrow size={14} />
    </button>
  )
}

export function LandingSidebar(p: Props) {
  const { t } = useTranslation()
  const { logout } = useAuthStore()
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function submitFromModal(payload: CreateSandboxPayload) {
    if (submitting) return
    setSubmitting(true)
    try {
      await p.onCreateSandbox(payload)
      setModalOpen(false)
    } finally {
      setSubmitting(false)
    }
  }

  // Collapsed mode: narrow strip with brand avatar + expand button
  if (p.collapsed) {
    return (
      <aside className="wx-sb collapsed" aria-label="Sidebar (collapsed)">
        <div className="wx-sb-collapsed-inner">
          <div className="wx-brand-avatar" style={{ width: 36, height: 36, fontSize: 16 }}>
            象
          </div>
          <CollapseToggle collapsed={true} onClick={p.onToggleCollapse} side="left" />
        </div>
      </aside>
    )
  }

  function handleNavClick(item: NavItemCfg) {
    p.onSelectView(item.key, item.requiresAuth)
  }

  return (
    <aside className="wx-sb">
      {/* Brand row */}
      <div className="wx-sb-brand">
        <BrandLogo size="md" />
        <CollapseToggle collapsed={false} onClick={p.onToggleCollapse} side="left" />
      </div>

      {/* Workspace switcher (only if authed and multiple workspaces) */}
      {p.authed && p.workspaces.length > 1 && (
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

      {/* Nav menu */}
      <nav className="wx-nav" aria-label="Primary navigation">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const active = p.activeView === item.key
          return (
            <button
              key={item.key}
              type="button"
              className={`wx-nav-item${active ? ' active' : ''}`}
              onClick={() => handleNavClick(item)}
            >
              <Icon size={16} />
              <span>{t(item.labelKey)}</span>
            </button>
          )
        })}
        {p.authed && p.user?.is_super_admin && (
          <a
            className="wx-nav-item"
            href="/admin"
            style={{ marginTop: 8, color: 'var(--wx-accent-cyan)' }}
          >
            <Shield size={16} />
            <span>{t('nav.admin')}</span>
          </a>
        )}
      </nav>

      {/* Sub-nav: sandbox list (only on chat view + authed) */}
      {p.authed && p.activeView === 'chat' && (
        <>
          <button
            type="button"
            className="wx-new-btn"
            onClick={() => setModalOpen(true)}
          >
            <Plus size={14} />
            {t('landing.new_sandbox')}
          </button>

          <NewSandboxModal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            onSubmit={submitFromModal}
            submitting={submitting}
          />

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
        </>
      )}

      {/* Spacer pushes bottom area down (only when no sandbox sub-list is
          taking the vertical space). On chat view + authed the sandbox
          scroll has flex:1 already; on every other view we need this. */}
      {!(p.authed && p.activeView === 'chat') && <div style={{ flex: 1 }} />}

      {/* Bottom: auth CTAs (anon) or user pill (authed) */}
      <div className="wx-sb-bottom">
        {p.authed ? (
          <div className="wx-usr" style={{ cursor: 'default' }} role="presentation">
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
        ) : (
          <>
            <p className="wx-sb-bottom-cta-intro">
              {t('landing.anon_get_personalized')}
            </p>
            <button
              type="button"
              className="wx-btn-ghost"
              style={{ width: '100%', marginBottom: 8 }}
              onClick={() => p.onOpenAuth('login')}
            >
              <LogIn size={14} style={{ display: 'inline', marginRight: 6 }} />
              {t('auth.login')}
            </button>
            <button
              type="button"
              className="wx-btn-primary"
              style={{ width: '100%' }}
              onClick={() => p.onOpenAuth('register')}
            >
              <UserPlus size={14} style={{ display: 'inline', marginRight: 6 }} />
              {t('auth.register')}
            </button>
          </>
        )}
      </div>
    </aside>
  )
}
