import { eq, and } from 'drizzle-orm'
import { z } from 'zod'
import { useDB } from '~~/server/database'
import { simulations, agentConversations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  agentId: z.number().int().min(0),
  roundContext: z.number().int().min(1),
  message: z.string().min(1).max(2000),
  conversationId: z.string().optional(),
  history: z.array(z.object({
    role: z.string(),
    content: z.string(),
    agent_id: z.number().optional(),
    agent_name: z.string().optional(),
  })).optional(),
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
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/chat`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        db_path: dbPath,
        agent_id: parsed.data.agentId,
        round_context: parsed.data.roundContext,
        message: parsed.data.message,
        history: parsed.data.history,
      },
    })

    const { generateId, now } = await import('~~/server/utils/id')
    const convId = parsed.data.conversationId || generateId()
    const newMessages = [
      ...(parsed.data.history || []),
      { role: 'user', content: parsed.data.message },
      { role: 'agent', content: result.response, agent_id: result.agent_id, agent_name: result.agent_name },
    ]

    const existing = await db.select().from(agentConversations)
      .where(eq(agentConversations.id, convId))
      .limit(1)

    if (existing.length > 0) {
      await db.update(agentConversations).set({
        messages: JSON.stringify(newMessages),
      }).where(eq(agentConversations.id, convId))
    } else {
      await db.insert(agentConversations).values({
        id: convId,
        simulationId: simId,
        enterpriseId,
        roundContext: parsed.data.roundContext,
        conversationType: 'chat',
        participants: JSON.stringify([parsed.data.agentId]),
        messages: JSON.stringify(newMessages),
        createdAt: now(),
      })
    }

    return success({ ...result, conversationId: convId })
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '对话失败: ' + (e.message || ''))
  }
})
