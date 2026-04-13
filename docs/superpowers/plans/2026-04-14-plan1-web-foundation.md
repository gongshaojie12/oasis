# Plan 1: Web Foundation & Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Nuxt 3 web application foundation with database, authentication, and base layout — the platform shell that all business features will plug into.

**Architecture:** Single Nuxt 3 application with Nitro server routes handling API logic, Drizzle ORM for database access (supporting both SQLite and PostgreSQL via env switch), JWT-based auth with SMS verification code login, and Naive UI component library with a dark tech-themed design.

**Tech Stack:** Nuxt 3, Nitro, Naive UI, Drizzle ORM, better-sqlite3, postgres (optional), jose (JWT), zod, Pinia, ECharts, Iconify

**Design Spec:** `docs/superpowers/specs/2026-04-13-commercial-platform-design.md`

---

## Task 1: Initialize Nuxt 3 Project & Dependencies

**Files:**
- Create: `web/package.json`
- Create: `web/nuxt.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/.env`
- Create: `web/.env.example`
- Create: `web/.gitignore`

- [ ] **Step 1: Create Nuxt 3 project**

```bash
cd D:/project/oasis
npx nuxi@latest init web --packageManager npm
```

When prompted, select defaults. This creates the basic Nuxt 3 scaffold.

- [ ] **Step 2: Install production dependencies**

```bash
cd D:/project/oasis/web
npm install naive-ui @css-render/vue3-ssr drizzle-orm better-sqlite3 nanoid jose zod @pinia/nuxt @vueuse/nuxt @iconify-json/carbon @nuxt/icon echarts vue-echarts
```

- [ ] **Step 3: Install dev dependencies**

```bash
cd D:/project/oasis/web
npm install -D drizzle-kit @types/better-sqlite3 vitest @nuxt/test-utils
```

- [ ] **Step 4: Configure nuxt.config.ts**

Replace `web/nuxt.config.ts` with:

```typescript
export default defineNuxtConfig({
  devtools: { enabled: true },

  modules: [
    '@pinia/nuxt',
    '@vueuse/nuxt',
    '@nuxt/icon',
  ],

  build: {
    transpile: ['naive-ui', '@css-render/vue3-ssr', '@juggle/resize-observer'],
  },

  vite: {
    optimizeDeps: {
      include: ['naive-ui', 'vueuc', 'date-fns-tz/formatInTimeZone'],
    },
  },

  runtimeConfig: {
    databaseType: process.env.DATABASE_TYPE || 'sqlite',
    databaseUrl: process.env.DATABASE_URL || 'file:./data/oasis.db',
    jwtSecret: process.env.JWT_SECRET || 'dev-secret-change-in-production',
    jwtExpiresIn: '2h',
    refreshTokenExpiresIn: '7d',
    smsAccessKey: process.env.SMS_ACCESS_KEY || '',
    smsAccessSecret: process.env.SMS_ACCESS_SECRET || '',
    internalApiKey: process.env.INTERNAL_API_KEY || 'dev-internal-key',
    engineUrl: process.env.ENGINE_URL || 'http://localhost:8000',
    encryptionKey: process.env.ENCRYPTION_KEY || 'dev-encryption-key-32chars!!',
  },

  compatibilityDate: '2025-01-01',
})
```

- [ ] **Step 5: Create environment files**

Create `web/.env`:

```bash
DATABASE_TYPE=sqlite
DATABASE_URL=file:./data/oasis.db
JWT_SECRET=your-secret-key-at-least-32-characters-long
SMS_ACCESS_KEY=
SMS_ACCESS_SECRET=
INTERNAL_API_KEY=dev-internal-key
ENGINE_URL=http://localhost:8000
ENCRYPTION_KEY=dev-encryption-key-32chars!!
```

Create `web/.env.example` (same content but with placeholder values).

- [ ] **Step 6: Update .gitignore**

Append to `web/.gitignore`:

```
data/
*.db
.env
```

- [ ] **Step 7: Verify project starts**

```bash
cd D:/project/oasis/web
npm run dev
```

Expected: Nuxt dev server starts at `http://localhost:3000` with the default welcome page.

- [ ] **Step 8: Commit**

```bash
cd D:/project/oasis
git add web/
git commit -m "feat(web): initialize Nuxt 3 project with dependencies"
```

---

## Task 2: Database Schema — SQLite

**Files:**
- Create: `web/server/database/schema/sqlite.ts`
- Create: `web/server/database/schema/index.ts`
- Create: `web/server/database/index.ts`
- Create: `web/server/database/migrate.ts`
- Create: `web/drizzle.config.ts`

- [ ] **Step 1: Create SQLite schema**

Create `web/server/database/schema/sqlite.ts`:

```typescript
import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core'

export const enterprises = sqliteTable('enterprises', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  contactPhone: text('contact_phone'),
  status: text('status').default('active').notNull(), // active | suspended
  planType: text('plan_type').default('basic').notNull(), // basic | professional | enterprise
  simQuota: integer('sim_quota').default(0).notNull(),
  quotaExpires: text('quota_expires'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  phone: text('phone').notNull().unique(),
  name: text('name'),
  role: text('role').default('user').notNull(), // admin | user
  lastLoginAt: text('last_login_at'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const smsCodes = sqliteTable('sms_codes', {
  id: text('id').primaryKey(),
  phone: text('phone').notNull(),
  code: text('code').notNull(),
  expiresAt: text('expires_at').notNull(),
  used: integer('used').default(0).notNull(),
  createdAt: text('created_at').notNull(),
})

export const simulations = sqliteTable('simulations', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  userId: text('user_id').notNull().references(() => users.id),
  name: text('name').notNull(),
  type: text('type').notNull(), // marketing_sim | sentiment_predict | recsys_test | research | digital_twin | synthetic_data
  platform: text('platform').notNull(),
  config: text('config').notNull(), // JSON string
  status: text('status').default('pending').notNull(), // pending | running | completed | failed
  progress: integer('progress').default(0).notNull(),
  agentCount: integer('agent_count'),
  timeSteps: integer('time_steps'),
  llmModel: text('llm_model'),
  startedAt: text('started_at'),
  completedAt: text('completed_at'),
  errorMessage: text('error_message'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const reports = sqliteTable('reports', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  title: text('title').notNull(),
  summary: text('summary'),
  dashboardData: text('dashboard_data'), // JSON string
  pdfUrl: text('pdf_url'),
  rawDataUrl: text('raw_data_url'),
  createdAt: text('created_at').notNull(),
})

export const orders = sqliteTable('orders', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  planType: text('plan_type').notNull(),
  amount: integer('amount').notNull(), // in cents (分)
  simQuota: integer('sim_quota').notNull(),
  durationDays: integer('duration_days').notNull(),
  status: text('status').default('pending').notNull(), // pending | paid | expired
  paidAt: text('paid_at'),
  notes: text('notes'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const agentTemplates = sqliteTable('agent_templates', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id'), // NULL = system preset
  platform: text('platform').notNull(),
  name: text('name').notNull(),
  profileConfig: text('profile_config').notNull(), // JSON string
  isPublic: integer('is_public').default(0).notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const simulationTemplates = sqliteTable('simulation_templates', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id'), // NULL = system preset
  name: text('name').notNull(),
  type: text('type').notNull(),
  platform: text('platform').notNull(),
  config: text('config').notNull(), // JSON string
  isPublic: integer('is_public').default(0).notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const llmUsage = sqliteTable('llm_usage', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  provider: text('provider'),
  model: text('model'),
  inputTokens: integer('input_tokens'),
  outputTokens: integer('output_tokens'),
  costYuan: real('cost_yuan'),
  agentTier: text('agent_tier'), // core | normal | background
  createdAt: text('created_at').notNull(),
})
```

