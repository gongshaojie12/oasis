import { defineStore } from 'pinia'

export interface AgentGroup {
  name: string
  ratio: number
  stance_range: number[]
}

export interface EventInjection {
  round: number
  content: string
}

export interface ScenarioDNA {
  conflict_level: number
  information_density: number
  viral_potential: number
  sentiment_polarity: number
  temporal_dynamics: string
  agent_diversity: number
  platform_fit: string[]
}

export interface ScenarioConfig {
  platform: string
  num_agents: number
  num_steps: number
  seed_content: string
  agent_groups: AgentGroup[]
  event_injections: EventInjection[]
  available_actions: string[]
  dna: ScenarioDNA | null
  description: string
}

export interface ResourceEstimate {
  llm_calls: number
  estimated_tokens: number
  estimated_minutes: number
  estimated_cost_usd: number
}

interface ComposerState {
  config: ScenarioConfig | null
  estimate: ResourceEstimate | null
  templates: ScenarioConfig[]
  parsing: boolean
  mixing: boolean
  estimating: boolean
}

export const useComposerStore = defineStore('composer', {
  state: (): ComposerState => ({
    config: null,
    estimate: null,
    templates: [],
    parsing: false,
    mixing: false,
    estimating: false,
  }),

  actions: {
    async parse(description: string) {
      this.parsing = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/composer/parse', { method: 'POST', body: { description } })
        if (res.code === 0) {
          this.config = res.data
          return res.data
        }
        throw new Error(res.message)
      } finally {
        this.parsing = false
      }
    },

    async mix(dna_a: ScenarioDNA, dna_b: ScenarioDNA, weight_a: number = 0.5) {
      this.mixing = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/composer/mix', { method: 'POST', body: { dna_a, dna_b, weight_a } })
        if (res.code === 0) {
          this.config = res.data
          return res.data
        }
        throw new Error(res.message)
      } finally {
        this.mixing = false
      }
    },

    async fetchTemplates(platform?: string) {
      try {
        const { $api } = useApi()
        const query = platform ? `?platform=${platform}` : ''
        const res = await $api<any>(`/api/composer/recommend${query}`)
        if (res.code === 0) {
          this.templates = res.data
        }
      } catch {}
    },

    async fetchEstimate(config: ScenarioConfig) {
      this.estimating = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/composer/estimate', { method: 'POST', body: { config } })
        if (res.code === 0) {
          this.estimate = res.data
          return res.data
        }
        throw new Error(res.message)
      } finally {
        this.estimating = false
      }
    },

    updateConfig(partial: Partial<ScenarioConfig>) {
      if (this.config) {
        Object.assign(this.config, partial)
      }
    },

    reset() {
      this.config = null
      this.estimate = null
      this.parsing = false
      this.mixing = false
      this.estimating = false
    },
  },
})
