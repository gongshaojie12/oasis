import { eq, and } from 'drizzle-orm'
import { z } from 'zod'
import { useDB } from '~~/server/database'
import { simulations, agentConversations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  agentIds: z.array(z.number().int().min(0)).min(2).max(8),
  roundContext: z.number().int().min(1),
  topic: z.string().min(1).max(500),
  numRounds: z.number().int().min(1).max(5).default(3),
})

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  let simConfig
  try { simConfig = JSON.parse(sim.config) } catch { return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏') }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return error(ErrorCodes.SERVER_ERROR, '仿真数据库路径不可用')

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/roundtable`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        db_path: dbPath,
        agent_ids: parsed.data.agentIds,
        round_context: parsed.data.roundContext,
        topic: parsed.data.topic,
        num_rounds: parsed.data.numRounds,
      },
    })

    const { generateId, now } = await import('~~/server/utils/id')
    await db.insert(agentConversations).values({
      id: generateId(),
      simulationId: simId,
      enterpriseId,
      roundContext: parsed.data.roundContext,
      conversationType: 'roundtable',
      participants: JSON.stringify(parsed.data.agentIds),
      messages: JSON.stringify(result.messages || []),
      topic: parsed.data.topic,
      createdAt: now(),
    })

    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '圆桌会议失败: ' + (e.message || ''))
  }
})