- [ ] **Step 2: Create schema index with re-export**

Create `web/server/database/schema/index.ts`:

```typescript
// All API code imports from here.
// Switch DATABASE_TYPE env var to change backend.
// Both SQLite and PG schemas export identical names.

export {
  enterprises,
  users,
  smsCodes,
  simulations,
  reports,
  orders,
  agentTemplates,
  simulationTemplates,
  llmUsage,
} from './sqlite'
```

- [ ] **Step 3: Create database connection factory**

Create `web/server/database/index.ts`:

```typescript
import { drizzle as drizzleSqlite } from 'drizzle-orm/better-sqlite3'
import Database from 'better-sqlite3'
import * as schema from './schema'

let _db: ReturnType<typeof createDatabase> | null = null

function createDatabase() {
  const config = useRuntimeConfig()
  const dbType = config.databaseType

  if (dbType === 'postgresql') {
    // PG support will be added in Task 3
    // Dynamic import to avoid loading pg when using SQLite
    throw new Error('PostgreSQL support not yet configured. Set DATABASE_TYPE=sqlite')
  }

  // SQLite (default)
  const dbPath = config.databaseUrl.replace('file:', '')
  const sqlite = new Database(dbPath)
  sqlite.pragma('journal_mode = WAL')
  sqlite.pragma('foreign_keys = ON')
  return drizzleSqlite(sqlite, { schema })
}

export function useDB() {
  if (!_db) {
    _db = createDatabase()
  }
  return _db
}

export { schema }
```

- [ ] **Step 4: Create migration script**

Create `web/server/database/migrate.ts`:

```typescript
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
```

- [ ] **Step 5: Configure Drizzle Kit**

Create `web/drizzle.config.ts`:

```typescript
import { defineConfig } from 'drizzle-kit'

export default defineConfig({
  schema: './server/database/schema/sqlite.ts',
  out: './drizzle',
  dialect: 'sqlite',
  dbCredentials: {
    url: process.env.DATABASE_URL?.replace('file:', '') || './data/oasis.db',
  },
})
```

- [ ] **Step 6: Generate initial migration and run it**

```bash
cd D:/project/oasis/web
npx drizzle-kit generate
npx tsx server/database/migrate.ts
```

Expected: `drizzle/` folder created with SQL migration files, `data/oasis.db` created with all tables.

- [ ] **Step 7: Verify database tables exist**

```bash
cd D:/project/oasis/web
npx tsx -e "
const Database = require('better-sqlite3');
const db = new Database('./data/oasis.db');
const tables = db.prepare(\"SELECT name FROM sqlite_master WHERE type='table'\").all();
console.log('Tables:', tables.map(t => t.name));
db.close();
"
```

Expected: All 9 tables listed (enterprises, users, sms_codes, simulations, reports, orders, agent_templates, simulation_templates, llm_usage).

- [ ] **Step 8: Commit**

```bash
cd D:/project/oasis
git add web/server/database/ web/drizzle.config.ts web/drizzle/
git commit -m "feat(web): add database schema and SQLite connection with Drizzle ORM"
```

---

## Task 3: PostgreSQL Schema & Connection Factory

**Files:**
- Create: `web/server/database/schema/pg.ts`
- Modify: `web/server/database/schema/index.ts`
- Modify: `web/server/database/index.ts`

- [ ] **Step 1: Install PostgreSQL driver**

```bash
cd D:/project/oasis/web
npm install postgres
```

- [ ] **Step 2: Create PostgreSQL schema**

Create `web/server/database/schema/pg.ts`:

```typescript
import { pgTable, text, integer, real } from 'drizzle-orm/pg-core'

export const enterprises = pgTable('enterprises', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  contactPhone: text('contact_phone'),
  status: text('status').default('active').notNull(),
  planType: text('plan_type').default('basic').notNull(),
  simQuota: integer('sim_quota').default(0).notNull(),
  quotaExpires: text('quota_expires'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const users = pgTable('users', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  phone: text('phone').notNull().unique(),
  name: text('name'),
  role: text('role').default('user').notNull(),
  lastLoginAt: text('last_login_at'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const smsCodes = pgTable('sms_codes', {
  id: text('id').primaryKey(),
  phone: text('phone').notNull(),
  code: text('code').notNull(),
  expiresAt: text('expires_at').notNull(),
  used: integer('used').default(0).notNull(),
  createdAt: text('created_at').notNull(),
})

export const simulations = pgTable('simulations', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  userId: text('user_id').notNull().references(() => users.id),
  name: text('name').notNull(),
  type: text('type').notNull(),
  platform: text('platform').notNull(),
  config: text('config').notNull(),
  status: text('status').default('pending').notNull(),
  progress: integer('progress').default(0).notNull(),
  agentCount: integer('agent_count'),
  timeSteps: integer('time_steps'),
  llmModel: text('llm_model'),
  startedAt: text('started_at'),
  completedAt: text('completed_at'),
  errorMessage: text('error_message'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const reports = pgTable('reports', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  title: text('title').notNull(),
  summary: text('summary'),
  dashboardData: text('dashboard_data'),
  pdfUrl: text('pdf_url'),
  rawDataUrl: text('raw_data_url'),
  createdAt: text('created_at').notNull(),
})

export const orders = pgTable('orders', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  planType: text('plan_type').notNull(),
  amount: integer('amount').notNull(),
  simQuota: integer('sim_quota').notNull(),
  durationDays: integer('duration_days').notNull(),
  status: text('status').default('pending').notNull(),
  paidAt: text('paid_at'),
  notes: text('notes'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const agentTemplates = pgTable('agent_templates', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id'),
  platform: text('platform').notNull(),
  name: text('name').notNull(),
  profileConfig: text('profile_config').notNull(),
  isPublic: integer('is_public').default(0).notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const simulationTemplates = pgTable('simulation_templates', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id'),
  name: text('name').notNull(),
  type: text('type').notNull(),
  platform: text('platform').notNull(),
  config: text('config').notNull(),
  isPublic: integer('is_public').default(0).notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const llmUsage = pgTable('llm_usage', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  provider: text('provider'),
  model: text('model'),
  inputTokens: integer('input_tokens'),
  outputTokens: integer('output_tokens'),
  costYuan: real('cost_yuan'),
  agentTier: text('agent_tier'),
  createdAt: text('created_at').notNull(),
})
```

- [ ] **Step 3: Update schema index to support switching**

Update `web/server/database/schema/index.ts`:

```typescript
// Database schema re-exports.
// To switch from SQLite to PostgreSQL:
//   1. Set DATABASE_TYPE=postgresql in .env
//   2. Change the import below from './sqlite' to './pg'
//   3. Update drizzle.config.ts dialect to 'postgresql'
//   4. Run migrations against PostgreSQL
//
// Both files export identical table names and column shapes.
// All API code imports from this file — no other changes needed.

export {
  enterprises,
  users,
  smsCodes,
  simulations,
  reports,
  orders,
  agentTemplates,
  simulationTemplates,
  llmUsage,
} from './sqlite'
```

- [ ] **Step 4: Update connection factory for PG support**

Replace `web/server/database/index.ts`:

```typescript
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

  // SQLite (default)
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
```

- [ ] **Step 5: Commit**

```bash
cd D:/project/oasis
git add web/server/database/ web/package.json web/package-lock.json
git commit -m "feat(web): add PostgreSQL schema and dual-database connection factory"
```

---

