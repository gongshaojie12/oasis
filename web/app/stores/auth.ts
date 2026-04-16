import { defineStore } from 'pinia'

interface User {
  id: string
  phone: string
  name: string | null
  role: string
}

interface Enterprise {
  id: string
  name: string
  planType: string
  simQuota: number
  quotaExpires?: string | null
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  enterprise: Enterprise | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: null,
    refreshToken: null,
    user: null,
    enterprise: null,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
  },

  actions: {
    setAuth(data: {
      token: string
      refreshToken: string
      user: User
      enterprise: Enterprise | null
    }) {
      this.token = data.token
      this.refreshToken = data.refreshToken
      this.user = data.user
      this.enterprise = data.enterprise
    },

    logout() {
      this.token = null
      this.refreshToken = null
      this.user = null
      this.enterprise = null
    },

    async fetchMe() {
      if (!this.token) return

      try {
        const res = await $fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${this.token}` },
        })
        const data = (res as any).data
        if (data) {
          this.user = data.user
          this.enterprise = data.enterprise
        }
      } catch {
        this.logout()
      }
    },
  },

  persist: {
    storage: piniaPluginPersistedstate.localStorage(),
  },
})
