import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  description: z.string().min(1).max(5000),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '请输入场景描述')

  const config = useRuntimeConfig()

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/parse`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { description: parsed.data.description },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '场景解析失败: ' + (e.message || ''))
  }
})
