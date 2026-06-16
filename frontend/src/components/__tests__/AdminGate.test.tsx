// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AdminGate } from '@/components/layout/AdminGate'
import { useAuthStore } from '@/stores/authStore'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/admin"
          element={
            <AdminGate>
              <div>SECRET ADMIN AREA</div>
            </AdminGate>
          }
        />
        <Route path="/workspaces" element={<div>WORKSPACES PAGE</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminGate', () => {
  it('renders nothing while user is still null (RequireAuth fetch in flight)', () => {
    useAuthStore.setState({ user: null, workspaces: [], currentWorkspaceSlug: null })
    const { container } = renderAt('/admin')
    expect(container.textContent).toBe('')
  })

  it('redirects non super-admin users to /workspaces', () => {
    useAuthStore.setState({
      user: {
        user_id: 'u1',
        email: 'a@b.c',
        phone: null,
        display_name: 'A',
        locale: 'zh',
        email_verified: true,
        phone_verified: false,
        is_super_admin: false,
        avatar_url: null,
      },
      workspaces: [],
      currentWorkspaceSlug: null,
    })
    renderAt('/admin')
    expect(screen.getByText('WORKSPACES PAGE')).toBeInTheDocument()
    expect(screen.queryByText('SECRET ADMIN AREA')).toBeNull()
  })

  it('renders children for super-admin users', () => {
    useAuthStore.setState({
      user: {
        user_id: 'u1',
        email: 'a@b.c',
        phone: null,
        display_name: 'A',
        locale: 'zh',
        email_verified: true,
        phone_verified: false,
        is_super_admin: true,
        avatar_url: null,
      },
      workspaces: [],
      currentWorkspaceSlug: null,
    })
    renderAt('/admin')
    expect(screen.getByText('SECRET ADMIN AREA')).toBeInTheDocument()
  })
})
