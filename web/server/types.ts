import type { TokenPayload } from '~~/server/utils/jwt'

declare module 'h3' {
  interface H3EventContext {
    user: TokenPayload | null
    enterprise: {
      id: string
      name: string
      planType: string
      simQuota: number
      quotaExpires: string | null
    } | null
  }
}
