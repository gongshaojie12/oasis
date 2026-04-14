import { success } from '~~/server/utils/response'

export default defineEventHandler(async () => {
  return success({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '0.1.0',
  })
})
