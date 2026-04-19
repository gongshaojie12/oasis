import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { users, smsCodes, enterprises } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { signToken, signRefreshToken } from '~~/server/utils/jwt'
import { now, isExpired } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  phone: z.string().regex(/^1[3-9]\d{9}$/),
  code: z.string().length(6),
  enterpriseName: z.string().min(2).max(50),
  userName: z.string().min(2).max(20),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_CODE_INVALID, parsed.error.issues[0].message)
  }

  const { phone, code, enterpriseName, userName } = parsed.data
  const db = useDB()
  const config = useRuntimeConfig()
  const isTestPhone = config.testPhone && phone === String(config.testPhone)

  // Verify SMS code (skip for test phone)
  if (isTestPhone) {
    if (code !== String(config.testSmsCode)) {
      return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
    }
  } else {
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
  }

  // Check if phone already registered
  const existingUser = await db.select()
    .from(users)
    .where(eq(users.phone, phone))
    .limit(1)

  if (existingUser.length > 0) {
    return error(ErrorCodes.SMS_CODE_INVALID, '该手机号已注册')
  }

  // Create enterprise
  const enterpriseId = generateId()
  const timestamp = now()
  await db.insert(enterprises).values({
    id: enterpriseId,
    name: enterpriseName,
    contactPhone: phone,
    simQuota: 3, // Free trial: 3 simulations
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  // Create user (admin of the enterprise)
  const userId = generateId()
  await db.insert(users).values({
    id: userId,
    enterpriseId,
    phone,
    name: userName,
    role: 'admin',
    lastLoginAt: timestamp,
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  // Generate tokens
  const tokenPayload = { userId, enterpriseId, role: 'admin' }
  const token = await signToken(tokenPayload)
  const refreshToken = await signRefreshToken(tokenPayload)

  return success({
    token,
    refreshToken,
    user: { id: userId, phone, name: userName, role: 'admin' },
    enterprise: {
      id: enterpriseId,
      name: enterpriseName,
      planType: 'basic',
      simQuota: 3,
    },
  })
})
