import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100).optional(),
  genomeData: z.record(z.string(), z.any()).optional(),
  tags: z.array(z.string()).optional(),
})

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const db = useDB()

  const existing = await db.select().from(personaGenomes)
    .where(and(eq(personaGenomes.id, id), eq(personaGenomes.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '基因组不存在')

  const updates: Record<string, any> = { updatedAt: now() }
  if (parsed.data.name) updates.name = parsed.data.name
  if (parsed.data.genomeData) updates.genomeData = JSON.stringify(parsed.data.genomeData)
  if (parsed.data.tags) updates.tags = JSON.stringify(parsed.data.tags)

  await db.update(personaGenomes).set(updates).where(eq(personaGenomes.id, id))

  return success({ id })
})
