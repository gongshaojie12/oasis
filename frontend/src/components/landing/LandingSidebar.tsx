// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage left sidebar — ChatGPT-style:
//  - top: brand row (logo + collapse button)
//  - 「+ 新对话」 + 「+ 新建分组」
//  - scroll area: groups (collapsible) + ungrouped prediction-task list
//  - bottom: user pill → click opens a popup menu holding the nav items
//    (dashboard/reports/billing/members/api_keys/settings/admin) + logout
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronDown, ChevronLeft, ChevronRight, ChevronUp,
  FileBarChart, FolderPlus, Key, LayoutDashboard, LogIn, LogOut,
  MoreHorizontal, Plus, Settings, Shield, Trash2, UserPlus, Users, Wallet,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { BrandLogo } from '@/components/BrandLogo'
import { clearTokens } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'
import type { Sandbox, SandboxGroup, User, Workspace } from '@/types/api'

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
  { key: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, requiresAuth: true },
  { key: 'reports',   labelKey: 'nav.reports',   icon: FileBarChart,    requiresAuth: true },
  { key: 'billing',   labelKey: 'nav.billing',   icon: Wallet,          requiresAuth: true },
  { key: 'members',   labelKey: 'nav.members',   icon: Users,           requiresAuth: true },
  { key: 'api_keys',  labelKey: 'nav.api_keys',  icon: Key,             requiresAuth: true },
  { key: 'settings',  labelKey: 'nav.settings',  icon: Settings,        requiresAuth: true },
]

interface Props {
  authed: boolean
  workspaces: Workspace[]
  currentWs: Workspace | undefined
  sandboxes: Sandbox[]
  groups: SandboxGroup[]
  activeSandbox: Sandbox | null
  onSelectWorkspace: (slug: string) => void
  onSelectSandbox: (sb: Sandbox) => void
  onDeleteSandbox: (sb: Sandbox) => void
  onNewChat: () => void
  onCreateGroup: (name: string) => void
  onRenameGroup: (group: SandboxGroup, name: string) => void
  onDeleteGroup: (group: SandboxGroup) => void
  onMoveSandbox: (sb: Sandbox, groupId: string | null) => void
  user: User | null
  collapsed: boolean
  onToggleCollapse: () => void
  onOpenAuth: (initialTab: 'login' | 'register') => void
  activeView: ViewKey
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

  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [creatingGroup, setCreatingGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  // 折叠状态:默认全部展开。记录被手动折叠的分组 id。
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())
  // 当前打开 … 菜单的任务 id / 分组 id
  const [taskMenu, setTaskMenu] = useState<string | null>(null)
  const [groupMenu, setGroupMenu] = useState<string | null>(null)

  const bottomRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭所有弹出菜单
  useEffect(() => {
    function onDocClick() {
      setUserMenuOpen(false)
      setTaskMenu(null)
      setGroupMenu(null)
    }
    if (userMenuOpen || taskMenu || groupMenu) {
      document.addEventListener('click', onDocClick)
      return () => document.removeEventListener('click', onDocClick)
    }
  }, [userMenuOpen, taskMenu, groupMenu])

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

