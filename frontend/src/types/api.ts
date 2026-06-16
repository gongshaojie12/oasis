// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Shared API types — keep in sync with wanxiang.api.routes.* response shapes.

export interface User {
  user_id: string
  email: string | null
  phone: string | null
  display_name: string
  locale: string
  email_verified: boolean
  phone_verified: boolean
  is_super_admin: boolean
  avatar_url: string | null
}

export type WorkspaceType = 'personal' | 'team'

export interface Workspace {
  workspace_id: string
  slug: string
  name: string
  type: WorkspaceType
  balance_cost_units: number
  locale: string
}

export interface BrandConfig {
  name: { zh: string; en: string }
  short: string
  avatar: { zh: string; en: string }
  tagline: { zh: string; en: string }
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginResponse extends TokenPair {
  user: User
  workspaces: Workspace[]
}

export interface RegisterResponse extends TokenPair {
  user: User
  default_workspace: Workspace
}

export interface MeResponse {
  user: User
  workspaces: Workspace[]
}

// P6: Sandbox + Chat
export interface Sandbox {
  sandbox_id: string
  workspace_id: string
  name: string
  emoji: string
  description: string
  distribution_path: string
  population_size: number
  created_by_user_id: string | null
  created_at: string
  last_active_at: string
  archived: boolean
}

export type ChatMessageKind =
  | 'text'
  | 'intent_parsed'
  | 'simulation_started'
  | 'simulation_progress'
  | 'simulation_done'
  | 'report_card'
  | 'error'

export type ChatMessageRole = 'user' | 'assistant' | 'system'

export interface ChatMessage {
  message_id: string
  sandbox_id: string
  role: ChatMessageRole
  content: string
  kind: ChatMessageKind
  metadata: Record<string, unknown>
  user_id: string | null
  created_at: string
}

export interface ChatSimulateResponse {
  user_message: ChatMessage
  assistant_messages: ChatMessage[]
  needs_clarification?: boolean
  missing?: string[]
  error?: string
  report?: Record<string, unknown>
}
