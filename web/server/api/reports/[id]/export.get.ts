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
  if (!report[0].rawDataUrl) throw createError({ statusCode: 404, statusMessage: '原始数据尚未生成' })

  const filePath = resolve(report[0].rawDataUrl)
  if (!existsSync(filePath)) throw createError({ statusCode: 404, statusMessage: '数据文件不存在' })

  setResponseHeader(event, 'Content-Type', 'text/csv')
  setResponseHeader(event, 'Content-Disposition', `attachment; filename="data-${id}.csv"`)
  return sendStream(event, createReadStream(filePath))
})
