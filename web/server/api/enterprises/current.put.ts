import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { enterprises } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100).optional(),
  contactPhone: z.string().regex(/^1[3-9]\d{9}$/).optional(),
})

export default defineEventHandler(async (event) => {
  const { enterpriseId, role } = event.context.user!
  if (role !== 'admin') return error(ErrorCodes.FORBIDDEN, '仅管理员可修改企业信息')

  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const db = useDB()
  const updates: Record<string, any> = { updatedAt: now() }
  if (parsed.data.name) updates.name = parsed.data.name
  if (parsed.data.contactPhone) updates.contactPhone = parsed.data.contactPhone

  await db.update(enterprises).set(updates).where(eq(enterprises.id, enterpriseId))
  return success({ updated: true })
})
