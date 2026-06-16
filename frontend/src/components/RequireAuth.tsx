// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { Navigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { isAuthenticated } from '@/lib/auth'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/lib/api'
import type { MeResponse } from '@/types/api'

interface Props {
  children: ReactNode
}

export function RequireAuth({ children }: Props) {
  const loc = useLocation()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const setWorkspaces = useAuthStore((s) => s.setWorkspaces)
  const setCurrentWorkspace = useAuthStore((s) => s.setCurrentWorkspace)
  const currentWs = useAuthStore((s) => s.currentWorkspaceSlug)

  useEffect(() => {
    if (isAuthenticated() && !user) {
      api.get<MeResponse>('/me')
        .then((r) => {
          setUser(r.data.user)
          setWorkspaces(r.data.workspaces)
          if (!currentWs && r.data.workspaces[0]) {
            setCurrentWorkspace(r.data.workspaces[0].slug)
          }
        })
        .catch(() => {
          /* axios interceptor will redirect on 401 */
        })
    }
  }, [user, currentWs, setUser, setWorkspaces, setCurrentWorkspace])

  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: loc.pathname }} replace />
  }
  return <>{children}</>
}
