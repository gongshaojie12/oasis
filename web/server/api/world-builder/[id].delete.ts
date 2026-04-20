import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const existing = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  await db.delete(knowledgeGraphs).where(eq(knowledgeGraphs.id, id))
  return success({ id })
})
