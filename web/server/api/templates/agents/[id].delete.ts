import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { agentTemplates } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
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
    return error(ErrorCodes.FORBIDDEN, '只能删除自己的模板')
  }

  await db.delete(agentTemplates).where(eq(agentTemplates.id, id))

  return success({ id })
})
