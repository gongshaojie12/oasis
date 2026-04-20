import { defineStore } from 'pinia'

export interface AnalysisReport {
  id: string
  simulationId: string
  status: string
  analystReports: any
  debateLog: any[]
  finalReport: any
  chartData: any
  timelineData: any[]
  createdAt: string
  completedAt: string | null
}

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    currentReport: null as AnalysisReport | null,
    loading: false,
  }),

  actions: {
    async generate(simulationId: string, debateRounds: number = 2) {
      const { $api } = useApi()
      return await $api<any>('/api/analysis/generate', {
        method: 'POST',
        body: { simulationId, debateRounds },
      })
    },

    async fetchOne(id: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/analysis/${id}`)
        if (res.code === 0) this.currentReport = res.data
        return res
      } finally {
        this.loading = false
      }
    },

    async fetchStatus(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/status`)
    },

    async fetchTimeline(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/timeline`)
    },

    async fetchCharts(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/charts`)
    },

    async fetchDebate(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/debate`)
    },

    async compare(reportIds: string[]) {
      const { $api } = useApi()
      return await $api<any>('/api/analysis/compare', {
        method: 'POST',
        body: { reportIds },
      })
    },
  },
})
