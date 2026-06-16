// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Token storage helpers — localStorage-backed. Keep keys stable; the axios
// interceptor in lib/api.ts and the auth store both read these.

const ACCESS_KEY = 'wanxiang.access_token'
const REFRESH_KEY = 'wanxiang.refresh_token'

export function getTokens() {
  return {
    access: localStorage.getItem(ACCESS_KEY),
    refresh: localStorage.getItem(REFRESH_KEY),
  }
}

export function setTokens({ access, refresh }: { access: string; refresh: string }) {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function isAuthenticated(): boolean {
  return !!getTokens().access
}
