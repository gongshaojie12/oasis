import { initDB } from '~~/server/database'

export default defineNitroPlugin(async () => {
  await initDB()
  console.log('[database] initialized')
})
