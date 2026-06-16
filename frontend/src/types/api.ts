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

// P7: Reports / Billing / Members / API keys / Admin

export type TaskStatus = 'pending' | 'running' | 'done' | 'failed'

export interface SimulationTaskSummary {
  task_id: string
  status: TaskStatus
  created_at: string
  started_at: string | null
  finished_at: string | null
  result: SimulationResult | null
  error: string | null
}

export interface SimulationResult {
  decision_kind: string
  n_valid: number
  n_total: number
  scores?: number[]
  mean?: number
  top_choice?: { label?: string; share?: number } | null
  markdown?: string
  [key: string]: unknown
}

export interface WorkspaceBalance {
  workspace_id: string
  slug: string
  balance_cost_units: number
  monthly_budget: number | null
}

export type TxKind = 'topup' | 'usage' | 'refund' | 'adjust'

export interface Transaction {
  tx_id: string
  workspace_id: string
  kind: TxKind
  delta_cost_units: number
  balance_after: number
  note: string
  created_by_user_id: string | null
  related_task_id: string | null
  created_at: string
}

export interface UsageMonthly {
  total_cost_units: number
  by_mode: Record<string, number>
  by_status: Record<string, number>
  events: UsageEvent[]
  period?: { start: string; end: string }
}

export interface UsageEvent {
  event_id: string
  tenant_id: string
  task_id: string | null
  mode: string
  n_agents: number
  rounds: number
  decision_kind: string
  cost_units: number
  status: string
  recorded_at: string
}

export type MemberRole = 'owner' | 'admin' | 'member'

export interface Member {
  user_id: string
  email: string | null
  phone: string | null
  display_name: string
  avatar_url: string | null
  email_verified: boolean
  phone_verified: boolean
  is_super_admin: boolean
  role: MemberRole
  joined_at: string
}

export interface Invite {
  invite_id: string
  invited_email: string
  role: MemberRole
  expires_at: string
  accepted_at: string | null
}

export interface InviteCreateResponse {
  invite_id: string
  token: string
  expires_at: string
  invited_email: string
  role: MemberRole
}

export interface ApiKeyEntry {
  key_id: string
  name: string
  api_key_preview: string
  role: 'admin' | 'member'
  rpm_limit: number
  monthly_budget: number | null
  created_at: string
}

export interface ApiKeyCreated {
  key_id: string
  api_key: string
  name: string
  role: 'admin' | 'member'
  rpm_limit: number
  monthly_budget: number | null
  created_at: string
  warning: string
}

export interface AdminWorkspace {
  workspace_id: string
  slug: string
  name: string
  type: WorkspaceType
  owner_user_id: string
  balance_cost_units: number
  monthly_budget: number | null
  locale: string
  created_at?: string
}
