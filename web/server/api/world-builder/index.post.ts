import { z } from 'zod'
import { useDB } from '~~/server/database'
import { knowledgeGraphs, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  graphData: z.object({
    nodes: z.array(z.any()).default([]),
    edges: z.array(z.any()).default([]),
  }).optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const timestamp = now()
  const id = generateId()

  const graphData = parsed.data.graphData || { nodes: [], edges: [] }

  await db.insert(knowledgeGraphs).values({
    id, enterpriseId,
    name: parsed.data.name,
    description: parsed.data.description || null,
    graphData: JSON.stringify(graphData),
    nodeCount: graphData.nodes.length,
    edgeCount: graphData.edges.length,
    createdAt: timestamp, updatedAt: timestamp,
  })

  await db.insert(operationLogs).values({
    id: generateId(), enterpriseId, userId,
    action: 'create_graph', resourceType: 'knowledge_graph', resourceId: id,
    createdAt: timestamp,
  })

  return success({ id, name: parsed.data.name })
})
