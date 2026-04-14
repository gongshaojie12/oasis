import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { enterprises } from '~~/server/database/schema'

export default defineEventHandler(async (event) => {
  const path = getRequestURL(event).pathname

  // Only apply to authenticated API routes
  if (!path.startsWith('/api/') || !event.context.user) return

  const db = useDB()
  const enterpriseId = event.context.user.enterpriseId

  // Verify enterprise is active
  const enterprise = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, enterpriseId))
    .limit(1)

  if (enterprise.length === 0 || enterprise[0].status === 'suspended') {
    throw createError({ statusCode: 403, message: '企业账户已被暂停' })
  }

  // Attach enterprise to context for downstream handlers
  event.context.enterprise = enterprise[0]
})
