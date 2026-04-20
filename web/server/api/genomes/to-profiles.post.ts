import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  genomeIds: z.array(z.string()).min(1),
  platform: z.string().default('twitter'),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const { enterpriseId } = event.context.user!
  const db = useDB()

  const profiles: any[] = []
  for (let i = 0; i < parsed.data.genomeIds.length; i++) {
    const gid = parsed.data.genomeIds[i]
    const g = await db.select().from(personaGenomes).where(eq(personaGenomes.id, gid)).limit(1)
    if (g.length === 0) continue
    const genome = JSON.parse(g[0].genomeData)

    const mbtiMap: Record<string, string> = {
      'INTJ': 'analytical and strategic thinker',
      'INTP': 'logical and curious explorer',
      'ENTJ': 'decisive and ambitious leader',
      'ENTP': 'innovative and quick-witted debater',
      'INFJ': 'insightful and idealistic advocate',
      'INFP': 'empathetic and creative mediator',
      'ENFJ': 'charismatic and inspiring protagonist',
      'ENFP': 'enthusiastic and creative campaigner',
      'ISTJ': 'responsible and detail-oriented logistician',
      'ISFJ': 'dedicated and warm protector',
      'ESTJ': 'organized and direct executive',
      'ESFJ': 'caring and sociable consul',
      'ISTP': 'bold and practical virtuoso',
      'ISFP': 'charming and artistic adventurer',
      'ESTP': 'smart and energetic entrepreneur',
      'ESFP': 'spontaneous and enthusiastic entertainer',
    }

    const personality = mbtiMap[genome.demographics?.mbti || ''] || 'thoughtful individual'
    const interests = (genome.demographics?.interests || []).join(', ')
    const ageRange = genome.demographics?.age_range || [25, 35]
    const age = Math.round((ageRange[0] + ageRange[1]) / 2)

    profiles.push({
      agent_id: i,
      name: g[0].name,
      user_name: g[0].name.toLowerCase().replace(/\s+/g, '_') + '_' + i,
      description: `A ${age}-year-old ${genome.demographics?.profession || 'professional'}, ${personality}. Interested in ${interests || 'various topics'}.`,
      persona: `${personality} who is ${genome.traits?.extraversion > 0.6 ? 'outgoing' : 'reserved'} and ${genome.traits?.agreeableness > 0.6 ? 'cooperative' : 'independent-minded'}`,
      age,
      mbti: genome.demographics?.mbti || null,
      interests: genome.demographics?.interests || [],
      activity_level: genome.social_behavior?.activity_level || 0.5,
    })
  }

  return success({ profiles, count: profiles.length })
})
