import { defineStore } from 'pinia'

export interface GraphSummary {
  id: string
  name: string
  description: string | null
  nodeCount: number
  edgeCount: number
  createdAt: string
  updatedAt: string
}

export interface GraphDetail extends GraphSummary {
  graphData: { nodes: any[]; edges: any[] }
  metadata: any
}

export const useWorldBuilderStore = defineStore('worldBuilder', {
  state: () => ({
    items: [] as GraphSummary[],
    current: null as GraphDetail | null,
    loading: false,
  }),

  actions: {
    async fetchList() {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/world-builder')
        if (res.code === 0) this.items = res.data
        return res
      } finally {
        this.loading = false
      }
    },

    async fetchOne(id: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/world-builder/${id}`)
        if (res.code === 0) this.current = res.data
        return res
      } finally {
        this.loading = false
      }
    },

    async create(name: string, description?: string) {
      const { $api } = useApi()
      return await $api<any>('/api/world-builder', {
        method: 'POST',
        body: { name, description },
      })
    },

    async update(id: string, data: any) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}`, {
        method: 'PUT',
        body: data,
      })
    },

    async remove(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}`, { method: 'DELETE' })
    },

    async analyze(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}/analyze`, { method: 'POST' })
    },

    async toSimulation(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}/to-simulation`, { method: 'POST' })
    },

    async importGraph(name: string, graphData: any) {
      const { $api } = useApi()
      return await $api<any>('/api/world-builder/import', {
        method: 'POST',
        body: { name, graphData },
      })
    },
  },
})
