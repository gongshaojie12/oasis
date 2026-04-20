import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  dna_a: z.record(z.string(), z.any()),
  dna_b: z.record(z.string(), z.any()),
  weight_a: z.number().min(0).max(1).default(0.5),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const config = useRuntimeConfig()

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/mix`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: parsed.data,
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, 'DNA混合失败: ' + (e.message || ''))
  }
})
