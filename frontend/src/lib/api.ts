// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Axios instance for the WANXIANG backend.
//
// - Bearer token auto-attached from localStorage.
// - Accept-Language header forwarded so backend i18n.py picks zh/en.
// - 401 triggers a single-flight refresh attempt; if refresh fails the
//   user is redirected to /login.
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { getTokens, setTokens, clearTokens } from './auth'

const BASE_URL = '/v1'

export const api: AxiosInstance = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const { access } = getTokens()
  if (access) config.headers.Authorization = `Bearer ${access}`
  const lang = localStorage.getItem('wanxiang.lang') || 'zh'
  config.headers['Accept-Language'] = lang
  return config
})

// Single-flight refresh so concurrent 401s only trigger one /auth/refresh.
let refreshing: Promise<string | null> | null = null

async function refreshAccess(): Promise<string | null> {
  if (refreshing) return refreshing
  refreshing = (async () => {
    const { refresh } = getTokens()
    if (!refresh) return null
    try {
      const r = await axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refresh })
      setTokens({ access: r.data.access_token, refresh: r.data.refresh_token })
      return r.data.access_token as string
    } catch {
      clearTokens()
      return null
    } finally {
      // Reset the lock after a short tick so the next 401 can refresh again.
      setTimeout(() => { refreshing = null }, 100)
    }
  })()
  return refreshing
}

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean }

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as RetryConfig | undefined
    if (err.response?.status === 401 && original && !original._retry) {
      original._retry = true
      const newAccess = await refreshAccess()
      if (newAccess) {
        original.headers.Authorization = `Bearer ${newAccess}`
        return api(original)
      }
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)
