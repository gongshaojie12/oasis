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

export const llmKeys = pgTable('llm_keys', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  provider: text('provider').notNull(),
  encryptedKey: text('encrypted_key').notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const operationLogs = pgTable('operation_logs', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  userId: text('user_id').notNull().references(() => users.id),
  action: text('action').notNull(),
  resourceType: text('resource_type').notNull(),
  resourceId: text('resource_id'),
  details: text('details'),
  createdAt: text('created_at').notNull(),
})

export const personaGenomes = pgTable('persona_genomes', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  sourceType: text('source_type').notNull(),
  genomeData: text('genome_data').notNull(),
  tags: text('tags'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const genomeBatches = pgTable('genome_batches', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  seedGenomeIds: text('seed_genome_ids').notNull(),
  targetCount: integer('target_count').notNull(),
  mutationRate: real('mutation_rate').default(0.15).notNull(),
  strategy: text('strategy').default('crossover').notNull(),
  status: text('status').default('pending').notNull(),
  resultGenomeIds: text('result_genome_ids'),
  diversity: real('diversity'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const analysisReports = pgTable('analysis_reports', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  status: text('status').default('pending').notNull(),
  analystReports: text('analyst_reports'),
  debateLog: text('debate_log'),
  finalReport: text('final_report'),
  chartData: text('chart_data'),
  timelineData: text('timeline_data'),
  engineTaskId: text('engine_task_id'),
  createdAt: text('created_at').notNull(),
  completedAt: text('completed_at'),
})

export const reportComparisons = pgTable('report_comparisons', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  reportIds: text('report_ids').notNull(),
  comparisonData: text('comparison_data'),
  createdAt: text('created_at').notNull(),
})

export const knowledgeGraphs = pgTable('knowledge_graphs', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  description: text('description'),
  graphData: text('graph_data').notNull(),
  nodeCount: integer('node_count').default(0).notNull(),
  edgeCount: integer('edge_count').default(0).notNull(),
  metadata: text('metadata'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})
