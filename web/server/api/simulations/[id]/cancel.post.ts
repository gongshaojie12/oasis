import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, enterprises } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'
import { cancelEngineTask } from '~~/server/utils/engine-client'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const sim = await db.select().from(simulations)
    .where(and(eq(simulations.id, id), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sim.length === 0) return error(ErrorCodes.NOT_FOUND, '模拟任务不存在')
  if (sim[0].status !== 'pending' && sim[0].status !== 'running') {
    return error(ErrorCodes.VALIDATION_ERROR, '只能取消等待中或运行中的任务')
  }

  // Try to cancel in engine
  const config = JSON.parse(sim[0].config || '{}')
  if (config.engineTaskId) {
    try { await cancelEngineTask(config.engineTaskId) } catch { /* engine may be down */ }
  }

  // Refund quota
  const ent = await db.select().from(enterprises).where(eq(enterprises.id, enterpriseId)).limit(1)
  if (ent.length > 0) {
    await db.update(enterprises).set({ simQuota: ent[0].simQuota + 1, updatedAt: now() }).where(eq(enterprises.id, enterpriseId))
  }

  await db.update(simulations).set({ status: 'cancelled', completedAt: now(), updatedAt: now() }).where(eq(simulations.id, id))
  return success({ id, cancelled: true })
})