## Task 4: Auth Utilities

**Files:**
- Create: `web/server/utils/id.ts`
- Create: `web/server/utils/jwt.ts`
- Create: `web/server/utils/sms.ts`
- Create: `web/server/utils/response.ts`
- Create: `web/server/utils/time.ts`
- Create: `web/tests/utils/jwt.test.ts`
- Create: `web/tests/utils/response.test.ts`

- [ ] **Step 1: Write ID generator utility**

Create `web/server/utils/id.ts`:

```typescript
import { nanoid } from 'nanoid'

export function generateId(size = 21): string {
  return nanoid(size)
}

export function generateSmsCode(): string {
  return Math.floor(100000 + Math.random() * 900000).toString()
}
```

- [ ] **Step 2: Write time utility**

Create `web/server/utils/time.ts`:

```typescript
export function now(): string {
  return new Date().toISOString()
}

export function addMinutes(minutes: number): string {
  const date = new Date()
  date.setMinutes(date.getMinutes() + minutes)
  return date.toISOString()
}

export function isExpired(isoString: string): boolean {
  return new Date(isoString) < new Date()
}
```

- [ ] **Step 3: Write JWT test**

Create `web/tests/utils/jwt.test.ts`:

```typescript
import { describe, test, expect } from 'vitest'

// We test the JWT functions directly, not through Nuxt
// Import will be done after implementation
describe('JWT Utilities', () => {
  test('signToken returns a valid JWT string', async () => {
    const { signToken } = await import('../../server/utils/jwt')
    const token = await signToken({ userId: 'u1', enterpriseId: 'e1', role: 'admin' })
    expect(token).toBeTruthy()
    expect(typeof token).toBe('string')
    expect(token.split('.')).toHaveLength(3) // JWT has 3 parts
  })

  test('verifyToken decodes a valid token', async () => {
    const { signToken, verifyToken } = await import('../../server/utils/jwt')
    const token = await signToken({ userId: 'u1', enterpriseId: 'e1', role: 'admin' })
    const payload = await verifyToken(token)
    expect(payload.userId).toBe('u1')
    expect(payload.enterpriseId).toBe('e1')
    expect(payload.role).toBe('admin')
  })

  test('verifyToken throws on invalid token', async () => {
    const { verifyToken } = await import('../../server/utils/jwt')
    await expect(verifyToken('invalid.token.here')).rejects.toThrow()
  })

  test('signRefreshToken creates a longer-lived token', async () => {
    const { signRefreshToken, verifyRefreshToken } = await import('../../server/utils/jwt')
    const token = await signRefreshToken({ userId: 'u1', enterpriseId: 'e1', role: 'user' })
    const payload = await verifyRefreshToken(token)
    expect(payload.userId).toBe('u1')
  })
})
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd D:/project/oasis/web
npx vitest run tests/utils/jwt.test.ts
```

Expected: FAIL — module `../../server/utils/jwt` not found.

- [ ] **Step 5: Implement JWT utility**

Create `web/server/utils/jwt.ts`:

```typescript
import { SignJWT, jwtVerify } from 'jose'

export interface TokenPayload {
  userId: string
  enterpriseId: string
  role: string
}

const getSecret = () => {
  // In server utils called outside of Nitro request context,
  // fall back to env var directly
  const secret = process.env.JWT_SECRET || 'dev-secret-change-in-production'
  return new TextEncoder().encode(secret)
}

export async function signToken(payload: TokenPayload): Promise<string> {
  return new SignJWT({ ...payload })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('2h')
    .sign(getSecret())
}

export async function signRefreshToken(payload: TokenPayload): Promise<string> {
  return new SignJWT({ ...payload })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('7d')
    .sign(getSecret())
}

export async function verifyToken(token: string): Promise<TokenPayload> {
  const { payload } = await jwtVerify(token, getSecret())
  return payload as unknown as TokenPayload
}

export async function verifyRefreshToken(token: string): Promise<TokenPayload> {
  const { payload } = await jwtVerify(token, getSecret())
  return payload as unknown as TokenPayload
}
```

- [ ] **Step 6: Run JWT test to verify it passes**

```bash
cd D:/project/oasis/web
npx vitest run tests/utils/jwt.test.ts
```

Expected: All 4 tests PASS.

- [ ] **Step 7: Write response utility test**

Create `web/tests/utils/response.test.ts`:

```typescript
import { describe, test, expect } from 'vitest'

describe('Response Utilities', () => {
  test('success returns code 0 with data', async () => {
    const { success } = await import('../../server/utils/response')
    const res = success({ name: 'test' })
    expect(res.code).toBe(0)
    expect(res.data.name).toBe('test')
    expect(res.message).toBe('ok')
  })

  test('error returns error code and message', async () => {
    const { error } = await import('../../server/utils/response')
    const res = error(40001, '验证码已过期')
    expect(res.code).toBe(40001)
    expect(res.data).toBeNull()
    expect(res.message).toBe('验证码已过期')
  })
})
```

- [ ] **Step 8: Run response test to verify it fails**

```bash
cd D:/project/oasis/web
npx vitest run tests/utils/response.test.ts
```

Expected: FAIL.

- [ ] **Step 9: Implement response utility**

Create `web/server/utils/response.ts`:

```typescript
interface ApiResponse<T = any> {
  code: number
  data: T | null
  message: string
}

export function success<T>(data: T, message = 'ok'): ApiResponse<T> {
  return { code: 0, data, message }
}

export function error(code: number, message: string): ApiResponse<null> {
  return { code, data: null, message }
}

// Error codes:
// 400xx — auth
// 401xx — permission
// 402xx — quota
// 500xx — server
export const ErrorCodes = {
  SMS_RATE_LIMIT: 40001,
  SMS_CODE_EXPIRED: 40002,
  SMS_CODE_INVALID: 40003,
  PHONE_NOT_FOUND: 40004,
  TOKEN_INVALID: 40101,
  TOKEN_EXPIRED: 40102,
  ENTERPRISE_SUSPENDED: 40103,
  QUOTA_EXCEEDED: 40201,
  QUOTA_EXPIRED: 40202,
  SERVER_ERROR: 50001,
} as const
```

- [ ] **Step 10: Run response test to verify it passes**

```bash
cd D:/project/oasis/web
npx vitest run tests/utils/response.test.ts
```

Expected: All 2 tests PASS.

- [ ] **Step 11: Implement SMS utility**

Create `web/server/utils/sms.ts`:

```typescript
export async function sendSms(phone: string, code: string): Promise<boolean> {
  const config = useRuntimeConfig()

  // In development or when no SMS credentials configured, log to console
  if (!config.smsAccessKey) {
    console.log(`[SMS DEV] Sending code ${code} to ${phone}`)
    return true
  }

  // Alibaba Cloud SMS API integration
  // Replace with your SMS provider's API call
  try {
    const response = await $fetch('https://dysmsapi.aliyuncs.com/', {
      method: 'POST',
      query: {
        Action: 'SendSms',
        PhoneNumbers: phone,
        SignName: 'OASIS',
        TemplateCode: 'SMS_TEMPLATE_ID',
        TemplateParam: JSON.stringify({ code }),
        AccessKeyId: config.smsAccessKey,
        // In production: add proper signature calculation
      },
    })
    return true
  } catch (err) {
    console.error('[SMS] Failed to send:', err)
    return false
  }
}
```

- [ ] **Step 12: Run all utils tests**

```bash
cd D:/project/oasis/web
npx vitest run tests/utils/
```

Expected: All 6 tests PASS.

- [ ] **Step 13: Commit**

