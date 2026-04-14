import { z } from 'zod'
import { useDB } from '~~/server/database'
import { simulationTemplates } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  type: z.string().min(1),
  platform: z.string().min(1),
  config: z.record(z.string(), z.any()),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误: ' + parsed.error.issues.map(i => i.message).join(', '))
  }

  const { enterpriseId } = event.context.user!
  const db = useDB()

  const id = generateId()
  const timestamp = now()
  const { name, type, platform, config } = parsed.data

  await db.insert(simulationTemplates).values({
    id,
    enterpriseId,
    name,
    type,
    platform,
    config: JSON.stringify(config),
    isPublic: 0,
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  return success({ id, name, type, platform })
})
