import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  genomes: z.array(z.record(z.string(), z.any())).min(1),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const genomes = parsed.data.genomes

  const traitKeys = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
  const traitDistribution: Record<string, { values: number[]; mean: number; std: number }> = {}
  for (const key of traitKeys) {
    const values = genomes.map(g => g.traits?.[key] ?? 0.5)
    const mean = values.reduce((a, b) => a + b, 0) / values.length
    const std = Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length)
    traitDistribution[key] = { values, mean: Math.round(mean * 1000) / 1000, std: Math.round(std * 1000) / 1000 }
  }

  const ageValues = genomes.map(g => {
    const range = g.demographics?.age_range ?? [25, 35]
    return Math.round((range[0] + range[1]) / 2)
  })

  const activityValues = genomes.map(g => g.social_behavior?.activity_level ?? 0.5)

  const professionCounts: Record<string, number> = {}
  for (const g of genomes) {
    const prof = g.demographics?.profession ?? 'unknown'
    professionCounts[prof] = (professionCounts[prof] || 0) + 1
  }

  return success({
    count: genomes.length,
    traitDistribution,
    ageDistribution: { values: ageValues, mean: Math.round(ageValues.reduce((a, b) => a + b, 0) / ageValues.length) },
    activityDistribution: { values: activityValues, mean: Math.round(activityValues.reduce((a, b) => a + b, 0) / activityValues.length * 100) / 100 },
    professionCounts,
  })
})