```bash
cd D:/project/oasis
git add web/server/utils/ web/tests/
git commit -m "feat(web): add auth utilities — JWT, SMS, response helpers, ID generator"
```

---

## Task 5: Auth API Routes

**Files:**
- Create: `web/server/api/auth/sms.send.post.ts`
- Create: `web/server/api/auth/login.post.ts`
- Create: `web/server/api/auth/register.post.ts`
- Create: `web/server/api/auth/me.get.ts`
- Create: `web/server/api/auth/logout.post.ts`
- Create: `web/server/api/health.get.ts`

- [ ] **Step 1: Create SMS send endpoint**

Create `web/server/api/auth/sms.send.post.ts`:

```typescript
import { z } from 'zod'
import { eq, and, gt } from 'drizzle-orm'
import { useDB } from '~/server/database'
import { smsCodes } from '~/server/database/schema'
import { generateId, generateSmsCode } from '~/server/utils/id'
import { now, addMinutes } from '~/server/utils/time'
import { sendSms } from '~/server/utils/sms'
import { success, error, ErrorCodes } from '~/server/utils/response'

const bodySchema = z.object({
  phone: z.string().regex(/^1[3-9]\d{9}$/, '请输入有效的手机号'),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_RATE_LIMIT, parsed.error.errors[0].message)
  }

  const { phone } = parsed.data
  const db = useDB()

  // Rate limit: 60 seconds between sends
  const recentCode = await db.select()
    .from(smsCodes)
    .where(
      and(
        eq(smsCodes.phone, phone),
        gt(smsCodes.createdAt, new Date(Date.now() - 60000).toISOString())
      )
    )
    .limit(1)

  if (recentCode.length > 0) {
    return error(ErrorCodes.SMS_RATE_LIMIT, '请60秒后再试')
  }

  const code = generateSmsCode()
  await db.insert(smsCodes).values({
    id: generateId(),
    phone,
    code,
    expiresAt: addMinutes(5),
    createdAt: now(),
  })

  await sendSms(phone, code)

  return success({ sent: true })
})
```

- [ ] **Step 2: Create login endpoint**

Create `web/server/api/auth/login.post.ts`:

```typescript
import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~/server/database'
import { users, smsCodes, enterprises } from '~/server/database/schema'
import { signToken, signRefreshToken } from '~/server/utils/jwt'
import { now } from '~/server/utils/time'
import { isExpired } from '~/server/utils/time'
import { success, error, ErrorCodes } from '~/server/utils/response'

const bodySchema = z.object({
  phone: z.string().regex(/^1[3-9]\d{9}$/),
  code: z.string().length(6),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_CODE_INVALID, '参数错误')
  }

  const { phone, code } = parsed.data
  const db = useDB()

  // Verify SMS code
  const smsRecord = await db.select()
    .from(smsCodes)
    .where(
      and(
        eq(smsCodes.phone, phone),
        eq(smsCodes.code, code),
        eq(smsCodes.used, 0)
      )
    )
    .orderBy(smsCodes.createdAt)
    .limit(1)

  if (smsRecord.length === 0) {
    return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
  }

  if (isExpired(smsRecord[0].expiresAt)) {
    return error(ErrorCodes.SMS_CODE_EXPIRED, '验证码已过期')
  }

  // Mark code as used
  await db.update(smsCodes)
    .set({ used: 1 })
    .where(eq(smsCodes.id, smsRecord[0].id))

  // Find user
  const userRecord = await db.select()
    .from(users)
    .where(eq(users.phone, phone))
    .limit(1)

  if (userRecord.length === 0) {
    return error(ErrorCodes.PHONE_NOT_FOUND, '用户不存在，请先注册')
  }

  const user = userRecord[0]

  // Update last login time
  await db.update(users)
    .set({ lastLoginAt: now() })
    .where(eq(users.id, user.id))

  // Get enterprise info
  const enterpriseRecord = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, user.enterpriseId))
    .limit(1)

  // Generate tokens
  const tokenPayload = {
    userId: user.id,
    enterpriseId: user.enterpriseId,
    role: user.role,
  }
  const token = await signToken(tokenPayload)
  const refreshToken = await signRefreshToken(tokenPayload)

  return success({
    token,
    refreshToken,
    user: {
      id: user.id,
      phone: user.phone,
      name: user.name,
      role: user.role,
    },
    enterprise: enterpriseRecord[0] || null,
  })
})
```

- [ ] **Step 3: Create register endpoint**

Create `web/server/api/auth/register.post.ts`:

```typescript
import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~/server/database'
import { users, smsCodes, enterprises } from '~/server/database/schema'
import { generateId } from '~/server/utils/id'
import { signToken, signRefreshToken } from '~/server/utils/jwt'
import { now, isExpired } from '~/server/utils/time'
import { success, error, ErrorCodes } from '~/server/utils/response'

const bodySchema = z.object({
  phone: z.string().regex(/^1[3-9]\d{9}$/),
  code: z.string().length(6),
  enterpriseName: z.string().min(2).max(50),
  userName: z.string().min(2).max(20),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.SMS_CODE_INVALID, parsed.error.errors[0].message)
  }

  const { phone, code, enterpriseName, userName } = parsed.data
  const db = useDB()

  // Verify SMS code
  const smsRecord = await db.select()
    .from(smsCodes)
    .where(
      and(
        eq(smsCodes.phone, phone),
        eq(smsCodes.code, code),
        eq(smsCodes.used, 0)
      )
    )
    .orderBy(smsCodes.createdAt)
    .limit(1)

  if (smsRecord.length === 0) {
    return error(ErrorCodes.SMS_CODE_INVALID, '验证码错误')
  }

  if (isExpired(smsRecord[0].expiresAt)) {
    return error(ErrorCodes.SMS_CODE_EXPIRED, '验证码已过期')
  }

  // Mark code as used
  await db.update(smsCodes)
    .set({ used: 1 })
    .where(eq(smsCodes.id, smsRecord[0].id))

  // Check if phone already registered
  const existingUser = await db.select()
    .from(users)
    .where(eq(users.phone, phone))
    .limit(1)

  if (existingUser.length > 0) {
    return error(ErrorCodes.SMS_CODE_INVALID, '该手机号已注册')
  }

  // Create enterprise
  const enterpriseId = generateId()
  const timestamp = now()
  await db.insert(enterprises).values({
    id: enterpriseId,
    name: enterpriseName,
    contactPhone: phone,
    simQuota: 3, // Free trial: 3 simulations
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  // Create user (admin of the enterprise)
  const userId = generateId()
  await db.insert(users).values({
    id: userId,
    enterpriseId,
    phone,
    name: userName,
    role: 'admin',
    lastLoginAt: timestamp,
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  // Generate tokens
  const tokenPayload = { userId, enterpriseId, role: 'admin' }
  const token = await signToken(tokenPayload)
  const refreshToken = await signRefreshToken(tokenPayload)

  return success({
    token,
    refreshToken,
    user: { id: userId, phone, name: userName, role: 'admin' },
    enterprise: {
      id: enterpriseId,
      name: enterpriseName,
      planType: 'basic',
      simQuota: 3,
    },
  })
})
```

- [ ] **Step 4: Create me endpoint**

Create `web/server/api/auth/me.get.ts`:

