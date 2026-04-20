import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  const item = items[0]
  let graphData, metadata
  try {
    graphData = JSON.parse(item.graphData)
    metadata = item.metadata ? JSON.parse(item.metadata) : null
  } catch {
    return error(ErrorCodes.SERVER_ERROR, '图谱数据损坏')
  }
  return success({ ...item, graphData, metadata })
})
