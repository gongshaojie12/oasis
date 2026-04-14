import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { llmKeys } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { encrypt } from '~~/server/utils/crypto'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  provider: z.string().min(1),
  apiKey: z.string().min(1),
})

export default defineEventHandler(async (event) => {
  const { enterpriseId, role } = event.context.user!
  if (role !== 'admin') return error(ErrorCodes.FORBIDDEN, '仅管理员可管理 API Key')

  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const config = useRuntimeConfig()
  const db = useDB()
  const timestamp = now()
  const encryptedKey = encrypt(parsed.data.apiKey, config.encryptionKey)

  // Upsert: delete existing then insert
  await db.delete(llmKeys).where(and(eq(llmKeys.enterpriseId, enterpriseId), eq(llmKeys.provider, parsed.data.provider)))
  await db.insert(llmKeys).values({
    id: generateId(), enterpriseId, provider: parsed.data.provider,
    encryptedKey, createdAt: timestamp, updatedAt: timestamp,
  })

  return success({ provider: parsed.data.provider, saved: true })
})