```typescript
import { eq } from 'drizzle-orm'
import { useDB } from '~/server/database'
import { users, enterprises } from '~/server/database/schema'
import { success, error, ErrorCodes } from '~/server/utils/response'

export default defineEventHandler(async (event) => {
  const user = event.context.user
  if (!user) {
    return error(ErrorCodes.TOKEN_INVALID, '未登录')
  }

  const db = useDB()

  const userRecord = await db.select()
    .from(users)
    .where(eq(users.id, user.userId))
    .limit(1)

  if (userRecord.length === 0) {
    return error(ErrorCodes.TOKEN_INVALID, '用户不存在')
  }

  const enterpriseRecord = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, user.enterpriseId))
    .limit(1)

  return success({
    user: {
      id: userRecord[0].id,
      phone: userRecord[0].phone,
      name: userRecord[0].name,
      role: userRecord[0].role,
    },
    enterprise: enterpriseRecord[0] || null,
  })
})
```

- [ ] **Step 5: Create logout endpoint**

Create `web/server/api/auth/logout.post.ts`:

```typescript
import { success } from '~/server/utils/response'

export default defineEventHandler(async () => {
  // JWT is stateless — client discards the token.
  // If refresh token revocation is needed later, add a blocklist table.
  return success({ loggedOut: true })
})
```

- [ ] **Step 6: Create health check endpoint**

Create `web/server/api/health.get.ts`:

```typescript
import { success } from '~/server/utils/response'

export default defineEventHandler(async () => {
  return success({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '0.1.0',
  })
})
```

- [ ] **Step 7: Verify endpoints compile by starting dev server**

```bash
cd D:/project/oasis/web
npm run dev
```

In another terminal test health endpoint:

```bash
curl http://localhost:3000/api/health
```

Expected: `{"code":0,"data":{"status":"healthy",...},"message":"ok"}`

- [ ] **Step 8: Commit**

```bash
cd D:/project/oasis
git add web/server/api/
git commit -m "feat(web): add auth API routes — SMS, login, register, me, logout, health"
```

---

## Task 6: Server Middleware

**Files:**
- Create: `web/server/middleware/01.auth.ts`
- Create: `web/server/middleware/02.enterprise.ts`

- [ ] **Step 1: Create auth middleware**

Create `web/server/middleware/01.auth.ts`:

```typescript
import { verifyToken } from '~/server/utils/jwt'

// Routes that don't require authentication
const publicPaths = [
  '/api/auth/sms/send',
  '/api/auth/login',
  '/api/auth/register',
  '/api/health',
  '/api/internal/',
]

export default defineEventHandler(async (event) => {
  const path = getRequestURL(event).pathname

  // Skip non-API routes (pages, assets)
  if (!path.startsWith('/api/')) return

  // Skip public API routes
  if (publicPaths.some(p => path.startsWith(p))) return

  const authHeader = getRequestHeader(event, 'authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    event.context.user = null
    throw createError({ statusCode: 401, message: '未登录' })
  }

  try {
    const token = authHeader.slice(7)
    const payload = await verifyToken(token)
    event.context.user = payload
  } catch {
    event.context.user = null
    throw createError({ statusCode: 401, message: 'Token 无效或已过期' })
  }
})
```

- [ ] **Step 2: Create enterprise isolation middleware**

Create `web/server/middleware/02.enterprise.ts`:

```typescript
import { eq } from 'drizzle-orm'
import { useDB } from '~/server/database'
import { enterprises } from '~/server/database/schema'

export default defineEventHandler(async (event) => {
  const path = getRequestURL(event).pathname

  // Only apply to authenticated API routes
  if (!path.startsWith('/api/') || !event.context.user) return

  const db = useDB()
  const enterpriseId = event.context.user.enterpriseId

  // Verify enterprise is active
  const enterprise = await db.select()
    .from(enterprises)
    .where(eq(enterprises.id, enterpriseId))
    .limit(1)

  if (enterprise.length === 0 || enterprise[0].status === 'suspended') {
    throw createError({ statusCode: 403, message: '企业账户已被暂停' })
  }

  // Attach enterprise to context for downstream handlers
  event.context.enterprise = enterprise[0]
})
```

- [ ] **Step 3: Add TypeScript type augmentation for event context**

Create `web/server/types.ts`:

```typescript
import type { TokenPayload } from '~/server/utils/jwt'

declare module 'h3' {
  interface H3EventContext {
    user: TokenPayload | null
    enterprise: {
      id: string
      name: string
      planType: string
      simQuota: number
      quotaExpires: string | null
    } | null
  }
}
```

- [ ] **Step 4: Verify middleware works by testing protected endpoint**

Start dev server and test:

```bash
# Should fail with 401
curl http://localhost:3000/api/auth/me

# Health should still work (public)
curl http://localhost:3000/api/health
```

Expected: `/api/auth/me` returns 401, `/api/health` returns 200.

- [ ] **Step 5: Commit**

```bash
cd D:/project/oasis
git add web/server/middleware/ web/server/types.ts
git commit -m "feat(web): add auth and enterprise isolation middleware"
```

---

## Task 7: Naive UI Theme & Layouts

**Files:**
- Create: `web/plugins/naive-ui.ts`
- Create: `web/layouts/default.vue`
- Create: `web/layouts/guest.vue`
- Create: `web/components/layout/Sidebar.vue`
- Create: `web/components/layout/Header.vue`
- Create: `web/assets/css/main.css`
- Modify: `web/app.vue`

- [ ] **Step 1: Create Naive UI plugin for SSR**

Create `web/plugins/naive-ui.ts`:

```typescript
import { setup } from '@css-render/vue3-ssr'
import { defineNuxtPlugin } from '#app'

export default defineNuxtPlugin((nuxtApp) => {
  if (import.meta.server) {
    const { collect } = setup(nuxtApp.vueApp)
    nuxtApp.ssrContext!.head = nuxtApp.ssrContext!.head || []
    nuxtApp.hooks.hook('app:rendered', () => {
      const cssContent = collect()
      if (cssContent) {
        nuxtApp.ssrContext!.head.push(cssContent)
      }
    })
  }
})
```

- [ ] **Step 2: Create global CSS with tech theme variables**

Create `web/assets/css/main.css`:

```css
:root {
  --bg-primary: #0a0e1a;
  --bg-secondary: #111827;
  --bg-card: #1a1f36;
  --bg-hover: #232946;
  --border-color: #2a3158;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-gradient: linear-gradient(135deg, #3b82f6, #8b5cf6);
  --success: #22c55e;
  --warning: #f59e0b;
  --error: #ef4444;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #__nuxt {
  height: 100%;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--accent-blue);
}
```

- [ ] **Step 3: Update nuxt.config.ts to include CSS**

Add to `web/nuxt.config.ts` at the top level:

```typescript
css: ['~/assets/css/main.css'],
```

- [ ] **Step 4: Create Sidebar component**

Create `web/components/layout/Sidebar.vue`:

```vue
<template>
  <div class="sidebar">
    <div class="sidebar-logo">
      <Icon name="carbon:analytics" size="28" />
      <span class="logo-text">OASIS</span>
    </div>

    <nav class="sidebar-nav">
      <NuxtLink
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        active-class="nav-item--active"
      >
        <Icon :name="item.icon" size="20" />
        <span>{{ item.label }}</span>
      </NuxtLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
const menuItems = [
  { path: '/dashboard', icon: 'carbon:dashboard', label: '工作台' },
  { path: '/simulations', icon: 'carbon:play-outline', label: '模拟任务' },
  { path: '/reports', icon: 'carbon:report', label: '报告中心' },
  { path: '/templates', icon: 'carbon:template', label: '模板管理' },
  { path: '/settings', icon: 'carbon:settings', label: '企业设置' },
]
</script>

<style scoped>
.sidebar {
  width: 220px;
  height: 100%;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-logo {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--border-color);
  color: var(--accent-blue);
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}

.sidebar-nav {
  padding: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item--active {
  background: rgba(59, 130, 246, 0.1);
  color: var(--accent-blue);
}
</style>
```

