import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, simulationSnapshots } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const roundStr = getRouterParam(event, 'round')!
  const roundNumber = parseInt(roundStr, 10)
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  if (isNaN(roundNumber) || roundNumber < 1) {
    return error(ErrorCodes.VALIDATION_ERROR, '轮次参数无效')
  }

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  const cached = await db.select().from(simulationSnapshots)
    .where(and(
      eq(simulationSnapshots.simulationId, simId),
      eq(simulationSnapshots.enterpriseId, enterpriseId),
      eq(simulationSnapshots.roundNumber, roundNumber),
    ))
    .limit(1)

  if (cached.length > 0) {
    try { return success(JSON.parse(cached[0].snapshotData)) } catch {}
  }

  let simConfig
  try { simConfig = JSON.parse(sim.config) } catch { return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏') }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return error(ErrorCodes.SERVER_ERROR, '仿真数据库路径不可用')

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/snapshots`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { db_path: dbPath, num_steps: sim.timeSteps || 5, round_number: roundNumber },
    })

    return success(result.snapshot || null)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '快照提取失败: ' + (e.message || ''))
  }
})
