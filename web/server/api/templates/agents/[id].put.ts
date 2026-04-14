import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { agentTemplates } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100).optional(),
  platform: z.string().min(1).optional(),
  profileConfig: z.record(z.string(), z.any()).optional(),
})

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误: ' + parsed.error.issues.map(i => i.message).join(', '))
  }

  const { enterpriseId } = event.context.user!
  const db = useDB()

  // Check ownership
  const template = await db.select()
    .from(agentTemplates)
    .where(and(
      eq(agentTemplates.id, id),
      eq(agentTemplates.enterpriseId, enterpriseId)
    ))
    .limit(1)

  if (template.length === 0) {
    return error(ErrorCodes.FORBIDDEN, '只能更新自己的模板')
  }

  const updates: any = { updatedAt: now() }
  if (parsed.data.name !== undefined) updates.name = parsed.data.name
  if (parsed.data.platform !== undefined) updates.platform = parsed.data.platform
  if (parsed.data.profileConfig !== undefined) {
    updates.profileConfig = JSON.stringify(parsed.data.profileConfig)
  }

  await db.update(agentTemplates)
    .set(updates)
    .where(eq(agentTemplates.id, id))

  return success({ id })
})
