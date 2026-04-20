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

  let graphData
  try {
    graphData = JSON.parse(items[0].graphData)
  } catch {
    return error(ErrorCodes.SERVER_ERROR, '图谱数据损坏')
  }

  try {
    const result = await $fetch(`${config.engineUrl}/engine/graph/analyze`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { graph_data: graphData },
    })

    await db.update(knowledgeGraphs).set({
      metadata: JSON.stringify(result),
    }).where(eq(knowledgeGraphs.id, id))

    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '图分析失败: ' + (e.message || ''))
  }
})
