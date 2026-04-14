import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { reports } from '~~/server/database/schema'
import { existsSync, createReadStream } from 'fs'
import { resolve } from 'path'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const report = await db.select().from(reports)
    .where(and(eq(reports.id, id), eq(reports.enterpriseId, enterpriseId)))
    .limit(1)

  if (report.length === 0) throw createError({ statusCode: 404, statusMessage: '报告不存在' })
  if (!report[0].pdfUrl) throw createError({ statusCode: 404, statusMessage: 'PDF 尚未生成' })

  const filePath = resolve(report[0].pdfUrl)
  if (!existsSync(filePath)) throw createError({ statusCode: 404, statusMessage: 'PDF 文件不存在' })

  setResponseHeader(event, 'Content-Type', 'application/pdf')
  setResponseHeader(event, 'Content-Disposition', `attachment; filename="report-${id}.pdf"`)
  return sendStream(event, createReadStream(filePath))
})
