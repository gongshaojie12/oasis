import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).optional(),
  graphData: z.object({
    nodes: z.array(z.any()),
    edges: z.array(z.any()),
  }).optional(),
})

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const existing = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  const updates: any = { updatedAt: now() }
  if (parsed.data.name) updates.name = parsed.data.name
  if (parsed.data.description !== undefined) updates.description = parsed.data.description
  if (parsed.data.graphData) {
    updates.graphData = JSON.stringify(parsed.data.graphData)
    updates.nodeCount = parsed.data.graphData.nodes.length
    updates.edgeCount = parsed.data.graphData.edges.length
  }

  await db.update(knowledgeGraphs).set(updates).where(eq(knowledgeGraphs.id, id))
  return success({ id })
})
