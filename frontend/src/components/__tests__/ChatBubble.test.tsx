// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatBubble } from '../chat/ChatBubble'
import { switchLang } from '@/lib/i18n'
import { useAuthStore } from '@/stores/authStore'
import type { ChatMessage } from '@/types/api'

function mkMsg(over: Partial<ChatMessage> = {}): ChatMessage {
  return {
    message_id: 'm1', sandbox_id: 's1',
    role: 'user', content: 'hello',
    kind: 'text', metadata: {}, user_id: 'u1',
    created_at: new Date().toISOString(),
    ...over,
  }
}

beforeEach(() => {
  switchLang('zh')
  useAuthStore.setState({
    user: {
      user_id: 'u1', email: 'a@x.com', phone: null,
      display_name: '小明', locale: 'zh',
      email_verified: true, phone_verified: false,
      is_super_admin: false, avatar_url: null,
    },
    workspaces: [], currentWorkspaceSlug: null,
  })
})

describe('ChatBubble', () => {
  it('renders user message with the user initial', () => {
    render(<ChatBubble msg={mkMsg({ content: 'hi' })} />)
    expect(screen.getByText('hi')).toBeInTheDocument()
    expect(screen.getByText('小')).toBeInTheDocument()
  })

  it('renders assistant text via markdown', () => {
    render(<ChatBubble msg={mkMsg({
      role: 'assistant', content: '**bold** text', user_id: null,
    })} />)
    expect(screen.getByText('bold')).toBeInTheDocument()
  })

  it('renders a report_card with decision stats', () => {
    render(<ChatBubble msg={mkMsg({
      role: 'assistant',
      content: '# Report\n\nDetails',
      kind: 'report_card',
      user_id: null,
      metadata: { decision_kind: 'rate', n_valid: 18, n_total: 20, mean: 7.42 },
    })} />)
    expect(screen.getByText('rate')).toBeInTheDocument()
    expect(screen.getByText(/18/)).toBeInTheDocument()
    expect(screen.getByText('7.42')).toBeInTheDocument()
  })
})
