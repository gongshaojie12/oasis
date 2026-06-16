// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Theme bootstrap. Light is the default (per design preference + ChatGPT
// reference). User choice persists in localStorage; we explicitly do NOT
// follow prefers-color-scheme so the default surface stays consistent.
export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'wanxiang.theme'

export function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light'
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    /* private mode / quota */
  }
  return 'light'
}

export function applyTheme(theme: Theme): void {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.style.colorScheme = theme
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    /* private mode / quota */
  }
}

export function toggleTheme(): Theme {
  const current = (typeof document !== 'undefined'
    ? (document.documentElement.getAttribute('data-theme') as Theme | null)
    : null) ?? 'light'
  const next: Theme = current === 'light' ? 'dark' : 'light'
  applyTheme(next)
  return next
}
