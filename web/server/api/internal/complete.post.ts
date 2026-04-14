import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, reports } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { progressStore } from '~~/server/utils/progress-store'

const bodySchema = z.object({
  task_id: z.string(),
  result: z.record(z.string(), z.any()),
})

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const internalKey = getHeader(event, 'x-internal-key')
  if (internalKey !== config.internalApiKey) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid request body' })
  }

  const { task_id, result } = parsed.data
  const db = useDB()

  const sim = await db.select()
    .from(simulations)
    .where(eq(simulations.id, task_id))
    .limit(1)

  if (sim.length === 0) return { ok: true }

  const timestamp = now()

  await db.update(simulations)
    .set({
      status: 'completed',
      progress: 100,
      completedAt: timestamp,
      updatedAt: timestamp,
    })
    .where(eq(simulations.id, task_id))

  const numStepsCompleted = (result.num_steps_completed as number | undefined) || 0
  const numAgents = (result.num_agents as number | undefined) || 0

  // Auto-create a report record
  await db.insert(reports).values({
    id: generateId(),
    simulationId: task_id,
    enterpriseId: sim[0].enterpriseId,
    title: `${sim[0].name} - 模拟报告`,
    summary: `模拟已完成，共 ${numStepsCompleted} 步，${numAgents} 个 Agent`,
    dashboardData: JSON.stringify(result),
    createdAt: timestamp,
  })

  progressStore.emit(task_id, {
    simulationId: task_id,
    type: 'complete',
    status: 'completed',
    progress: 100,
    currentStep: numStepsCompleted,
    totalSteps: numStepsCompleted,
    result,
  })

  return { ok: true }
})
