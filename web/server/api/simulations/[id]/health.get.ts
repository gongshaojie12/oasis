import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, id), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  if (sim.status !== 'running') {
    return success({ health_score: 1.0, indicators: {} })
  }

  let simConfig
  try { simConfig = JSON.parse(sim.config) } catch { return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏') }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return success({ health_score: 1.0, indicators: {} })

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/simulations/health`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        db_path: dbPath,
        num_agents: sim.agentCount || 10,
        num_steps: sim.timeSteps || 5,
        current_step: Math.round((sim.progress || 0) * (sim.timeSteps || 5) / 100),
      },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '健康检查失败: ' + (e.message || ''))
  }
})
