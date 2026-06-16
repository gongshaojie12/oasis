// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Zustand store for the active Sandbox + its chat messages.
// Replaces nothing; lives alongside authStore.
import { create } from 'zustand'
import type { ChatMessage, Sandbox } from '@/types/api'

interface SandboxState {
  currentSandbox: Sandbox | null
  sandboxes: Sandbox[]
  messages: ChatMessage[]
  isSending: boolean
  setSandboxes: (s: Sandbox[]) => void
  setCurrentSandbox: (s: Sandbox | null) => void
  setMessages: (m: ChatMessage[]) => void
  appendMessages: (m: ChatMessage[]) => void
  setSending: (v: boolean) => void
  reset: () => void
}

export const useSandboxStore = create<SandboxState>((set) => ({
  currentSandbox: null,
  sandboxes: [],
  messages: [],
  isSending: false,
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
  reset: () => set({
    currentSandbox: null,
    messages: [],
    isSending: false,
  }),
}))
