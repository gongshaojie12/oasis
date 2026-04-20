import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const existing = await db.select().from(personaGenomes)
    .where(and(eq(personaGenomes.id, id), eq(personaGenomes.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '基因组不存在')

  await db.delete(personaGenomes).where(eq(personaGenomes.id, id))
  return success({ id })
})
