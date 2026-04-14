import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, enterprises } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { progressStore } from '~~/server/utils/progress-store'

const bodySchema = z.object({
  task_id: z.string(),
  error: z.string(),
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

  const { task_id, error: errorMsg } = parsed.data
  const db = useDB()

  const sim = await db.select()
    .from(simulations)
    .where(eq(simulations.id, task_id))
    .limit(1)

  if (sim.length === 0) return { ok: true }

  const timestamp = now()

  // Refund quota on failure
  const enterprise = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, sim[0].enterpriseId))
    .limit(1)

  if (enterprise.length > 0) {
    await db.update(enterprises)
      .set({ simQuota: enterprise[0].simQuota + 1 })
      .where(eq(enterprises.id, sim[0].enterpriseId))
  }

  await db.update(simulations)
    .set({
      status: 'failed',
      errorMessage: errorMsg,
      completedAt: timestamp,
      updatedAt: timestamp,
    })
    .where(eq(simulations.id, task_id))

  progressStore.emit(task_id, {
    simulationId: task_id,
    type: 'error',
    status: 'failed',
    progress: sim[0].progress,
    currentStep: 0,
    totalSteps: 0,
    error: errorMsg,
  })

  return { ok: true }
})
