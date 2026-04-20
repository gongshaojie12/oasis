import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const items = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  const graphData = JSON.parse(items[0].graphData)

  try {
    const result = await $fetch(`${config.engineUrl}/engine/graph/to-simulation`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { graph_data: graphData },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '映射失败: ' + (e.message || ''))
  }
})