- [ ] **Step 5: Create Header component**

Create `web/components/layout/Header.vue`:

```vue
<template>
  <header class="app-header">
    <div class="header-left">
      <span class="enterprise-name">{{ enterpriseName }}</span>
    </div>
    <div class="header-right">
      <div class="quota-info" v-if="quota !== null">
        <Icon name="carbon:cube" size="16" />
        <span>剩余 {{ quota }} 次</span>
      </div>
      <div class="user-menu" @click="handleLogout">
        <Icon name="carbon:user-avatar" size="20" />
        <span>{{ userName }}</span>
        <Icon name="carbon:logout" size="16" class="logout-icon" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const props = defineProps<{
  enterpriseName: string
  userName: string
  quota: number | null
}>()

const emit = defineEmits<{
  logout: []
}>()

function handleLogout() {
  emit('logout')
}
</script>

<style scoped>
.app-header {
  height: 56px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.enterprise-name {
  font-size: 14px;
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.quota-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--accent-blue);
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.user-menu:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.logout-icon {
  color: var(--text-secondary);
}
</style>
```

- [ ] **Step 6: Create default layout (authenticated pages)**

Create `web/layouts/default.vue`:

```vue
<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div class="app-layout">
        <LayoutSidebar />
        <div class="app-main">
          <LayoutHeader
            :enterprise-name="authStore.enterprise?.name || ''"
            :user-name="authStore.user?.name || ''"
            :quota="authStore.enterprise?.simQuota ?? null"
            @logout="handleLogout"
          />
          <main class="app-content">
            <slot />
          </main>
          <footer class="app-footer">
            <span>{{ authStore.enterprise?.planType || 'basic' }} 版</span>
            <span>·</span>
            <span>剩余 {{ authStore.enterprise?.simQuota ?? 0 }} 次模拟</span>
          </footer>
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { useAuthStore } from '~/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#3b82f6',
    primaryColorHover: '#60a5fa',
    primaryColorPressed: '#2563eb',
    bodyColor: '#0a0e1a',
    cardColor: '#1a1f36',
    modalColor: '#1a1f36',
    popoverColor: '#1a1f36',
    borderColor: '#2a3158',
    textColorBase: '#e2e8f0',
    inputColor: '#111827',
    borderRadius: '8px',
  },
  Button: {
    borderRadiusMedium: '8px',
  },
  Card: {
    borderRadius: '12px',
    borderColor: '#2a3158',
  },
  Input: {
    borderRadius: '8px',
  },
}

async function handleLogout() {
  authStore.logout()
  await router.push('/login')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.app-footer {
  height: 36px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
}
</style>
```

- [ ] **Step 7: Create guest layout (login/register)**

Create `web/layouts/guest.vue`:

```vue
<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div class="guest-layout">
        <div class="guest-bg">
          <div class="grid-lines"></div>
        </div>
        <div class="guest-container">
          <div class="guest-logo">
            <Icon name="carbon:analytics" size="36" />
            <span>OASIS</span>
          </div>
          <p class="guest-tagline">AI 社交模拟平台</p>
          <slot />
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { NConfigProvider, NMessageProvider } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#3b82f6',
    primaryColorHover: '#60a5fa',
    primaryColorPressed: '#2563eb',
    bodyColor: '#0a0e1a',
    cardColor: '#1a1f36',
    borderColor: '#2a3158',
    textColorBase: '#e2e8f0',
    inputColor: '#111827',
    borderRadius: '8px',
  },
}
</script>

<style scoped>
.guest-layout {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.guest-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 60%);
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}

.guest-container {
  position: relative;
  z-index: 1;
  width: 400px;
  text-align: center;
}

.guest-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 32px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}

.guest-logo :deep(svg) {
  color: var(--accent-blue);
}

.guest-tagline {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 32px;
}
</style>
```

- [ ] **Step 8: Update app.vue**

Replace `web/app.vue`:

```vue
<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
```

- [ ] **Step 9: Verify layouts render by starting dev server**

```bash
cd D:/project/oasis/web
npm run dev
```

Open `http://localhost:3000` — should see dark background. No errors in console.

- [ ] **Step 10: Commit**

```bash
cd D:/project/oasis
git add web/plugins/ web/layouts/ web/components/ web/assets/ web/app.vue web/nuxt.config.ts
git commit -m "feat(web): add Naive UI dark theme, sidebar layout, header, and guest layout"
```

---

## Task 8: Auth Store & Navigation Guard

**Files:**
- Create: `web/stores/auth.ts`
- Create: `web/composables/useApi.ts`
- Create: `web/middleware/auth.global.ts`

- [ ] **Step 1: Create API composable**

Create `web/composables/useApi.ts`:

```typescript
export function useApi() {
  const authStore = useAuthStore()

  async function $api<T = any>(url: string, options: any = {}): Promise<T> {
    const headers: Record<string, string> = { ...options.headers }

    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await $fetch(url, {
      ...options,
      headers,
    })

    return response as T
  }

  return { $api }
}
```

- [ ] **Step 2: Create auth store**

Create `web/stores/auth.ts`:

```typescript
import { defineStore } from 'pinia'

interface User {
  id: string
  phone: string
  name: string | null
  role: string
}

interface Enterprise {
  id: string
  name: string
  planType: string
  simQuota: number
  quotaExpires?: string | null
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  enterprise: Enterprise | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: null,
    refreshToken: null,
    user: null,
    enterprise: null,
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
  },

  actions: {
    setAuth(data: {
      token: string
      refreshToken: string
      user: User
      enterprise: Enterprise
    }) {
      this.token = data.token
      this.refreshToken = data.refreshToken
      this.user = data.user
      this.enterprise = data.enterprise
    },

    logout() {
      this.token = null
      this.refreshToken = null
      this.user = null
      this.enterprise = null
    },

    async fetchMe() {
      if (!this.token) return

      try {
        const res = await $fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${this.token}` },
        })
        const data = (res as any).data
        if (data) {
          this.user = data.user
          this.enterprise = data.enterprise
        }
      } catch {
        this.logout()
      }
    },
  },

  persist: {
    storage: piniaPluginPersistedstate.localStorage(),
  },
})
```

- [ ] **Step 3: Install Pinia persisted state plugin**

```bash
cd D:/project/oasis/web
npm install pinia-plugin-persistedstate
```

Update `web/nuxt.config.ts` modules array:

```typescript
modules: [
  '@pinia/nuxt',
  '@vueuse/nuxt',
  '@nuxt/icon',
  'pinia-plugin-persistedstate/nuxt',
],
```

- [ ] **Step 4: Create navigation guard**

Create `web/middleware/auth.global.ts`:

```typescript
export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore()

  const publicPages = ['/login', '/register']
  const isPublic = publicPages.includes(to.path)

  if (!isPublic && !authStore.isLoggedIn) {
    return navigateTo('/login')
  }

  if (isPublic && authStore.isLoggedIn) {
    return navigateTo('/dashboard')
  }
})
```

- [ ] **Step 5: Commit**

```bash
cd D:/project/oasis
git add web/stores/ web/composables/ web/middleware/ web/nuxt.config.ts web/package.json web/package-lock.json
git commit -m "feat(web): add auth store with persistence and navigation guard"
```

---

## Task 9: Login & Register Pages

**Files:**
- Create: `web/pages/login.vue`
- Create: `web/pages/register.vue`

- [ ] **Step 1: Create login page**

Create `web/pages/login.vue`:

```vue
<template>
  <div>
    <NCard class="auth-card">
      <h2 class="auth-title">登录</h2>

      <NForm ref="formRef" :model="form" :rules="rules">
        <NFormItem path="phone" label="手机号">
          <NInput v-model:value="form.phone" placeholder="请输入手机号" maxlength="11" />
        </NFormItem>

        <NFormItem path="code" label="验证码">
          <div class="code-row">
            <NInput v-model:value="form.code" placeholder="请输入验证码" maxlength="6" />
            <NButton
              :disabled="countdown > 0 || !isPhoneValid"
              :loading="sendingCode"
              @click="sendCode"
              class="code-btn"
            >
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </NButton>
          </div>
        </NFormItem>

        <NButton
          type="primary"
          block
          :loading="submitting"
          @click="handleLogin"
          class="submit-btn"
        >
          登录
        </NButton>
      </NForm>

      <div class="auth-footer">
        还没有账号？<NuxtLink to="/register" class="auth-link">立即注册</NuxtLink>
      </div>
    </NCard>
  </div>
