import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const config = useRuntimeConfig()

  try {
    const params = new URLSearchParams()
    if (query.platform) params.set('platform', String(query.platform))
    if (query.type) params.set('type', String(query.type))

    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/recommend?${params.toString()}`, {
      headers: { 'X-Internal-Key': config.internalApiKey },
    })
    return success(result.templates || [])
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '获取推荐场景失败: ' + (e.message || ''))
  }
})
