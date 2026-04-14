import { eq, or, desc, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulationTemplates } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const query = getQuery(event)
  const platform = query.platform as string | undefined

  const db = useDB()

  const conditions = [
    or(
      eq(simulationTemplates.enterpriseId, enterpriseId),
      eq(simulationTemplates.isPublic, 1)
    )!,
  ]
  if (platform) conditions.push(eq(simulationTemplates.platform, platform))

  const where = conditions.length === 1 ? conditions[0] : and(...conditions)

  const items = await db.select()
    .from(simulationTemplates)
    .where(where)
    .orderBy(desc(simulationTemplates.createdAt))

  return success({ items })
})
