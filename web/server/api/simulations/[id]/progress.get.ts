import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations } from '~~/server/database/schema'
import { progressStore } from '~~/server/utils/progress-store'
import { createEventStream } from 'h3'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const sim = await db.select().from(simulations)
    .where(and(eq(simulations.id, id), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sim.length === 0) {
    throw createError({ statusCode: 404, statusMessage: 'Not found' })
  }

  // If already finished, send final state and close
  if (['completed', 'failed', 'cancelled'].includes(sim[0].status)) {
    const eventStream = createEventStream(event)
    await eventStream.push(JSON.stringify({
      type: sim[0].status === 'completed' ? 'complete' : 'error',
      status: sim[0].status, progress: sim[0].progress, error: sim[0].errorMessage,
    }))
    await eventStream.close()
    return eventStream.send()
  }

  const eventStream = createEventStream(event)

  // Send current state immediately
  await eventStream.push(JSON.stringify({
    type: 'progress', status: sim[0].status, progress: sim[0].progress,
    currentStep: 0, totalSteps: (sim[0].timeSteps || 5) + 2,
  }))

  // Subscribe to progress store
  const unsubscribe = progressStore.subscribe(id, async (progressEvent) => {
    try {
      await eventStream.push(JSON.stringify(progressEvent))
      if (progressEvent.type === 'complete' || progressEvent.type === 'error') {
        unsubscribe()
        await eventStream.close()
      }
    } catch { unsubscribe() }
  })

  eventStream.onClosed(() => { unsubscribe() })
  return eventStream.send()
})