</template>

<script setup lang="ts">
import { NCard, NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'

definePageMeta({ layout: 'guest' })

const authStore = useAuthStore()
const router = useRouter()
const message = useMessage()

const form = reactive({ phone: '', code: '' })
const sendingCode = ref(false)
const submitting = ref(false)
const countdown = ref(0)

const isPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone))

const rules = {
  phone: { required: true, message: '请输入手机号', trigger: 'blur' },
  code: { required: true, message: '请输入验证码', trigger: 'blur' },
}

async function sendCode() {
  if (!isPhoneValid.value) return
  sendingCode.value = true
  try {
    const res = await $fetch('/api/auth/sms/send', {
      method: 'POST',
      body: { phone: form.phone },
    })
    if ((res as any).code === 0) {
      message.success('验证码已发送')
      countdown.value = 60
      const timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      message.error((res as any).message)
    }
  } catch (err: any) {
    message.error('发送失败，请稍后重试')
  } finally {
    sendingCode.value = false
  }
}

async function handleLogin() {
  if (!form.phone || !form.code) return
  submitting.value = true
  try {
    const res = await $fetch('/api/auth/login', {
      method: 'POST',
      body: form,
    })
    const data = res as any
    if (data.code === 0) {
      authStore.setAuth(data.data)
      message.success('登录成功')
      await router.push('/dashboard')
    } else {
      message.error(data.message)
    }
  } catch (err: any) {
    message.error('登录失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-card {
  width: 100%;
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
  padding: 12px;
}

.auth-title {
  font-size: 24px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 24px;
  color: var(--text-primary);
}

.code-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.code-btn {
  flex-shrink: 0;
  width: 120px;
}

.submit-btn {
  margin-top: 8px;
  height: 42px;
  font-size: 15px;
}

.auth-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: var(--text-secondary);
}

.auth-link {
  color: var(--accent-blue);
  text-decoration: none;
}

.auth-link:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 2: Create register page**

Create `web/pages/register.vue`:

```vue
<template>
  <div>
    <NCard class="auth-card">
      <h2 class="auth-title">企业注册</h2>

      <NForm ref="formRef" :model="form" :rules="rules">
        <NFormItem path="enterpriseName" label="企业名称">
          <NInput v-model:value="form.enterpriseName" placeholder="请输入企业名称" />
        </NFormItem>

        <NFormItem path="userName" label="您的姓名">
          <NInput v-model:value="form.userName" placeholder="请输入姓名" />
        </NFormItem>

        <NFormItem path="phone" label="手机号">
          <NInput v-model:value="form.phone" placeholder="请输入手机号" maxlength="11" />
        </NFormItem>

        <NFormItem path="code" label="验证码">
          <div class="code-row">
            <NInput v-model:value="form.code" placeholder="请输入验证码" maxlength="6" />
            <NButton
              :disabled="countdown > 0 || !isPhoneValid"
              :loading="sendingCode"
              @click="sendCode"
              class="code-btn"
            >
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </NButton>
          </div>
        </NFormItem>

        <NButton
          type="primary"
          block
          :loading="submitting"
          @click="handleRegister"
          class="submit-btn"
        >
          注册并登录
        </NButton>
      </NForm>

      <div class="auth-footer">
        已有账号？<NuxtLink to="/login" class="auth-link">去登录</NuxtLink>
      </div>
    </NCard>
  </div>
</template>

<script setup lang="ts">
import { NCard, NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'

definePageMeta({ layout: 'guest' })

const authStore = useAuthStore()
const router = useRouter()
const message = useMessage()

const form = reactive({
  enterpriseName: '',
  userName: '',
  phone: '',
  code: '',
})
const sendingCode = ref(false)
const submitting = ref(false)
const countdown = ref(0)

const isPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone))

const rules = {
  enterpriseName: { required: true, message: '请输入企业名称', trigger: 'blur' },
  userName: { required: true, message: '请输入姓名', trigger: 'blur' },
  phone: { required: true, message: '请输入手机号', trigger: 'blur' },
  code: { required: true, message: '请输入验证码', trigger: 'blur' },
}

async function sendCode() {
  if (!isPhoneValid.value) return
  sendingCode.value = true
  try {
    const res = await $fetch('/api/auth/sms/send', {
      method: 'POST',
      body: { phone: form.phone },
    })
    if ((res as any).code === 0) {
      message.success('验证码已发送')
      countdown.value = 60
      const timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      message.error((res as any).message)
    }
  } catch {
    message.error('发送失败，请稍后重试')
  } finally {
    sendingCode.value = false
  }
}

async function handleRegister() {
  if (!form.enterpriseName || !form.userName || !form.phone || !form.code) return
  submitting.value = true
  try {
    const res = await $fetch('/api/auth/register', {
      method: 'POST',
      body: form,
    })
    const data = res as any
    if (data.code === 0) {
      authStore.setAuth(data.data)
      message.success('注册成功')
      await router.push('/dashboard')
    } else {
      message.error(data.message)
    }
  } catch {
    message.error('注册失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-card {
  width: 100%;
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
  padding: 12px;
}

.auth-title {
  font-size: 24px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 24px;
  color: var(--text-primary);
}

.code-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.code-btn {
  flex-shrink: 0;
  width: 120px;
}

.submit-btn {
  margin-top: 8px;
  height: 42px;
  font-size: 15px;
}

.auth-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: var(--text-secondary);
}

.auth-link {
  color: var(--accent-blue);
  text-decoration: none;
}

.auth-link:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 3: Create index redirect**

Create `web/pages/index.vue`:

```vue
<script setup lang="ts">
definePageMeta({ layout: false })
navigateTo('/dashboard')
</script>
```

- [ ] **Step 4: Verify login page renders**

```bash
cd D:/project/oasis/web
npm run dev
```

Open `http://localhost:3000/login` — should see the dark-themed login card with OASIS logo, phone input, verification code input, and login button.

- [ ] **Step 5: Commit**

```bash
cd D:/project/oasis
git add web/pages/
git commit -m "feat(web): add login, register, and index pages"
```

---

## Task 10: Dashboard Shell Page

**Files:**
- Create: `web/pages/dashboard.vue`
- Create: `web/components/common/StatCard.vue`

- [ ] **Step 1: Create StatCard component**

Create `web/components/common/StatCard.vue`:

```vue
<template>
  <div class="stat-card">
    <div class="stat-icon" :style="{ background: iconBg }">
      <Icon :name="icon" size="22" />
    </div>
    <div class="stat-info">
      <span class="stat-label">{{ label }}</span>
      <span class="stat-value">{{ value }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: string
  label: string
  value: string | number
  iconBg?: string
}>()
</script>

<style scoped>
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: border-color 0.2s;
}

.stat-card:hover {
  border-color: var(--accent-blue);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  background: rgba(59, 130, 246, 0.15);
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}
</style>
```

- [ ] **Step 2: Create dashboard page**

Create `web/pages/dashboard.vue`:

```vue
<template>
  <div class="dashboard">
    <h1 class="page-title">工作台</h1>

    <div class="stats-grid">
      <StatCard
        icon="carbon:play-outline"
        label="模拟总次数"
        :value="stats.totalSims"
        icon-bg="rgba(59, 130, 246, 0.15)"
      />
      <StatCard
        icon="carbon:checkmark-outline"
        label="已完成"
        :value="stats.completedSims"
        icon-bg="rgba(34, 197, 94, 0.15)"
      />
      <StatCard
        icon="carbon:cube"
        label="剩余配额"
        :value="stats.remainingQuota"
        icon-bg="rgba(139, 92, 246, 0.15)"
      />
      <StatCard
        icon="carbon:report"
        label="报告数量"
        :value="stats.totalReports"
        icon-bg="rgba(245, 158, 11, 0.15)"
      />
    </div>

    <div class="dashboard-sections">
      <div class="section">
        <div class="section-header">
          <h2>快速开始</h2>
        </div>
        <div class="quick-actions">
          <NuxtLink to="/simulations/create" class="action-card">
            <Icon name="carbon:add-alt" size="24" />
            <span>新建模拟</span>
          </NuxtLink>
          <NuxtLink to="/reports" class="action-card">
            <Icon name="carbon:report" size="24" />
            <span>查看报告</span>
          </NuxtLink>
          <NuxtLink to="/templates" class="action-card">
            <Icon name="carbon:template" size="24" />
            <span>模板管理</span>
          </NuxtLink>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>最近任务</h2>
          <NuxtLink to="/simulations" class="view-all">查看全部</NuxtLink>
        </div>
        <div class="empty-state" v-if="recentSims.length === 0">
          <Icon name="carbon:no-image" size="48" />
          <p>暂无模拟任务</p>
          <NuxtLink to="/simulations/create">
            <NButton type="primary" size="small">创建第一个模拟</NButton>
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'

const authStore = useAuthStore()

const stats = computed(() => ({
  totalSims: 0,
  completedSims: 0,
  remainingQuota: authStore.enterprise?.simQuota ?? 0,
  totalReports: 0,
}))

const recentSims = ref([])
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.dashboard-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h2 {
  font-size: 16px;
  font-weight: 600;
}

.view-all {
  font-size: 13px;
  color: var(--accent-blue);
  text-decoration: none;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  cursor: pointer;
}

.action-card:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  background: var(--bg-hover);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
}
</style>
```

- [ ] **Step 3: Create placeholder pages for navigation**

Create `web/pages/simulations/index.vue`:

```vue
<template>
  <div>
    <h1 class="page-title">模拟任务</h1>
    <p style="color: var(--text-secondary)">将在 Plan 4 中实现</p>
  </div>
</template>

<style scoped>
.page-title { font-size: 24px; font-weight: 600; margin-bottom: 24px; }
</style>
```

Create `web/pages/reports/index.vue`, `web/pages/templates/index.vue`, `web/pages/settings/index.vue` with the same pattern, changing the title accordingly ("报告中心", "模板管理", "企业设置").

- [ ] **Step 4: Verify full app flow**

```bash
cd D:/project/oasis/web
npm run dev
```

Test flow:
1. Open `http://localhost:3000` — redirected to `/login`
2. Login page shows dark theme with OASIS logo
3. Navigate to `/register` — registration form renders
4. After login (will need to manually insert test data or use the API), `/dashboard` shows stats grid and quick actions
5. Sidebar navigation works between all pages

- [ ] **Step 5: Commit**

```bash
cd D:/project/oasis
git add web/pages/ web/components/common/
git commit -m "feat(web): add dashboard shell and placeholder pages with stat cards"
```

---

## Task 11: End-to-End Auth Flow Verification

**Files:**
- Create: `web/tests/e2e/auth-flow.test.ts`

- [ ] **Step 1: Write E2E auth flow test**

Create `web/tests/e2e/auth-flow.test.ts`:

```typescript
import { describe, test, expect, beforeAll } from 'vitest'
import Database from 'better-sqlite3'
import { resolve } from 'path'
import { mkdirSync, existsSync } from 'fs'

// Test the auth flow by calling the API endpoints directly
// This test uses a separate test database

const TEST_DB = resolve(process.cwd(), 'data/test-oasis.db')
const BASE_URL = 'http://localhost:3000'

describe('Auth Flow E2E', () => {
  // These tests require the dev server to be running
  // Run: npm run dev (in another terminal)
  // Then: npx vitest run tests/e2e/auth-flow.test.ts

  test('health check returns ok', async () => {
    const res = await fetch(`${BASE_URL}/api/health`)
    const data = await res.json()
    expect(data.code).toBe(0)
    expect(data.data.status).toBe('healthy')
  })

  test('SMS send returns success for valid phone', async () => {
    const res = await fetch(`${BASE_URL}/api/auth/sms/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '13800138000' }),
    })
    const data = await res.json()
    expect(data.code).toBe(0)
  })

  test('SMS send rejects invalid phone', async () => {
    const res = await fetch(`${BASE_URL}/api/auth/sms/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '123' }),
    })
    const data = await res.json()
    expect(data.code).not.toBe(0)
  })

  test('login rejects non-existent user', async () => {
    const res = await fetch(`${BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '13800138001', code: '000000' }),
    })
    const data = await res.json()
    expect(data.code).not.toBe(0)
  })

  test('me endpoint rejects unauthenticated request', async () => {
    const res = await fetch(`${BASE_URL}/api/auth/me`)
    expect(res.status).toBe(401)
  })
})
```

- [ ] **Step 2: Run E2E tests (with dev server running)**

In terminal 1:
```bash
cd D:/project/oasis/web
npm run dev
```

In terminal 2:
```bash
cd D:/project/oasis/web
npx vitest run tests/e2e/auth-flow.test.ts
```

Expected: All 5 tests PASS.

- [ ] **Step 3: Run all tests**

```bash
cd D:/project/oasis/web
npx vitest run
```

Expected: All tests pass (utils + e2e).

- [ ] **Step 4: Final commit for Plan 1**

```bash
cd D:/project/oasis
git add web/tests/
git commit -m "test(web): add E2E auth flow tests

Plan 1 (Web Foundation & Auth) complete:
- Nuxt 3 project with Naive UI dark theme
- Drizzle ORM with SQLite/PostgreSQL dual support
- JWT auth with SMS verification code
- Server middleware for auth and enterprise isolation
- Login, register, and dashboard pages
- Navigation guard and auth store with persistence"
```

---

## Summary

After completing Plan 1, you will have:

| Component | Status |
|-----------|--------|
| Nuxt 3 project scaffold | Done |
| Database (9 tables, SQLite + PG ready) | Done |
| Auth system (SMS + JWT) | Done |
| Server middleware (auth + enterprise isolation) | Done |
| Dark tech-themed UI (layouts + components) | Done |
| Login / Register pages | Done |
| Dashboard shell | Done |
| Navigation guard + auth store | Done |
| Placeholder pages for all routes | Done |

**Next:** Plan 2 (Simulation Engine) and Plan 3 (Platform Adaptations) can be started in parallel.
