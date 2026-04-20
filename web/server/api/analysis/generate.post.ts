import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, analysisReports, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  simulationId: z.string().min(1),
  debateRounds: z.number().int().min(1).max(5).default(2),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const sim = await db.select().from(simulations).where(eq(simulations.id, parsed.data.simulationId)).limit(1)
  if (sim.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  if (sim[0].status !== 'completed') return error(ErrorCodes.VALIDATION_ERROR, '仿真尚未完成')

  const analysisId = generateId()
  const timestamp = now()

  const simConfig = JSON.parse(sim[0].config || '{}')
  const dbPath = simConfig.engineTaskId ? `./data/${simConfig.engineTaskId}.db` : ''

  await db.insert(analysisReports).values({
    id: analysisId, simulationId: parsed.data.simulationId, enterpriseId,
    status: 'analyzing', createdAt: timestamp,
  })

  try {
    const result: any = await $fetch(`${config.engineUrl}/engine/analysis/run`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        simulation_id: parsed.data.simulationId,
        platform: sim[0].platform,
        num_agents: sim[0].agentCount || 10,
        num_steps: sim[0].timeSteps || 5,
        db_path: dbPath,
        debate_rounds: parsed.data.debateRounds,
      },
    })

    await db.update(analysisReports).set({
      engineTaskId: result.task_id,
    }).where(eq(analysisReports.id, analysisId))

    await db.insert(operationLogs).values({
      id: generateId(), enterpriseId, userId,
      action: 'generate_analysis', resourceType: 'analysis', resourceId: analysisId,
      createdAt: timestamp,
    })

    return success({ id: analysisId, taskId: result.task_id, status: 'analyzing' })
  } catch (e: any) {
    await db.update(analysisReports).set({ status: 'failed' }).where(eq(analysisReports.id, analysisId))
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '分析启动失败: ' + (e.message || ''))
  }
})
