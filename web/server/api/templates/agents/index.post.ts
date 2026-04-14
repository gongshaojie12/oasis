import { z } from 'zod'
import { useDB } from '~~/server/database'
import { agentTemplates } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  platform: z.string().min(1),
  name: z.string().min(1).max(100),
  profileConfig: z.record(z.string(), z.any()),
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
  const { platform, name, profileConfig } = parsed.data

  await db.insert(agentTemplates).values({
    id,
    enterpriseId,
    platform,
    name,
    profileConfig: JSON.stringify(profileConfig),
    isPublic: 0,
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  return success({ id, name, platform })
})
