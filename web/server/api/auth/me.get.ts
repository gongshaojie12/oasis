import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { users, enterprises } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const user = event.context.user
  if (!user) {
    return error(ErrorCodes.TOKEN_INVALID, '未登录')
  }

  const db = useDB()

  const userRecord = await db.select()
    .from(users)
    .where(eq(users.id, user.userId))
    .limit(1)

  if (userRecord.length === 0) {
    return error(ErrorCodes.TOKEN_INVALID, '用户不存在')
  }

  const enterpriseRecord = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, user.enterpriseId))
    .limit(1)

  return success({
    user: {
      id: userRecord[0].id,
      phone: userRecord[0].phone,
      name: userRecord[0].name,
      role: userRecord[0].role,
    },
    enterprise: enterpriseRecord[0] || null,
  })
})
