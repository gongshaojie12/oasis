// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Zustand store for the active Sandbox + its chat messages.
// Replaces nothing; lives alongside authStore.
import { create } from 'zustand'
import type {
  ChatMessage, Sandbox, SimProgress, FeedItem,
} from '@/types/api'

// 决策动态 feed 封顶条数(只渲染最新 N 条,prepend)。
const FEED_CAP = 30

interface SandboxState {
  currentSandbox: Sandbox | null
  sandboxes: Sandbox[]
  messages: ChatMessage[]
  isSending: boolean
  liveProgress: SimProgress | null
  feedItems: FeedItem[]
  setSandboxes: (s: Sandbox[]) => void
  setCurrentSandbox: (s: Sandbox | null) => void
  setMessages: (m: ChatMessage[]) => void
  appendMessages: (m: ChatMessage[]) => void
  setSending: (v: boolean) => void
  setLiveProgress: (p: SimProgress | null) => void
  pushFeedItem: (f: Omit<FeedItem, 'id'>) => void
  clearFeed: () => void
  reset: () => void
}

export const useSandboxStore = create<SandboxState>((set) => ({
  currentSandbox: null,
  sandboxes: [],
  messages: [],
  isSending: false,
  liveProgress: null,
  feedItems: [],
  setSandboxes: (sandboxes) => set({ sandboxes }),
  setCurrentSandbox: (currentSandbox) => set({ currentSandbox }),
  setMessages: (messages) => set({ messages }),
  appendMessages: (m) =>
    set((s) => {
      const ids = new Set(s.messages.map((x) => x.message_id))
      const fresh = m.filter((x) => !ids.has(x.message_id))
      return { messages: [...s.messages, ...fresh] }
    }),
  setSending: (isSending) => set({ isSending }),
  setLiveProgress: (liveProgress) => set({ liveProgress }),
  pushFeedItem: (f) =>
    set((s) => {
      // id 唯一即可:agent_id + 累计序号 + 时间戳。social 多轮同 agent 会重复,
      // 故不能只用 agent_id 当 key。
      const id = `${f.agent_id}-${s.feedItems.length}-${Date.now()}`
      return { feedItems: [{ ...f, id }, ...s.feedItems].slice(0, FEED_CAP) }
    }),
  clearFeed: () => set({ feedItems: [] }),
  reset: () => set({
    currentSandbox: null,
    messages: [],
    isSending: false,
    liveProgress: null,
    feedItems: [],
  }),
}))
