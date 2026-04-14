import { verifyToken } from '~~/server/utils/jwt'

// Routes that don't require authentication
const publicPaths = [
  '/api/auth/sms.send',
  '/api/auth/login',
  '/api/auth/register',
  '/api/health',
  '/api/internal/',
]

export default defineEventHandler(async (event) => {
  const path = getRequestURL(event).pathname

  // Skip non-API routes (pages, assets)
  if (!path.startsWith('/api/')) return

  // Skip public API routes
  if (publicPaths.some(p => path.startsWith(p))) return

  const authHeader = getRequestHeader(event, 'authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    event.context.user = null
    throw createError({ statusCode: 401, message: '未登录' })
  }

  try {
    const token = authHeader.slice(7)
    const payload = await verifyToken(token)
    event.context.user = payload
  } catch {
    event.context.user = null
    throw createError({ statusCode: 401, message: 'Token 无效或已过期' })
  }
})
