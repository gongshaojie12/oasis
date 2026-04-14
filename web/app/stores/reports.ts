import { defineStore } from 'pinia'

export interface Report {
  id: string
  simulationId: string
  title: string
  summary: string | null
  dashboardData: any
  pdfUrl: string | null
  rawDataUrl: string | null
  createdAt: string
  simulation?: any
}

interface ReportsState {
  items: Report[]
  pagination: { page: number; pageSize: number; total: number; totalPages: number }
  loading: boolean
  currentReport: Report | null
}

export const useReportsStore = defineStore('reports', {
  state: (): ReportsState => ({
    items: [],
    pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
    loading: false,
    currentReport: null,
  }),

  actions: {
    async fetchList(params: { page?: number; pageSize?: number } = {}) {
      this.loading = true
      try {
        const { $api } = useApi()
        const query = new URLSearchParams()
        if (params.page) query.set('page', String(params.page))
        if (params.pageSize) query.set('pageSize', String(params.pageSize))

        const res = await $api<any>(`/api/reports?${query.toString()}`)
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
      const res = await $api<any>(`/api/reports/${id}`)
      if (res.code === 0) {
        this.currentReport = res.data
      }
      return res
    },
  },
})
