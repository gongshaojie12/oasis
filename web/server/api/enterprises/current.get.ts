import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { enterprises, users } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const ent = await db.select().from(enterprises).where(eq(enterprises.id, enterpriseId)).limit(1)
  const members = await db.select().from(users).where(eq(users.enterpriseId, enterpriseId))

  return success({
    ...ent[0],
    memberCount: members.length,
    members: members.map(m => ({
      id: m.id, name: m.name, phone: m.phone, role: m.role, lastLoginAt: m.lastLoginAt,
    })),
  })
})
