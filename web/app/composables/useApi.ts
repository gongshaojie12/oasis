export function useApi() {
  const authStore = useAuthStore()

  async function $api<T = any>(url: string, options: any = {}): Promise<T> {
    const headers: Record<string, string> = { ...options.headers }

    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await $fetch(url, {
      ...options,
      headers,
    })

    return response as T
  }

  return { $api }
}
