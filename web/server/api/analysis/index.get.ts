import { eq, desc } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select().from(analysisReports)
    .where(eq(analysisReports.enterpriseId, enterpriseId))
    .orderBy(desc(analysisReports.createdAt))
    .limit(50)

  return success(items)
})