  function toggleGroup(id: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function submitNewGroup() {
    const name = newGroupName.trim()
    if (name) p.onCreateGroup(name)
    setNewGroupName('')
    setCreatingGroup(false)
  }

  const ungrouped = p.sandboxes.filter((s) => !s.group_id)

  function renderSandbox(sb: Sandbox) {
    const isActive = p.activeSandbox?.sandbox_id === sb.sandbox_id
    return (
      <div
        key={sb.sandbox_id}
        role="button"
        tabIndex={0}
        className={`wx-sandbox ${isActive ? 'on' : ''}`}
        onClick={() => p.onSelectSandbox(sb)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            p.onSelectSandbox(sb)
          }
        }}
      >
        <span className="wx-sb-emoji" aria-hidden="true">{sb.emoji}</span>
        <span className="wx-sb-txt">
          <b>{sb.name}</b>
          <small>
            {sb.population_size.toLocaleString()} {t('landing.people_suffix')}
          </small>
        </span>
        <button
          type="button"
          className="wx-sandbox-del"
          title={t('common.more') || '更多'}
          aria-label={t('common.more') || '更多'}
          onClick={(e) => {
            e.stopPropagation()
            setGroupMenu(null)
            setTaskMenu(taskMenu === sb.sandbox_id ? null : sb.sandbox_id)
          }}
        >
          <MoreHorizontal size={15} />
        </button>
        {taskMenu === sb.sandbox_id && (
          <div className="wx-pop-menu" onClick={(e) => e.stopPropagation()}>
            <div className="wx-pop-label">{t('sandbox.move_to')}</div>
            {p.groups.map((g) => (
              <button
                key={g.group_id}
                type="button"
                className="wx-pop-item"
                disabled={sb.group_id === g.group_id}
                onClick={() => { p.onMoveSandbox(sb, g.group_id); setTaskMenu(null) }}
              >
                {g.name}
              </button>
            ))}
            {sb.group_id && (
              <button
                type="button"
                className="wx-pop-item"
                onClick={() => { p.onMoveSandbox(sb, null); setTaskMenu(null) }}
              >
                {t('sandbox.ungrouped')}
              </button>
            )}
            {p.groups.length === 0 && (
              <div className="wx-pop-empty">{t('sandbox.no_groups_hint')}</div>
            )}
            <div className="wx-pop-sep" />
            <button
              type="button"
              className="wx-pop-item danger"
              onClick={() => { p.onDeleteSandbox(sb); setTaskMenu(null) }}
            >
              <Trash2 size={13} /> {t('sandbox.delete')}
            </button>
          </div>
        )}
      </div>
    )
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
              fontSize: 10, color: 'var(--wx-text-tertiary)', letterSpacing: 1.5,
              fontWeight: 700, display: 'block', marginBottom: 4,
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

