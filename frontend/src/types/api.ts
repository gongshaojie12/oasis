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
