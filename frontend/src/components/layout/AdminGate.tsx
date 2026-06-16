// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Wraps super-admin only routes. RequireAuth handles unauthenticated users;
// here we only need to redirect logged-in non-admins back to /workspaces.
import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuthStore } from '@/stores/authStore'

interface Props {
  children: ReactNode
}

export function AdminGate({ children }: Props) {
  const user = useAuthStore((s) => s.user)
  // While /me is in flight RequireAuth keeps user null. Render nothing
  // until we know whether super-admin or not (prevents a redirect flicker).
  if (!user) return null
  if (!user.is_super_admin) {
    return <Navigate to="/workspaces" replace />
  }
  return <>{children}</>
}
