import { z } from 'zod'
import { and, eq, inArray } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports, reportComparisons } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  reportIds: z.array(z.string()).min(2).max(5),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '请选择2-5份报告')

  const { enterpriseId } = event.context.user!
  const db = useDB()

  const reports = await db.select().from(analysisReports)
    .where(and(
      inArray(analysisReports.id, parsed.data.reportIds),
      eq(analysisReports.enterpriseId, enterpriseId),
    ))

  if (reports.length !== parsed.data.reportIds.length) return error(ErrorCodes.NOT_FOUND, '部分报告不存在或无权访问')

  const comparisonData: any = { reports: [] }
  for (const r of reports) {
    const chartData = r.chartData ? JSON.parse(r.chartData) : {}
    const finalReport = r.finalReport ? JSON.parse(r.finalReport) : {}
    comparisonData.reports.push({
      id: r.id,
      simulationId: r.simulationId,
      executive_summary: finalReport.executive_summary || '',
      chart_data: chartData,
    })
  }

  const compId = generateId()
  await db.insert(reportComparisons).values({
    id: compId, enterpriseId,
    reportIds: JSON.stringify(parsed.data.reportIds),
    comparisonData: JSON.stringify(comparisonData),
    createdAt: now(),
  })

  return success({ id: compId, comparison: comparisonData })
})
