import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select({ chartData: analysisReports.chartData })
    .from(analysisReports)
    .where(and(eq(analysisReports.id, id), eq(analysisReports.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '不存在')
  return success(items[0].chartData ? JSON.parse(items[0].chartData) : {})
})
