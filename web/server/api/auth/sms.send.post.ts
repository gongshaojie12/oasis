import { z } from 'zod'
import { eq, and, gt } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { smsCodes } from '~~/server/database/schema'
import { generateId, generateSmsCode } from '~~/server/utils/id'
import { now, addMinutes } from '~~/server/utils/time'
import { sendSms } from '~~/server/utils/sms'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  phone: z.string().regex(/^1[3-9]\d{9}$/, '请输入有效的手机号'),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_RATE_LIMIT, parsed.error.issues[0].message)
  }

  const { phone } = parsed.data

  // Test phone: skip SMS sending entirely
  const config = useRuntimeConfig()
  if (config.testPhone && phone === config.testPhone) {
    return success({ sent: true })
  }

  const db = useDB()

  // Rate limit: 60 seconds between sends
  const recentCode = await db.select()
    .from(smsCodes)
    .where(
      and(
        eq(smsCodes.phone, phone),
        gt(smsCodes.createdAt, new Date(Date.now() - 60000).toISOString())
      )
    )
    .limit(1)

  if (recentCode.length > 0) {
    return error(ErrorCodes.SMS_RATE_LIMIT, '请60秒后再试')
  }

  const code = generateSmsCode()
  await db.insert(smsCodes).values({
    id: generateId(),
    phone,
    code,
    expiresAt: addMinutes(5),
    createdAt: now(),
  })

  await sendSms(phone, code)

  return success({ sent: true })
})
