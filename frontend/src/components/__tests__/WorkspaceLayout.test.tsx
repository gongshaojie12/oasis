// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout'
import { useAuthStore } from '@/stores/authStore'
import { switchLang } from '@/lib/i18n'

function renderLayout(opts: { superAdmin: boolean }) {
  useAuthStore.setState({
    user: {
      user_id: 'u1',
      email: 'a@b.c',
      phone: null,
      display_name: 'Alice',
      locale: 'zh',
      email_verified: true,
      phone_verified: false,
      is_super_admin: opts.superAdmin,
      avatar_url: null,
    },
    workspaces: [
      {
        workspace_id: 'w1',
        slug: 'acme',
        name: 'Acme Inc',
        type: 'team',
        balance_cost_units: 1234,
        locale: 'zh',
      },
    ],
    currentWorkspaceSlug: 'acme',
  })
  switchLang('zh')
  return render(
    <MemoryRouter initialEntries={['/w/acme']}>
      <Routes>
        <Route path="/w/:slug" element={<WorkspaceLayout />}>
          <Route index element={<div>HOME</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('WorkspaceLayout', () => {
  it('shows all 6 default nav items + workspace name + balance', () => {
    renderLayout({ superAdmin: false })
    expect(screen.getByText('Acme Inc')).toBeInTheDocument()
    expect(screen.getByText(/1,?234/)).toBeInTheDocument()
    // 7 sidebar entries: dashboard / reports / billing / members / api-keys / settings / sandboxes
    expect(screen.getByText('仪表盘')).toBeInTheDocument()
    expect(screen.getByText('报告')).toBeInTheDocument()
    expect(screen.getByText('账单')).toBeInTheDocument()
    expect(screen.getByText('成员')).toBeInTheDocument()
    expect(screen.getByText('API Keys')).toBeInTheDocument()
    expect(screen.getByText('设置')).toBeInTheDocument()
    expect(screen.getByText('模拟沙盒')).toBeInTheDocument()
    expect(screen.queryByText('管理后台')).toBeNull()
  })

  it('shows admin link when user.is_super_admin', () => {
    renderLayout({ superAdmin: true })
    expect(screen.getByText('管理后台')).toBeInTheDocument()
  })
})
