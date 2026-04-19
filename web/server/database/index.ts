import * as sqliteSchema from './schema/sqlite'
import * as pgSchema from './schema/pg'

let _db: any = null
let _dbReady: Promise<any> | null = null

function ensureSQLiteTables(sqlite: any) {
  const tableExists = sqlite.prepare(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='enterprises'"
  ).get()
  if (tableExists) return

  console.log('[database] creating tables...')
  sqlite.exec(`
    CREATE TABLE IF NOT EXISTS \`enterprises\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`name\` text NOT NULL,
      \`contact_phone\` text,
      \`status\` text DEFAULT 'active' NOT NULL,
      \`plan_type\` text DEFAULT 'basic' NOT NULL,
      \`sim_quota\` integer DEFAULT 0 NOT NULL,
      \`quota_expires\` text,
      \`created_at\` text NOT NULL,
      \`updated_at\` text NOT NULL
    );
    CREATE TABLE IF NOT EXISTS \`users\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`enterprise_id\` text NOT NULL,
      \`phone\` text NOT NULL,
      \`name\` text,
      \`role\` text DEFAULT 'user' NOT NULL,
      \`last_login_at\` text,
      \`created_at\` text NOT NULL,
      \`updated_at\` text NOT NULL,
      FOREIGN KEY (\`enterprise_id\`) REFERENCES \`enterprises\`(\`id\`) ON UPDATE no action ON DELETE no action
    );
    CREATE UNIQUE INDEX IF NOT EXISTS \`users_phone_unique\` ON \`users\` (\`phone\`);
    CREATE TABLE IF NOT EXISTS \`sms_codes\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`phone\` text NOT NULL,
      \`code\` text NOT NULL,
      \`expires_at\` text NOT NULL,
      \`used\` integer DEFAULT 0 NOT NULL,
      \`created_at\` text NOT NULL
    );
    CREATE TABLE IF NOT EXISTS \`simulations\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`enterprise_id\` text NOT NULL,
      \`user_id\` text NOT NULL,
      \`name\` text NOT NULL,
      \`type\` text NOT NULL,
      \`platform\` text NOT NULL,
      \`config\` text NOT NULL,
      \`status\` text DEFAULT 'pending' NOT NULL,
      \`progress\` integer DEFAULT 0 NOT NULL,
      \`agent_count\` integer,
      \`time_steps\` integer,
      \`llm_model\` text,
      \`started_at\` text,
      \`completed_at\` text,
      \`error_message\` text,
      \`created_at\` text NOT NULL,
      \`updated_at\` text NOT NULL,
      FOREIGN KEY (\`enterprise_id\`) REFERENCES \`enterprises\`(\`id\`) ON UPDATE no action ON DELETE no action,
      FOREIGN KEY (\`user_id\`) REFERENCES \`users\`(\`id\`) ON UPDATE no action ON DELETE no action
    );
    CREATE TABLE IF NOT EXISTS \`reports\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`simulation_id\` text NOT NULL,
      \`enterprise_id\` text NOT NULL,
      \`title\` text NOT NULL,
      \`summary\` text,
      \`dashboard_data\` text,
      \`pdf_url\` text,
      \`raw_data_url\` text,
      \`created_at\` text NOT NULL,
      FOREIGN KEY (\`simulation_id\`) REFERENCES \`simulations\`(\`id\`) ON UPDATE no action ON DELETE no action,
      FOREIGN KEY (\`enterprise_id\`) REFERENCES \`enterprises\`(\`id\`) ON UPDATE no action ON DELETE no action
    );
    CREATE TABLE IF NOT EXISTS \`orders\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`enterprise_id\` text NOT NULL,
      \`plan_type\` text NOT NULL,
      \`amount\` integer NOT NULL,
      \`sim_quota\` integer NOT NULL,
      \`duration_days\` integer NOT NULL,
      \`status\` text DEFAULT 'pending' NOT NULL,
      \`paid_at\` text,
      \`notes\` text,
      \`created_at\` text NOT NULL,
      \`updated_at\` text NOT NULL,
      FOREIGN KEY (\`enterprise_id\`) REFERENCES \`enterprises\`(\`id\`) ON UPDATE no action ON DELETE no action
    );
    CREATE TABLE IF NOT EXISTS \`agent_templates\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`enterprise_id\` text,
      \`platform\` text NOT NULL,
      \`name\` text NOT NULL,
      \`profile_config\` text NOT NULL,
      \`is_public\` integer DEFAULT 0 NOT NULL,
      \`created_at\` text NOT NULL,
      \`updated_at\` text NOT NULL
    );
    CREATE TABLE IF NOT EXISTS \`simulation_templates\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`enterprise_id\` text,
      \`name\` text NOT NULL,
      \`type\` text NOT NULL,
      \`platform\` text NOT NULL,
      \`config\` text NOT NULL,
      \`is_public\` integer DEFAULT 0 NOT NULL,
      \`created_at\` text NOT NULL,
      \`updated_at\` text NOT NULL
    );
    CREATE TABLE IF NOT EXISTS \`llm_usage\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`simulation_id\` text NOT NULL,
      \`enterprise_id\` text NOT NULL,
      \`provider\` text,
      \`model\` text,
      \`input_tokens\` integer,
      \`output_tokens\` integer,
      \`cost_yuan\` real,
      \`agent_tier\` text,
      \`created_at\` text NOT NULL,
      FOREIGN KEY (\`simulation_id\`) REFERENCES \`simulations\`(\`id\`) ON UPDATE no action ON DELETE no action,
      FOREIGN KEY (\`enterprise_id\`) REFERENCES \`enterprises\`(\`id\`) ON UPDATE no action ON DELETE no action
    );
    CREATE TABLE IF NOT EXISTS \`llm_keys\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`enterprise_id\` text NOT NULL,
      \`provider\` text NOT NULL,
      \`encrypted_key\` text NOT NULL,
      \`created_at\` text NOT NULL,
      \`updated_at\` text NOT NULL,
      FOREIGN KEY (\`enterprise_id\`) REFERENCES \`enterprises\`(\`id\`) ON UPDATE no action ON DELETE no action
    );
    CREATE TABLE IF NOT EXISTS \`operation_logs\` (
      \`id\` text PRIMARY KEY NOT NULL,
      \`enterprise_id\` text NOT NULL,
      \`user_id\` text NOT NULL,
      \`action\` text NOT NULL,
      \`resource_type\` text NOT NULL,
      \`resource_id\` text,
      \`details\` text,
      \`created_at\` text NOT NULL,
      FOREIGN KEY (\`enterprise_id\`) REFERENCES \`enterprises\`(\`id\`) ON UPDATE no action ON DELETE no action,
      FOREIGN KEY (\`user_id\`) REFERENCES \`users\`(\`id\`) ON UPDATE no action ON DELETE no action
    );
  `)
  console.log('[database] tables created')
}

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
  ensureSQLiteTables(sqlite)
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
