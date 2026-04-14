import { eq, desc } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { operationLogs, users } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const query = getQuery(event)
  const page = Number(query.page) || 1
  const pageSize = Math.min(Number(query.pageSize) || 50, 200)
  const db = useDB()

  const items = await db.select().from(operationLogs)
    .where(eq(operationLogs.enterpriseId, enterpriseId))
    .orderBy(desc(operationLogs.createdAt))
    .limit(pageSize)
    .offset((page - 1) * pageSize)

  // Enrich with user names
  const userIds = [...new Set(items.map(i => i.userId))]
  const userMap = new Map<string, string>()
  for (const uid of userIds) {
    const u = await db.select({ name: users.name }).from(users).where(eq(users.id, uid)).limit(1)
    if (u.length > 0) userMap.set(uid, u[0].name || '未知用户')
  }

  const enriched = items.map(i => ({
    ...i, userName: userMap.get(i.userId) || '未知用户',
    details: i.details ? JSON.parse(i.details) : null,
  }))

  return success({ items: enriched })
})
