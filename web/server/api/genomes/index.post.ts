import { z } from 'zod'
import { useDB } from '~~/server/database'
import { personaGenomes, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  sourceType: z.enum(['document', 'url', 'csv', 'manual', 'natural_language']),
  genomeData: z.record(z.string(), z.any()),
  tags: z.array(z.string()).optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误: ' + parsed.error.issues.map(i => i.message).join(', '))
  }

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const id = generateId()
  const timestamp = now()

  await db.insert(personaGenomes).values({
    id,
    enterpriseId,
    name: parsed.data.name,
    sourceType: parsed.data.sourceType,
    genomeData: JSON.stringify(parsed.data.genomeData),
    tags: parsed.data.tags ? JSON.stringify(parsed.data.tags) : null,
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  await db.insert(operationLogs).values({
    id: generateId(), enterpriseId, userId,
    action: 'create', resourceType: 'genome', resourceId: id,
    details: JSON.stringify({ name: parsed.data.name, sourceType: parsed.data.sourceType }),
    createdAt: timestamp,
  })

  return success({ id, name: parsed.data.name })
})
