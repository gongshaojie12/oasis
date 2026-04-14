import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { llmKeys } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

const PROVIDERS = [
  { id: 'deepseek', name: 'DeepSeek', models: ['deepseek-chat', 'deepseek-reasoner'] },
  { id: 'qwen', name: '通义千问', models: ['qwen-plus', 'qwen-max', 'qwen-turbo'] },
  { id: 'doubao', name: '字节豆包', models: ['doubao-1-5-pro-256k', 'doubao-1-5-lite-32k'] },
  { id: 'minimax', name: 'MiniMax', models: ['MiniMax-Text-01', 'abab6.5s'] },
  { id: 'zhipu', name: '智谱AI', models: ['glm-4-plus', 'glm-4-flash'] },
  { id: 'kimi', name: 'Kimi', models: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'] },
  { id: 'openai', name: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini'] },
]

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const keys = await db.select({ provider: llmKeys.provider }).from(llmKeys)
    .where(eq(llmKeys.enterpriseId, enterpriseId))

  const configuredProviders = new Set(keys.map(k => k.provider))

  return success(PROVIDERS.map(p => ({ ...p, hasKey: configuredProviders.has(p.id) })))
})
