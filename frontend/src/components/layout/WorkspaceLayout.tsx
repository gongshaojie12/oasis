// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Shared layout for /w/:slug/* routes — sidebar with navigation +
// outlet for the active workspace page.
import { useEffect } from 'react'
import { Outlet, NavLink, useParams, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  FileBarChart,
  Wallet,
  Users,
  Key,
  Settings,
  Shield,
  LogOut,
  User as UserIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { BrandLogo } from '@/components/BrandLogo'
import { I18nToggle } from '@/components/I18nToggle'
import { ThemeToggle } from '@/components/ThemeToggle'
import { api } from '@/lib/api'
import { clearTokens } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'

interface NavItemConfig {
  to: string
  icon: typeof LayoutDashboard
  key: string
  end?: boolean
}

const NAV_ITEMS: NavItemConfig[] = [
  { to: '', icon: LayoutDashboard, key: 'nav.dashboard', end: true },
  { to: 'reports', icon: FileBarChart, key: 'nav.reports' },
  { to: 'billing', icon: Wallet, key: 'nav.billing' },
  { to: 'members', icon: Users, key: 'nav.members' },
  { to: 'api-keys', icon: Key, key: 'nav.api_keys' },
  { to: 'settings', icon: Settings, key: 'nav.settings' },
]

export function WorkspaceLayout() {
  const { slug } = useParams<{ slug: string }>()
  const nav = useNavigate()
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const workspaces = useAuthStore((s) => s.workspaces)
  const currentSlug = useAuthStore((s) => s.currentWorkspaceSlug)
  const setCurrentWorkspace = useAuthStore((s) => s.setCurrentWorkspace)
  const logoutStore = useAuthStore((s) => s.logout)
  const ws = workspaces.find((w) => w.slug === slug)

  useEffect(() => {
    if (slug && slug !== currentSlug) setCurrentWorkspace(slug)
  }, [slug, currentSlug, setCurrentWorkspace])

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

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--wx-grad-bg)' }}>
      <aside className="wx-side-nav" style={{ width: 240 }}>
        <div style={{ padding: '18px 16px 12px' }}>
          <BrandLogo size="sm" />
        </div>
        {ws && (
          <div style={{ padding: '4px 16px 12px' }}>
            <div
              className="text-xs"
              style={{
                color: 'var(--wx-text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '1.4px',
                fontWeight: 600,
              }}
            >
              {t('nav.current_workspace')}
            </div>
            <button
              type="button"
              className="text-sm"
              style={{
                marginTop: 2,
                background: 'transparent',
                border: 'none',
                color: 'var(--wx-text-primary)',
                padding: 0,
                cursor: 'pointer',
                fontWeight: 600,
                textAlign: 'left',
                width: '100%',
                font: 'inherit',
              }}
              onClick={() => nav('/workspaces')}
              title={t('dashboard.switch_workspace')}
            >
              {ws.name}
            </button>
            <div
              className="text-xs"
              style={{ color: 'var(--wx-text-secondary)', marginTop: 2 }}
            >
              {t('workspaces.units', { n: ws.balance_cost_units })}
            </div>
          </div>
        )}
        <nav style={{ padding: '0 10px 12px' }}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `wx-side-link ${isActive ? 'is-active' : ''}`
              }
            >
              <item.icon size={16} />
              {t(item.key)}
            </NavLink>
          ))}
          <div className="wx-divider-h" />
          <button
            type="button"
            className="wx-side-link"
            style={{ width: '100%', background: 'transparent', border: 'none', font: 'inherit', cursor: 'pointer' }}
            onClick={() => nav(`/w/${slug}`)}
          >
            <MessageSquare size={16} />
            {t('nav.sandboxes')}
          </button>
          {user?.is_super_admin && (
            <NavLink
              to="/admin"
              className="wx-side-link wx-side-link-admin"
              style={{ marginTop: 10 }}
            >
              <Shield size={16} />
              {t('nav.admin')}
            </NavLink>
          )}
        </nav>
        <div className="wx-side-nav-foot">
          <div style={{ display: 'flex', gap: 4 }}>
            <ThemeToggle />
            <I18nToggle />
            <button
              type="button"
              className="wx-icon-btn"
              onClick={() => nav('/settings/account')}
              title={t('settings.account_title')}
              aria-label="account"
            >
              <UserIcon size={14} />
            </button>
          </div>
          <button
            type="button"
            className="wx-icon-btn"
            onClick={handleLogout}
            title={t('auth.logout')}
            aria-label="logout"
          >
            <LogOut size={14} />
          </button>
        </div>
      </aside>
      <main
        className="flex-1 min-w-0"
        style={{ overflowY: 'auto', maxHeight: '100vh' }}
      >
        <Outlet />
      </main>
    </div>
  )
}
