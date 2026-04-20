import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select().from(analysisReports)
    .where(and(eq(analysisReports.id, id), eq(analysisReports.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '分析报告不存在')

  const item = items[0]
  return success({
    ...item,
    analystReports: item.analystReports ? JSON.parse(item.analystReports) : null,
    debateLog: item.debateLog ? JSON.parse(item.debateLog) : null,
    finalReport: item.finalReport ? JSON.parse(item.finalReport) : null,
    chartData: item.chartData ? JSON.parse(item.chartData) : null,
    timelineData: item.timelineData ? JSON.parse(item.timelineData) : null,
  })
})
