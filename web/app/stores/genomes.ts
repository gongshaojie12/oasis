import { defineStore } from 'pinia'

export interface GenomeItem {
  id: string
  name: string
  sourceType: string
  genomeData: any
  tags: string[]
  createdAt: string
  updatedAt: string
}

interface Pagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

interface GenomesState {
  items: GenomeItem[]
  pagination: Pagination
  loading: boolean
  currentGenome: GenomeItem | null
}

export const useGenomesStore = defineStore('genomes', {
  state: (): GenomesState => ({
    items: [],
    pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
    loading: false,
    currentGenome: null,
  }),

  actions: {
    async fetchList(params: { page?: number; pageSize?: number; sourceType?: string } = {}) {
      this.loading = true
      try {
        const { $api } = useApi()
        const query = new URLSearchParams()
        if (params.page) query.set('page', String(params.page))
        if (params.pageSize) query.set('pageSize', String(params.pageSize))
        if (params.sourceType) query.set('sourceType', params.sourceType)
        const res = await $api<any>(`/api/genomes?${query.toString()}`)
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
      const res = await $api<any>(`/api/genomes/${id}`)
      if (res.code === 0) {
        this.currentGenome = res.data
      }
      return res
    },

    async create(data: { name: string; sourceType: string; genomeData: any; tags?: string[] }) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes', { method: 'POST', body: data })
    },

    async update(id: string, data: { name?: string; genomeData?: any; tags?: string[] }) {
      const { $api } = useApi()
      return await $api<any>(`/api/genomes/${id}`, { method: 'PUT', body: data })
    },

    async remove(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/genomes/${id}`, { method: 'DELETE' })
    },

    async extract(data: { sourceType: string; content?: string; structuredData?: any }) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/extract', { method: 'POST', body: data })
    },

    async breed(data: { name: string; seedGenomeIds: string[]; targetCount: number; mutationRate?: number; strategy?: string }) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/breed', { method: 'POST', body: data })
    },

    async preview(genomes: any[]) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/preview', { method: 'POST', body: { genomes } })
    },

    async toProfiles(genomeIds: string[], platform: string = 'twitter') {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/to-profiles', { method: 'POST', body: { genomeIds, platform } })
    },
  },
})
