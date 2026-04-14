import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, reports, llmUsage } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const allSims = await db.select().from(simulations).where(eq(simulations.enterpriseId, enterpriseId))
  const allReports = await db.select({ id: reports.id }).from(reports).where(eq(reports.enterpriseId, enterpriseId))
  const allUsage = await db.select().from(llmUsage).where(eq(llmUsage.enterpriseId, enterpriseId))

  const totalCost = allUsage.reduce((sum, u) => sum + (u.costYuan || 0), 0)
  const totalTokens = allUsage.reduce((sum, u) => sum + (u.inputTokens || 0) + (u.outputTokens || 0), 0)

  return success({
    simulations: {
      total: allSims.length,
      completed: allSims.filter(s => s.status === 'completed').length,
      running: allSims.filter(s => s.status === 'running').length,
      pending: allSims.filter(s => s.status === 'pending').length,
      failed: allSims.filter(s => s.status === 'failed').length,
    },
    reports: allReports.length,
    llm: {
      totalCost: Math.round(totalCost * 100) / 100,
      totalTokens,
      recordCount: allUsage.length,
    },
  })
})
