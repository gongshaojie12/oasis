import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { llmKeys } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const provider = getRouterParam(event, 'provider')!
  const { enterpriseId, role } = event.context.user!
  if (role !== 'admin') return error(ErrorCodes.FORBIDDEN, '仅管理员可管理 API Key')

  const db = useDB()
  const existing = await db.select().from(llmKeys)
    .where(and(eq(llmKeys.enterpriseId, enterpriseId), eq(llmKeys.provider, provider)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '未找到该提供商的 Key')

  await db.delete(llmKeys).where(and(eq(llmKeys.enterpriseId, enterpriseId), eq(llmKeys.provider, provider)))
  return success({ provider, deleted: true })
})
