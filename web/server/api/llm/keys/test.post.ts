import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const PROVIDER_URLS: Record<string, string> = {
  deepseek: 'https://api.deepseek.com/v1/models',
  qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1/models',
  doubao: 'https://ark.cn-beijing.volces.com/api/v3/models',
  minimax: 'https://api.minimax.chat/v1/models',
  zhipu: 'https://open.bigmodel.cn/api/paas/v4/models',
  kimi: 'https://api.moonshot.cn/v1/models',
  openai: 'https://api.openai.com/v1/models',
}

const bodySchema = z.object({
  provider: z.string().min(1),
  apiKey: z.string().min(1),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const { provider, apiKey } = parsed.data
  const url = PROVIDER_URLS[provider]
  if (!url) return error(ErrorCodes.VALIDATION_ERROR, `不支持的提供商: ${provider}`)

  try {
    await $fetch(url, { headers: { Authorization: `Bearer ${apiKey}` }, timeout: 10000 })
    return success({ provider, connected: true })
  } catch (e: any) {
    const status = e.response?.status || e.statusCode
    if (status === 401 || status === 403) {
      return success({ provider, connected: false, reason: 'API Key 无效' })
    }
    return success({ provider, connected: false, reason: `连接失败: ${e.message}` })
  }
})