      {/* 「+ 新对话」 + 「+ 新建分组」 */}
      {p.authed && (
        <>
          <button type="button" className="wx-new-btn" onClick={p.onNewChat}>
            <Plus size={14} />
            {t('landing.new_sandbox')}
          </button>
          {creatingGroup ? (
            <input
              className="wx-input"
              style={{ fontSize: 12.5, padding: '8px 10px', marginBottom: 6 }}
              autoFocus
              value={newGroupName}
              placeholder={t('sandbox.group_name_ph')}
              onChange={(e) => setNewGroupName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') submitNewGroup()
                if (e.key === 'Escape') { setCreatingGroup(false); setNewGroupName('') }
              }}
              onBlur={submitNewGroup}
            />
          ) : (
            <button
              type="button"
              className="wx-newgroup-btn"
              onClick={() => setCreatingGroup(true)}
            >
              <FolderPlus size={14} />
              {t('sandbox.group_new')}
            </button>
          )}
        </>
      )}

      {/* Scroll area: groups + ungrouped tasks */}
      {p.authed && (
        <div className="wx-sb-scroll">
          {/* Groups */}
          {p.groups.map((g) => {
            const open = !collapsedGroups.has(g.group_id)
            const children = p.sandboxes.filter((s) => s.group_id === g.group_id)
            return (
              <div key={g.group_id} className="wx-group">
                <div className="wx-group-head">
                  <button
                    type="button"
                    className="wx-group-toggle"
                    onClick={() => toggleGroup(g.group_id)}
                  >
                    {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                    <span className="wx-group-name">{g.name}</span>
                    <span className="wx-group-count">{children.length}</span>
                  </button>
                  <button
                    type="button"
                    className="wx-group-more"
                    title={t('common.more') || '更多'}
                    onClick={(e) => {
                      e.stopPropagation()
                      setTaskMenu(null)
                      setGroupMenu(groupMenu === g.group_id ? null : g.group_id)
                    }}
                  >
                    <MoreHorizontal size={14} />
                  </button>
                  {groupMenu === g.group_id && (
                    <div className="wx-pop-menu" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        className="wx-pop-item"
                        onClick={() => {
                          const name = window.prompt(t('sandbox.group_rename'), g.name)
                          if (name && name.trim()) p.onRenameGroup(g, name.trim())
                          setGroupMenu(null)
                        }}
                      >
                        {t('sandbox.group_rename')}
                      </button>
                      <button
                        type="button"
                        className="wx-pop-item danger"
                        onClick={() => { p.onDeleteGroup(g); setGroupMenu(null) }}
                      >
                        <Trash2 size={13} /> {t('sandbox.group_delete')}
                      </button>
                    </div>
                  )}
                </div>
                {open && (
                  <div className="wx-group-children">
                    {children.length === 0 ? (
                      <div className="wx-group-empty">{t('sandbox.group_empty')}</div>
                    ) : (
                      children.map(renderSandbox)
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {/* Ungrouped */}
          <div className="wx-sb-label">{t('landing.sandbox_label')}</div>
          {ungrouped.length === 0 ? (
            <div className="wx-sb-empty-state">
              <p style={{ fontSize: 12, color: 'var(--wx-text-tertiary)',
                          padding: '12px', lineHeight: 1.5 }}>
                {t('landing.no_sandboxes')}
              </p>
            </div>
          ) : (
            ungrouped.map(renderSandbox)
          )}
        </div>
      )}

      {/* Spacer for anon */}
      {!p.authed && <div style={{ flex: 1 }} />}

      {/* Bottom: user pill → popup menu (authed) | auth CTAs (anon) */}
      <div className="wx-sb-bottom" ref={bottomRef}>
        {p.authed ? (
          <div style={{ position: 'relative' }}>
            {userMenuOpen && (
              <div className="wx-user-menu" onClick={(e) => e.stopPropagation()}>
                {NAV_ITEMS.map((item) => {
                  const Icon = item.icon
                  return (
                    <button
                      key={item.key}
                      type="button"
                      className="wx-user-menu-item"
                      onClick={() => {
                        p.onSelectView(item.key, item.requiresAuth)
                        setUserMenuOpen(false)
                      }}
                    >
                      <Icon size={15} />
                      <span>{t(item.labelKey)}</span>
                    </button>
                  )
                })}
                {p.user?.is_super_admin && (
                  <a className="wx-user-menu-item" href="/admin"
                     style={{ color: 'var(--wx-accent-cyan)' }}>
                    <Shield size={15} />
                    <span>{t('nav.admin')}</span>
                  </a>
                )}
                <div className="wx-pop-sep" />
                <button
                  type="button"
                  className="wx-user-menu-item danger"
                  onClick={() => {
                    clearTokens()
                    logout()
                    window.location.assign('/')
                  }}
                >
                  <LogOut size={15} />
                  <span>{t('auth.logout')}</span>
                </button>
              </div>
            )}
            <button
              type="button"
              className="wx-usr"
              onClick={(e) => { e.stopPropagation(); setUserMenuOpen((v) => !v) }}
            >
              <span className="wx-usr-av" aria-hidden="true">
                {(p.user?.display_name || '?').slice(0, 1)}
              </span>
              <span style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                <b style={{ display: 'block', fontSize: 12.5, lineHeight: 1.3,
                            whiteSpace: 'nowrap', overflow: 'hidden',
                            textOverflow: 'ellipsis' }}>
                  {p.user?.display_name || '…'}
                </b>
                <small style={{ fontSize: 10.5, color: 'var(--wx-text-tertiary)',
                                whiteSpace: 'nowrap', overflow: 'hidden',
                                textOverflow: 'ellipsis', display: 'block' }}>
                  {p.currentWs?.name || ''}
                </small>
              </span>
              {userMenuOpen ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
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
