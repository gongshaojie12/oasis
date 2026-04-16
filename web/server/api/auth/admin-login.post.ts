import { z } from 'zod'
import { signToken, signRefreshToken } from '~~/server/utils/jwt'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_CODE_INVALID, '请输入账号和密码')
  }

  const { username, password } = parsed.data
  const config = useRuntimeConfig()

  if (!config.adminUsername || !config.adminPassword) {
    return error(ErrorCodes.FORBIDDEN, '管理员登录未启用')
  }

  if (username !== config.adminUsername || password !== config.adminPassword) {
    return error(ErrorCodes.FORBIDDEN, '账号或密码错误')
  }

  const tokenPayload = {
    userId: 'superadmin',
    enterpriseId: '',
    role: 'superadmin',
  }
  const token = await signToken(tokenPayload)
  const refreshToken = await signRefreshToken(tokenPayload)

  return success({
    token,
    refreshToken,
    user: {
      id: 'superadmin',
      phone: '',
      name: '超级管理员',
      role: 'superadmin',
    },
    enterprise: null,
  })
})
