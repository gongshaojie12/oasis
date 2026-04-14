import { eq, desc, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const query = getQuery(event)
  const page = Number(query.page) || 1
  const pageSize = Math.min(Number(query.pageSize) || 20, 100)
  const status = query.status as string | undefined
  const type = query.type as string | undefined
  const platform = query.platform as string | undefined

  const db = useDB()

  const conditions = [eq(simulations.enterpriseId, enterpriseId)]
  if (status) conditions.push(eq(simulations.status, status))
  if (type) conditions.push(eq(simulations.type, type))
  if (platform) conditions.push(eq(simulations.platform, platform))

  const where = conditions.length === 1 ? conditions[0] : and(...conditions)

  const items = await db.select()
    .from(simulations)
    .where(where)
    .orderBy(desc(simulations.createdAt))
    .limit(pageSize)
    .offset((page - 1) * pageSize)

  const allMatching = await db.select({ id: simulations.id })
    .from(simulations)
    .where(where)
  const total = allMatching.length

  return success({
    items,
    pagination: { page, pageSize, total, totalPages: Math.ceil(total / pageSize) },
  })
})
