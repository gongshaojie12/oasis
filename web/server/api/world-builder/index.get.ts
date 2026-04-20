import { eq, desc } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select({
    id: knowledgeGraphs.id,
    name: knowledgeGraphs.name,
    description: knowledgeGraphs.description,
    nodeCount: knowledgeGraphs.nodeCount,
    edgeCount: knowledgeGraphs.edgeCount,
    createdAt: knowledgeGraphs.createdAt,
    updatedAt: knowledgeGraphs.updatedAt,
  }).from(knowledgeGraphs)
    .where(eq(knowledgeGraphs.enterpriseId, enterpriseId))
    .orderBy(desc(knowledgeGraphs.createdAt))
    .limit(50)

  return success(items)
})
