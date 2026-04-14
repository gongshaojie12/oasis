import { eq, or, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { agentTemplates } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const template = await db.select()
    .from(agentTemplates)
    .where(and(
      eq(agentTemplates.id, id),
      or(
        eq(agentTemplates.enterpriseId, enterpriseId),
        eq(agentTemplates.isPublic, 1)
      )!
    ))
    .limit(1)

  if (template.length === 0) return error(ErrorCodes.NOT_FOUND, '模板不存在')

  const result = {
    ...template[0],
    profileConfig: JSON.parse(template[0].profileConfig),
  }

  return success(result)
})
