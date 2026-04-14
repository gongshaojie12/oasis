import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { reports, simulations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const report = await db.select().from(reports)
    .where(and(eq(reports.id, id), eq(reports.enterpriseId, enterpriseId)))
    .limit(1)

  if (report.length === 0) return error(ErrorCodes.NOT_FOUND, '报告不存在')

  const sim = await db.select().from(simulations)
    .where(eq(simulations.id, report[0].simulationId))
    .limit(1)

  return success({
    ...report[0],
    dashboardData: report[0].dashboardData ? JSON.parse(report[0].dashboardData) : null,
    simulation: sim[0] || null,
  })
})
