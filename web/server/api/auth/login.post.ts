import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { users, smsCodes, enterprises } from '~~/server/database/schema'
import { signToken, signRefreshToken } from '~~/server/utils/jwt'
import { now } from '~~/server/utils/time'
import { isExpired } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  phone: z.string().regex(/^1[3-9]\d{9}$/),
  code: z.string().length(6),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_CODE_INVALID, '参数错误')
  }

  const { phone, code } = parsed.data
  const db = useDB()

  // Verify SMS code
  const smsRecord = await db.select()
    .from(smsCodes)
    .where(
      and(
        eq(smsCodes.phone, phone),
        eq(smsCodes.code, code),
        eq(smsCodes.used, 0)
      )
    )
    .orderBy(smsCodes.createdAt)
    .limit(1)

  if (smsRecord.length === 0) {
    return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
  }

  if (isExpired(smsRecord[0].expiresAt)) {
    return error(ErrorCodes.SMS_CODE_EXPIRED, '验证码已过期')
  }

  // Mark code as used
  await db.update(smsCodes)
    .set({ used: 1 })
    .where(eq(smsCodes.id, smsRecord[0].id))

  // Find user
  const userRecord = await db.select()
    .from(users)
    .where(eq(users.phone, phone))
    .limit(1)

  if (userRecord.length === 0) {
    return error(ErrorCodes.PHONE_NOT_FOUND, '用户不存在，请先注册')
  }

  const user = userRecord[0]

  // Update last login time
  await db.update(users)
    .set({ lastLoginAt: now() })
    .where(eq(users.id, user.id))

  // Get enterprise info
  const enterpriseRecord = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, user.enterpriseId))
    .limit(1)

  // Generate tokens
  const tokenPayload = {
    userId: user.id,
    enterpriseId: user.enterpriseId,
    role: user.role,
  }
  const token = await signToken(tokenPayload)
  const refreshToken = await signRefreshToken(tokenPayload)

  return success({
    token,
    refreshToken,
    user: {
      id: user.id,
      phone: user.phone,
      name: user.name,
      role: user.role,
    },
    enterprise: enterpriseRecord[0] || null,
  })
})
