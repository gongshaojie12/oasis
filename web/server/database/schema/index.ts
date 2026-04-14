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
  llmKeys,
  operationLogs,
} from './sqlite'
