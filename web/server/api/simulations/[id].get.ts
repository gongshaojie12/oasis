import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const sim = await db.select().from(simulations)
    .where(and(eq(simulations.id, id), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sim.length === 0) return error(ErrorCodes.NOT_FOUND, '模拟任务不存在')
  return success(sim[0])
})
