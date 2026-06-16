// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Layout for /admin/* super-admin routes — separate from workspace layout.
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Users, Building, Receipt, ArrowLeft } from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'
import { I18nToggle } from '@/components/I18nToggle'

const ADMIN_NAV = [
  { to: '/admin/users', icon: Users, key: 'admin.users' },
  { to: '/admin/workspaces', icon: Building, key: 'admin.workspaces' },
  { to: '/admin/transactions', icon: Receipt, key: 'admin.transactions' },
]

export function AdminLayout() {
  const { t } = useTranslation()
  const nav = useNavigate()
  return (
    <div className="min-h-screen flex" style={{ background: 'var(--wx-grad-bg)' }}>
      <aside className="wx-side-nav" style={{ width: 240 }}>
        <div style={{ padding: '18px 16px 12px' }}>
          <BrandLogo size="sm" />
          <div
            className="text-xs"
            style={{
              marginTop: 8,
              color: 'var(--wx-accent-amber)',
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: 'uppercase',
            }}
          >
            {t('admin.title')}
          </div>
        </div>
        <nav style={{ padding: '0 10px 12px' }}>
          {ADMIN_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
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
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              font: 'inherit',
              cursor: 'pointer',
            }}
            onClick={() => nav('/workspaces')}
          >
            <ArrowLeft size={16} />
            {t('nav.back_to_app')}
          </button>
        </nav>
        <div className="wx-side-nav-foot">
          <I18nToggle />
        </div>
      </aside>
      <main className="flex-1 min-w-0" style={{ overflowY: 'auto', maxHeight: '100vh' }}>
        <Outlet />
      </main>
    </div>
  )
}
