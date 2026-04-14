import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, enterprises } from '~~/server/database/schema'
import { now, isExpired } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'
import { submitToEngine } from '~~/server/utils/engine-client'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const sim = await db.select().from(simulations)
    .where(and(eq(simulations.id, id), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sim.length === 0) return error(ErrorCodes.NOT_FOUND, '模拟任务不存在')
  if (sim[0].status !== 'failed' && sim[0].status !== 'cancelled') {
    return error(ErrorCodes.VALIDATION_ERROR, '只能重试失败或已取消的任务')
  }

  // Check quota
  const ent = await db.select().from(enterprises).where(eq(enterprises.id, enterpriseId)).limit(1)
  if (ent.length === 0 || ent[0].simQuota <= 0) return error(ErrorCodes.QUOTA_EXCEEDED, '配额不足')
  if (ent[0].quotaExpires && isExpired(ent[0].quotaExpires)) return error(ErrorCodes.QUOTA_EXPIRED, '配额已过期')

  // Deduct quota
  await db.update(enterprises).set({ simQuota: ent[0].simQuota - 1, updatedAt: now() }).where(eq(enterprises.id, enterpriseId))

  // Reset simulation
  await db.update(simulations).set({
    status: 'pending', progress: 0, errorMessage: null,
    startedAt: null, completedAt: null, updatedAt: now(),
  }).where(eq(simulations.id, id))

  // Re-dispatch
  const config = JSON.parse(sim[0].config || '{}')
  try {
    const engineResult = await submitToEngine({
      platform_type: sim[0].platform, num_steps: sim[0].timeSteps || 5, num_agents: sim[0].agentCount || 10,
      seed_content: config.seedContent, agent_profiles: config.agentProfiles,
      available_actions: config.availableActions, llm_provider: config.llmProvider, llm_model: config.llmModel,
    })
    await db.update(simulations).set({
      config: JSON.stringify({ ...config, engineTaskId: engineResult.task_id }), updatedAt: now(),
    }).where(eq(simulations.id, id))
  } catch (e: any) {
    await db.update(enterprises).set({ simQuota: ent[0].simQuota, updatedAt: now() }).where(eq(enterprises.id, enterpriseId))
    await db.update(simulations).set({ status: 'failed', errorMessage: `重试调度失败: ${e.message}`, updatedAt: now() }).where(eq(simulations.id, id))
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '引擎调度失败，配额已退还')
  }

  return success({ id, status: 'pending' })
})
