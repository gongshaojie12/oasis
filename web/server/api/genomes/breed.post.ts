import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes, genomeBatches, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  seedGenomeIds: z.array(z.string()).min(1),
  targetCount: z.number().int().min(1).max(10000),
  mutationRate: z.number().min(0).max(1).default(0.15),
  strategy: z.enum(['clone_mutate', 'crossover', 'distribution']).default('crossover'),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误: ' + parsed.error.issues.map(i => i.message).join(', '))
  }

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const seeds: any[] = []
  for (const gid of parsed.data.seedGenomeIds) {
    const g = await db.select().from(personaGenomes).where(eq(personaGenomes.id, gid)).limit(1)
    if (g.length === 0) return error(ErrorCodes.NOT_FOUND, `种子基因组 ${gid} 不存在`)
    seeds.push(JSON.parse(g[0].genomeData))
  }

  const batchId = generateId()
  const timestamp = now()

  await db.insert(genomeBatches).values({
    id: batchId, enterpriseId, name: parsed.data.name,
    seedGenomeIds: JSON.stringify(parsed.data.seedGenomeIds),
    targetCount: parsed.data.targetCount, mutationRate: parsed.data.mutationRate,
    strategy: parsed.data.strategy, status: 'processing',
    createdAt: timestamp, updatedAt: timestamp,
  })

  try {
    const result: any = await $fetch(`${config.engineUrl}/engine/genomes/breed`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        seeds,
        target_count: parsed.data.targetCount,
        mutation_rate: parsed.data.mutationRate,
        strategy: parsed.data.strategy,
      },
    })

    const genomeIds: string[] = []
    for (let i = 0; i < result.genomes.length; i++) {
      const gId = generateId()
      genomeIds.push(gId)
      await db.insert(personaGenomes).values({
        id: gId, enterpriseId,
        name: `${parsed.data.name}_${String(i + 1).padStart(3, '0')}`,
        sourceType: 'breed',
        genomeData: JSON.stringify(result.genomes[i]),
        tags: JSON.stringify([`batch:${batchId}`]),
        createdAt: timestamp, updatedAt: timestamp,
      })
    }

    await db.update(genomeBatches).set({
      status: 'completed',
      resultGenomeIds: JSON.stringify(genomeIds),
      diversity: result.diversity,
      updatedAt: now(),
    }).where(eq(genomeBatches.id, batchId))

    await db.insert(operationLogs).values({
      id: generateId(), enterpriseId, userId,
      action: 'breed', resourceType: 'genome_batch', resourceId: batchId,
      details: JSON.stringify({ count: result.count, diversity: result.diversity }),
      createdAt: timestamp,
    })

    return success({ batchId, count: result.count, diversity: result.diversity, genomeIds })
  } catch (e: any) {
    await db.update(genomeBatches).set({ status: 'failed', updatedAt: now() }).where(eq(genomeBatches.id, batchId))
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '繁殖失败: ' + (e.message || '引擎不可用'))
  }
})
