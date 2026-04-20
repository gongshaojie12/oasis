import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  sourceType: z.enum(['document', 'url', 'csv', 'manual', 'natural_language']),
  content: z.string().optional(),
  structuredData: z.record(z.string(), z.any()).optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const config = useRuntimeConfig()
  try {
    const result = await $fetch(`${config.engineUrl}/engine/genomes/extract`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        source_type: parsed.data.sourceType,
        content: parsed.data.content || '',
        structured_data: parsed.data.structuredData || null,
      },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '基因组提取失败: ' + (e.message || '引擎不可用'))
  }
})
