// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it, beforeEach } from 'vitest'
import { useSandboxStore } from '../sandboxStore'
import type { ChatMessage, Sandbox } from '@/types/api'

function mkSandbox(id = 's1'): Sandbox {
  return {
    sandbox_id: id, workspace_id: 'w1',
    name: 'Box', emoji: '🥤', description: '',
    distribution_path: 'x.yaml', population_size: 100,
    created_by_user_id: null,
    created_at: new Date().toISOString(),
    last_active_at: new Date().toISOString(),
    archived: false,
    group_id: null,
  }
}

function mkMsg(id: string, content = 'hi'): ChatMessage {
  return {
    message_id: id, sandbox_id: 's1', role: 'user', content,
    kind: 'text', metadata: {}, user_id: null,
    created_at: new Date().toISOString(),
  }
}

describe('sandboxStore', () => {
  beforeEach(() => {
    useSandboxStore.getState().reset()
    useSandboxStore.getState().setSandboxes([])
    useSandboxStore.getState().setMessages([])
  })

  it('appendMessages dedupes by message_id', () => {
    const store = useSandboxStore.getState()
    store.setMessages([mkMsg('a'), mkMsg('b')])
    store.appendMessages([mkMsg('b'), mkMsg('c')])
    const ids = useSandboxStore.getState().messages.map((m) => m.message_id)
    expect(ids).toEqual(['a', 'b', 'c'])
  })

  it('setCurrentSandbox stores the sandbox', () => {
    const sb = mkSandbox('xyz')
    useSandboxStore.getState().setCurrentSandbox(sb)
    expect(useSandboxStore.getState().currentSandbox?.sandbox_id).toBe('xyz')
  })

  it('reset clears current sandbox + sending flag but keeps list intact', () => {
    useSandboxStore.getState().setSandboxes([mkSandbox()])
    useSandboxStore.getState().setCurrentSandbox(mkSandbox())
    useSandboxStore.getState().setSending(true)
    useSandboxStore.getState().reset()
    const s = useSandboxStore.getState()
    expect(s.currentSandbox).toBeNull()
    expect(s.isSending).toBe(false)
    // reset() doesn't touch the workspace-level sandboxes list
    expect(s.sandboxes.length).toBe(1)
  })
})
