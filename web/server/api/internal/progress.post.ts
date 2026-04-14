import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { progressStore } from '~~/server/utils/progress-store'

const bodySchema = z.object({
  task_id: z.string(),
  current_step: z.number(),
  total_steps: z.number(),
  progress: z.number(),
  data: z.record(z.string(), z.any()).optional(),
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

  const { task_id, current_step, total_steps, progress } = parsed.data
  const db = useDB()

  const sim = await db.select()
    .from(simulations)
    .where(eq(simulations.id, task_id))
    .limit(1)

  if (sim.length === 0) return { ok: true }

  const progressPercent = Math.round(progress * 100)

  await db.update(simulations)
    .set({
      status: 'running',
      progress: progressPercent,
      startedAt: sim[0].startedAt || now(),
      updatedAt: now(),
    })
    .where(eq(simulations.id, task_id))

  progressStore.emit(task_id, {
    simulationId: task_id,
    type: 'progress',
    status: 'running',
    progress: progressPercent,
    currentStep: current_step,
    totalSteps: total_steps,
    data: parsed.data.data,
  })

  return { ok: true }
})
