import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select().from(personaGenomes)
    .where(and(eq(personaGenomes.id, id), eq(personaGenomes.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '基因组不存在')

  return success({
    ...items[0],
    genomeData: JSON.parse(items[0].genomeData),
    tags: items[0].tags ? JSON.parse(items[0].tags) : [],
  })
})
