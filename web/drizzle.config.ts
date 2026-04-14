import { defineConfig } from 'drizzle-kit'

export default defineConfig({
  schema: './server/database/schema/sqlite.ts',
  out: './drizzle',
  dialect: 'sqlite',
  dbCredentials: {
    url: process.env.DATABASE_URL?.replace('file:', '') || './data/oasis.db',
  },
})
