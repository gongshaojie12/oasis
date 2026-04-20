import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, simulationSnapshots } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  if (sim.status !== 'completed') return error(ErrorCodes.VALIDATION_ERROR, '仿真未完成')

  const cached = await db.select().from(simulationSnapshots)
    .where(and(
      eq(simulationSnapshots.simulationId, simId),
      eq(simulationSnapshots.enterpriseId, enterpriseId),
    ))
    .orderBy(simulationSnapshots.roundNumber)

  if (cached.length > 0) {
    return success(cached.map(s => {
      let snapshotData
      try { snapshotData = JSON.parse(s.snapshotData) } catch { snapshotData = {} }
      return { ...s, snapshotData }
    }))
  }

  let simConfig
  try { simConfig = JSON.parse(sim.config) } catch { return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏') }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return error(ErrorCodes.SERVER_ERROR, '仿真数据库路径不可用')

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/snapshots`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { db_path: dbPath, num_steps: sim.timeSteps || 5 },
    })

    const { generateId, now } = await import('~~/server/utils/id')
    for (const snap of (result.snapshots || [])) {
      await db.insert(simulationSnapshots).values({
        id: generateId(),
        simulationId: simId,
        enterpriseId,
        roundNumber: snap.round_number,
        snapshotData: JSON.stringify(snap),
        createdAt: now(),
      })
    }

    return success(result.snapshots || [])
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '快照提取失败: ' + (e.message || ''))
  }
})
