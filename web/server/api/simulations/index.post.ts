import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, enterprises, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now, isExpired } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'
import { submitToEngine } from '~~/server/utils/engine-client'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  type: z.enum([
    'marketing_sim', 'sentiment_predict', 'recsys_test',
    'research', 'digital_twin', 'synthetic_data',
  ]),
  platform: z.string().min(1),
  agentCount: z.number().int().min(1).max(100000).default(10),
  timeSteps: z.number().int().min(1).max(1000).default(5),
  seedContent: z.string().optional(),
  agentProfiles: z.array(z.record(z.string(), z.any())).optional(),
  availableActions: z.array(z.string()).optional(),
  llmProvider: z.string().optional(),
  llmModel: z.string().optional(),
  config: z.record(z.string(), z.any()).optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误: ' + parsed.error.issues.map(i => i.message).join(', '))
  }

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()

  // Check quota
  const ent = await db.select().from(enterprises).where(eq(enterprises.id, enterpriseId)).limit(1)
  if (ent.length === 0) return error(ErrorCodes.ENTERPRISE_SUSPENDED, '企业不存在')
  if (ent[0].quotaExpires && isExpired(ent[0].quotaExpires)) return error(ErrorCodes.QUOTA_EXPIRED, '配额已过期，请续费')
  if (ent[0].simQuota <= 0) return error(ErrorCodes.QUOTA_EXCEEDED, '模拟次数已用完，请购买更多配额')

  // Deduct quota
  await db.update(enterprises).set({ simQuota: ent[0].simQuota - 1, updatedAt: now() }).where(eq(enterprises.id, enterpriseId))

  const simId = generateId()
  const timestamp = now()
  const { name, type, platform, agentCount, timeSteps, seedContent, agentProfiles, availableActions, llmProvider, llmModel, config } = parsed.data

  const fullConfig = JSON.stringify({ ...config, agentProfiles, availableActions, seedContent })

  await db.insert(simulations).values({
    id: simId, enterpriseId, userId, name, type, platform,
    config: fullConfig, status: 'pending', progress: 0,
    agentCount, timeSteps, llmModel: llmModel || null,
    createdAt: timestamp, updatedAt: timestamp,
  })

  // Log operation
  await db.insert(operationLogs).values({
    id: generateId(), enterpriseId, userId,
    action: 'create', resourceType: 'simulation', resourceId: simId,
    details: JSON.stringify({ name, type, platform }), createdAt: timestamp,
  })

  // Dispatch to engine
  try {
    const engineResult = await submitToEngine({
      platform_type: platform, num_steps: timeSteps, num_agents: agentCount,
      seed_content: seedContent, agent_profiles: agentProfiles,
      available_actions: availableActions, llm_provider: llmProvider, llm_model: llmModel,
    })
    await db.update(simulations).set({
      config: JSON.stringify({ ...JSON.parse(fullConfig), engineTaskId: engineResult.task_id }),
      updatedAt: now(),
    }).where(eq(simulations.id, simId))
  } catch (e: any) {
    await db.update(enterprises).set({ simQuota: ent[0].simQuota, updatedAt: now() }).where(eq(enterprises.id, enterpriseId))
    await db.update(simulations).set({
      status: 'failed', errorMessage: `引擎调度失败: ${e.message || '无法连接模拟引擎'}`, updatedAt: now(),
    }).where(eq(simulations.id, simId))
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '模拟引擎调度失败，配额已退还')
  }

  return success({ id: simId, status: 'pending', name, type, platform })
})
