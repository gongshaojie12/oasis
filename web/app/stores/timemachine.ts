import { defineStore } from 'pinia'

export interface SnapshotSummary {
  round_number: number
  metrics: {
    total_actions: number
    total_posts_this_round: number
    action_distribution: Record<string, number>
  }
  agent_summaries: {
    agent_id: number
    user_name: string
    action_count: number
    recent_actions: string[]
  }[]
  posts: any[]
}

export const useTimeMachineStore = defineStore('timeMachine', {
  state: () => ({
    snapshots: [] as SnapshotSummary[],
    currentRound: 1,
    currentSnapshot: null as SnapshotSummary | null,
    chatMessages: [] as any[],
    conversationId: null as string | null,
    roundtableMessages: [] as any[],
    replayData: null as any,
    loading: false,
    chatLoading: false,
  }),

  actions: {
    async fetchSnapshots(simId: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/snapshots`)
        if (res.code === 0) {
          this.snapshots = res.data || []
          if (this.snapshots.length > 0) {
            this.currentRound = 1
            this.currentSnapshot = this.snapshots[0]
          }
        }
        return res
      } finally {
        this.loading = false
      }
    },

    async fetchRoundSnapshot(simId: string, round: number) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/snapshots/${round}`)
        if (res.code === 0) {
          this.currentRound = round
          this.currentSnapshot = res.data
        }
        return res
      } finally {
        this.loading = false
      }
    },

    async sendChat(simId: string, agentId: number, roundContext: number, message: string) {
      this.chatLoading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/chat`, {
          method: 'POST',
          body: {
            agentId,
            roundContext,
            message,
            conversationId: this.conversationId,
            history: this.chatMessages,
          },
        })
        if (res.code === 0) {
          this.conversationId = res.data.conversationId
          this.chatMessages.push(
            { role: 'user', content: message },
            { role: 'agent', content: res.data.response, agent_id: res.data.agent_id, agent_name: res.data.agent_name },
          )
        }
        return res
      } finally {
        this.chatLoading = false
      }
    },

    async startRoundtable(simId: string, agentIds: number[], roundContext: number, topic: string, numRounds: number = 3) {
      this.chatLoading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/roundtable`, {
          method: 'POST',
          body: { agentIds, roundContext, topic, numRounds },
        })
        if (res.code === 0) {
          this.roundtableMessages = res.data.messages || []
        }
        return res
      } finally {
        this.chatLoading = false
      }
    },

    async fetchReplay(simId: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/replay`)
        if (res.code === 0) {
          this.replayData = res.data
        }
        return res
      } finally {
        this.loading = false
      }
    },

    clearChat() {
      this.chatMessages = []
      this.conversationId = null
    },

    setRound(round: number) {
      this.currentRound = round
      const snap = this.snapshots.find(s => s.round_number === round)
      if (snap) this.currentSnapshot = snap
    },
  },
})
