import { defineStore } from 'pinia'

export interface Simulation {
  id: string
  name: string
  type: string
  platform: string
  status: string
  progress: number
  agentCount: number | null
  timeSteps: number | null
  llmModel: string | null
  errorMessage: string | null
  createdAt: string
  startedAt: string | null
  completedAt: string | null
}

interface Pagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

interface SimulationsState {
  items: Simulation[]
  pagination: Pagination
  loading: boolean
  currentSimulation: Simulation | null
}

export const useSimulationsStore = defineStore('simulations', {
  state: (): SimulationsState => ({
    items: [],
    pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
    loading: false,
    currentSimulation: null,
  }),

  actions: {
    async fetchList(params: {
      page?: number
      pageSize?: number
      status?: string
      type?: string
      platform?: string
    } = {}) {
      this.loading = true
      try {
        const { $api } = useApi()
        const query = new URLSearchParams()
        if (params.page) query.set('page', String(params.page))
        if (params.pageSize) query.set('pageSize', String(params.pageSize))
        if (params.status) query.set('status', params.status)
        if (params.type) query.set('type', params.type)
        if (params.platform) query.set('platform', params.platform)

        const res = await $api<any>(`/api/simulations?${query.toString()}`)
        if (res.code === 0) {
          this.items = res.data.items
          this.pagination = res.data.pagination
        }
      } finally {
        this.loading = false
      }
    },

    async fetchOne(id: string) {
      const { $api } = useApi()
      const res = await $api<any>(`/api/simulations/${id}`)
      if (res.code === 0) {
        this.currentSimulation = res.data
      }
      return res
    },

    async create(data: Record<string, any>) {
      const { $api } = useApi()
      return await $api<any>('/api/simulations', {
        method: 'POST',
        body: data,
      })
    },

    async cancel(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/simulations/${id}/cancel`, { method: 'POST' })
    },

    async retry(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/simulations/${id}/retry`, { method: 'POST' })
    },
  },
})
