import { eq, desc } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { reports } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const query = getQuery(event)
  const page = Number(query.page) || 1
  const pageSize = Math.min(Number(query.pageSize) || 20, 100)

  const db = useDB()

  const items = await db.select().from(reports)
    .where(eq(reports.enterpriseId, enterpriseId))
    .orderBy(desc(reports.createdAt))
    .limit(pageSize)
    .offset((page - 1) * pageSize)

  const allMatching = await db.select({ id: reports.id }).from(reports)
    .where(eq(reports.enterpriseId, enterpriseId))
  const total = allMatching.length

  return success({
    items,
    pagination: { page, pageSize, total, totalPages: Math.ceil(total / pageSize) },
  })
})
