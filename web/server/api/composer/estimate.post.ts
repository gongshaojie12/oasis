import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  config: z.record(z.string(), z.any()),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const config = useRuntimeConfig()

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/estimate`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { config: parsed.data.config },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '资源估算失败: ' + (e.message || ''))
  }
})
