import { eq, and, asc } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, simulationSnapshots } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  const snapshots = await db.select().from(simulationSnapshots)
    .where(and(
      eq(simulationSnapshots.simulationId, simId),
      eq(simulationSnapshots.enterpriseId, enterpriseId),
    ))
    .orderBy(asc(simulationSnapshots.roundNumber))

  const replayData = snapshots.map(s => {
    let data
    try { data = JSON.parse(s.snapshotData) } catch { data = {} }
    return { round: s.roundNumber, ...data }
  })

  return success({
    simulationId: simId,
    totalRounds: sim.timeSteps || replayData.length,
    platform: sim.platform,
    agentCount: sim.agentCount,
    rounds: replayData,
  })
})
