import { eq, desc, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const query = getQuery(event)
  const page = Number(query.page) || 1
  const pageSize = Math.min(Number(query.pageSize) || 20, 100)
  const sourceType = query.sourceType as string | undefined

  const db = useDB()

  const conditions = [eq(personaGenomes.enterpriseId, enterpriseId)]
  if (sourceType) conditions.push(eq(personaGenomes.sourceType, sourceType))

  const where = conditions.length === 1 ? conditions[0] : and(...conditions)

  const items = await db.select()
    .from(personaGenomes)
    .where(where)
    .orderBy(desc(personaGenomes.createdAt))
    .limit(pageSize)
    .offset((page - 1) * pageSize)

  const allMatching = await db.select({ id: personaGenomes.id })
    .from(personaGenomes)
    .where(where)
  const total = allMatching.length

  const parsed = items.map(item => ({
    ...item,
    genomeData: JSON.parse(item.genomeData),
    tags: item.tags ? JSON.parse(item.tags) : [],
  }))

  return success({
    items: parsed,
    pagination: { page, pageSize, total, totalPages: Math.ceil(total / pageSize) },
  })
})
