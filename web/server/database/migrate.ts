import Database from 'better-sqlite3'
import { drizzle } from 'drizzle-orm/better-sqlite3'
import { migrate } from 'drizzle-orm/better-sqlite3/migrator'
import { resolve } from 'path'
import { mkdirSync, existsSync } from 'fs'

const dbDir = resolve(process.cwd(), 'data')
if (!existsSync(dbDir)) {
  mkdirSync(dbDir, { recursive: true })
}

const dbPath = process.env.DATABASE_URL?.replace('file:', '') || './data/oasis.db'
const sqlite = new Database(dbPath)
sqlite.pragma('journal_mode = WAL')
sqlite.pragma('foreign_keys = ON')

const db = drizzle(sqlite)
migrate(db, { migrationsFolder: resolve(process.cwd(), 'drizzle') })

console.log('Migration completed successfully')
sqlite.close()
