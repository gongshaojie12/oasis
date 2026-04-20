import { z } from 'zod'
import { useDB } from '~~/server/database'
import { knowledgeGraphs, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  graphData: z.object({
    nodes: z.array(z.any()),
    edges: z.array(z.any()),
  }),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '导入数据格式错误')

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const timestamp = now()
  const id = generateId()

  await db.insert(knowledgeGraphs).values({
    id, enterpriseId,
    name: parsed.data.name,
    graphData: JSON.stringify(parsed.data.graphData),
    nodeCount: parsed.data.graphData.nodes.length,
    edgeCount: parsed.data.graphData.edges.length,
    createdAt: timestamp, updatedAt: timestamp,
  })

  await db.insert(operationLogs).values({
    id: generateId(), enterpriseId, userId,
    action: 'import_graph', resourceType: 'knowledge_graph', resourceId: id,
    createdAt: timestamp,
  })

  return success({ id, name: parsed.data.name, nodeCount: parsed.data.graphData.nodes.length })
})
