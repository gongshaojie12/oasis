import * as sqliteSchema from './schema/sqlite'
import * as pgSchema from './schema/pg'

let _db: any = null

function createDatabase() {
  const config = useRuntimeConfig()
  const dbType = config.databaseType

  if (dbType === 'postgresql') {
    const { drizzle } = require('drizzle-orm/postgres-js') as typeof import('drizzle-orm/postgres-js')
    const postgres = require('postgres') as typeof import('postgres')
    const client = postgres(config.databaseUrl)
    return drizzle(client, { schema: pgSchema })
  }

  const { drizzle } = require('drizzle-orm/better-sqlite3') as typeof import('drizzle-orm/better-sqlite3')
  const Database = require('better-sqlite3')
  const dbPath = config.databaseUrl.replace('file:', '')
  const sqlite = new Database(dbPath)
  sqlite.pragma('journal_mode = WAL')
  sqlite.pragma('foreign_keys = ON')
  return drizzle(sqlite, { schema: sqliteSchema })
}

export function useDB() {
  if (!_db) {
    _db = createDatabase()
  }
  return _db
}

export { sqliteSchema, pgSchema }
