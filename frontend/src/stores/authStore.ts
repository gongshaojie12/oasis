// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { create } from 'zustand'
import type { User, Workspace } from '@/types/api'

interface AuthState {
  user: User | null
  workspaces: Workspace[]
  currentWorkspaceSlug: string | null
  setUser: (user: User | null) => void
  setWorkspaces: (ws: Workspace[]) => void
  setCurrentWorkspace: (slug: string) => void
  logout: () => void
}

const CURRENT_WS_KEY = 'wanxiang.current_ws'

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  workspaces: [],
  currentWorkspaceSlug: localStorage.getItem(CURRENT_WS_KEY),
  setUser: (user) => set({ user }),
  setWorkspaces: (workspaces) => set({ workspaces }),
  setCurrentWorkspace: (slug) => {
    localStorage.setItem(CURRENT_WS_KEY, slug)
    set({ currentWorkspaceSlug: slug })
  },
  logout: () => {
    localStorage.removeItem(CURRENT_WS_KEY)
    set({ user: null, workspaces: [], currentWorkspaceSlug: null })
  },
}))
