import * as sqliteSchema from './schema/sqlite'
import * as pgSchema from './schema/pg'

let _db: any = null
let _dbReady: Promise<any> | null = null

async function createDatabase() {
  const config = useRuntimeConfig()
  const dbType = config.databaseType

  if (dbType === 'postgresql') {
    const { drizzle } = await import('drizzle-orm/postgres-js')
    const postgres = (await import('postgres')).default
    const client = postgres(config.databaseUrl)
    return drizzle(client, { schema: pgSchema })
  }

  const { drizzle } = await import('drizzle-orm/better-sqlite3')
  const Database = (await import('better-sqlite3')).default
  const dbPath = config.databaseUrl.replace('file:', '')
  const sqlite = new Database(dbPath)
  sqlite.pragma('journal_mode = WAL')
  sqlite.pragma('foreign_keys = ON')
  return drizzle(sqlite, { schema: sqliteSchema })
}

export function useDB() {
  if (!_db) {
    throw new Error('Database not initialized. Call initDB() first.')
  }
  return _db
}

export async function initDB() {
  if (_db) return _db
  if (!_dbReady) {
    _dbReady = createDatabase().then((db) => {
      _db = db
      return db
    })
  }
  return _dbReady
}

export { sqliteSchema, pgSchema }
