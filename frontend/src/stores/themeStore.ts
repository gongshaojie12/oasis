// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Zustand store mirroring the persisted theme. `toggle` flips light <-> dark
// and writes the new value to localStorage + the <html data-theme> attr in
// one shot (so CSS custom properties switch with no re-render lag).
import { create } from 'zustand'
import { applyTheme, getInitialTheme, type Theme } from '@/lib/theme'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggle: () => void
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: getInitialTheme(),
  setTheme: (theme) => {
    applyTheme(theme)
    set({ theme })
  },
  toggle: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light'
    applyTheme(next)
    set({ theme: next })
  },
}))
