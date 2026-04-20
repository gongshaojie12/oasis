# P3-1 Mission Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Dashboard into an adaptive "Mission Control" center that switches views based on simulation lifecycle stages (Prepare/Launch/Monitor/Analyze), shows health indicators, and provides contextual quick actions.

**Architecture:** Dashboard page gets a lifecycle-aware layout with MissionControl, HealthIndicator, and QuickActions components. A new health API endpoint on engine + Nuxt proxy provides real-time sim health metrics. The dashboard auto-detects active simulations and shows the appropriate lifecycle stage.

**Tech Stack:** Vue 3 + Naive UI + ECharts (frontend), Nuxt 4/h3 (server API), FastAPI (engine health endpoint)

---

### Task 1: Engine — Health Endpoint + i18n Keys

**Files:**
- Modify: `engine/main.py` (add SimHealthRequest model + endpoint)
- Modify: `web/locales/zh-CN.json` (add mission control keys)
- Modify: `web/locales/en-US.json` (add mission control keys)

- [ ] **Step 1: Add health request model and endpoint to engine/main.py**

Add request model after ComposerEstimateRequest:

```python
class SimHealthRequest(BaseModel):
    db_path: str
    num_agents: int = 10
    num_steps: int = 5
    current_step: int = 0
```

Add endpoint at end of file:

```python
@app.post(
    "/engine/simulations/health",
    dependencies=[Depends(verify_internal_key)],
)
async def simulation_health(body: SimHealthRequest):
    import sqlite3

    try:
        conn = sqlite3.connect(body.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        total_agents = body.num_agents
        traces = cursor.execute("SELECT DISTINCT agent_id FROM trace").fetchall()
        active_agents = len(traces)
        agent_activity = round(active_agents / max(total_agents, 1), 2)

        actions = cursor.execute("SELECT action FROM trace").fetchall()
        action_types = set(a["action"] for a in actions)
        action_diversity = round(min(len(action_types) / 5.0, 1.0), 2)

        errors = cursor.execute("SELECT COUNT(*) as cnt FROM trace WHERE action = 'ERROR'").fetchone()
        total_traces = cursor.execute("SELECT COUNT(*) as cnt FROM trace").fetchone()
        error_count = errors["cnt"] if errors else 0
        total_count = total_traces["cnt"] if total_traces else 1
        error_rate = round(error_count / max(total_count, 1), 4)

        conn.close()

        system_load = round(min(body.current_step / max(body.num_steps, 1), 1.0), 2)
        response_quality = round(max(1.0 - error_rate * 10, 0.0), 2)

        indicators = {
            "agent_activity": agent_activity,
            "response_quality": response_quality,
            "action_diversity": action_diversity,
            "system_load": system_load,
            "error_rate": error_rate,
        }

        weights = [0.3, 0.25, 0.2, 0.15, 0.1]
        values = [agent_activity, response_quality, action_diversity, 1.0 - system_load, 1.0 - error_rate]
        health_score = round(sum(w * v for w, v in zip(weights, values)), 2)

        return {"health_score": health_score, "indicators": indicators}
    except Exception as e:
        return {"health_score": 0.0, "indicators": {}, "error": str(e)}
```

- [ ] **Step 2: Add i18n keys**

Add `"missionControl"` section to both locale files:

zh-CN:
```json
"missionControl": {
  "title": "任务控制中心",
  "prepare": "准备",
  "launch": "发射",
  "monitor": "监控",
  "analyze": "分析",
  "healthScore": "健康评分",
  "agentActivity": "Agent 活跃度",
  "responseQuality": "响应质量",
  "actionDiversity": "行为多样性",
  "systemLoad": "系统负载",
  "errorRate": "错误率",
  "healthGood": "状态良好",
  "healthWarning": "需要关注",
  "healthCritical": "状态异常",
  "noActiveSim": "没有活跃的仿真任务",
  "activeSimCount": "活跃仿真: {count}",
  "quickNewSim": "新建仿真",
  "quickViewReport": "查看报告",
  "quickTimeMachine": "时间机器",
  "quickManageGenome": "管理基因组",
  "quickImportTemplate": "导入模板",
  "quickViewProgress": "查看进度",
  "quickPause": "暂停仿真",
  "quickAnalysis": "开始分析",
  "lifecycleStage": "当前阶段",
  "estimatedTime": "预估剩余时间",
  "configReady": "配置就绪",
  "resourceReady": "资源就绪"
}
```

en-US:
```json
"missionControl": {
  "title": "Mission Control",
  "prepare": "Prepare",
  "launch": "Launch",
  "monitor": "Monitor",
  "analyze": "Analyze",
  "healthScore": "Health Score",
  "agentActivity": "Agent Activity",
  "responseQuality": "Response Quality",
  "actionDiversity": "Action Diversity",
  "systemLoad": "System Load",
  "errorRate": "Error Rate",
  "healthGood": "All Good",
  "healthWarning": "Needs Attention",
  "healthCritical": "Critical",
  "noActiveSim": "No active simulations",
  "activeSimCount": "Active sims: {count}",
  "quickNewSim": "New Simulation",
  "quickViewReport": "View Report",
  "quickTimeMachine": "Time Machine",
  "quickManageGenome": "Manage Genomes",
  "quickImportTemplate": "Import Template",
  "quickViewProgress": "View Progress",
  "quickPause": "Pause Simulation",
  "quickAnalysis": "Start Analysis",
  "lifecycleStage": "Current Stage",
  "estimatedTime": "Estimated Time Left",
  "configReady": "Config Ready",
  "resourceReady": "Resource Ready"
}
```

- [ ] **Step 3: Commit**

```bash
git add engine/main.py web/locales/zh-CN.json web/locales/en-US.json
git commit -m "feat(mission-control): add health endpoint and i18n keys"
```

---

### Task 2: Nuxt Server — Health Proxy API Route

**Files:**
- Create: `web/server/api/simulations/[id]/health.get.ts`

- [ ] **Step 1: Create health API route**

```typescript
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, id), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  if (sim.status !== 'running') {
    return success({ health_score: 1.0, indicators: {} })
  }

  let simConfig
  try { simConfig = JSON.parse(sim.config) } catch { return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏') }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return success({ health_score: 1.0, indicators: {} })

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/simulations/health`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        db_path: dbPath,
        num_agents: sim.agentCount || 10,
        num_steps: sim.timeSteps || 5,
        current_step: Math.round((sim.progress || 0) * (sim.timeSteps || 5) / 100),
      },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '健康检查失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 2: Commit**

```bash
git add web/server/api/simulations/[id]/health.get.ts
git commit -m "feat(mission-control): add simulation health proxy API"
```

---

### Task 3: Frontend — HealthIndicator + QuickActions Components

**Files:**
- Create: `web/app/components/mission/HealthIndicator.vue`
- Create: `web/app/components/mission/QuickActions.vue`

- [ ] **Step 1: Create HealthIndicator component**

Gauge chart (ECharts) showing health_score 0-1 with color gradient (red→yellow→green). Below, show 5 indicator bars. Props: `health: { health_score: number, indicators: {...} }`. All labels use $t().

- [ ] **Step 2: Create QuickActions component**

Context-aware action grid. Props: `stage: 'prepare'|'launch'|'monitor'|'analyze'|'idle'`, `activeSim: object|null`. Shows different actions per stage. Each action is a NuxtLink card with icon + label.

- [ ] **Step 3: Commit**

```bash
git add web/app/components/mission/HealthIndicator.vue web/app/components/mission/QuickActions.vue
git commit -m "feat(mission-control): add HealthIndicator and QuickActions components"
```

---

### Task 4: Frontend — Upgrade Dashboard Page

**Files:**
- Modify: `web/app/pages/dashboard.vue`

- [ ] **Step 1: Upgrade dashboard to Mission Control**

Add lifecycle stage detection based on recent simulations:
- If any sim is 'pending' → 'prepare' stage
- If any sim is 'running' → 'monitor' stage
- If latest sim is 'completed' and no running → 'analyze' stage
- Otherwise → 'idle'

Show lifecycle stages as a horizontal stepper at the top.
Show HealthIndicator for running sims.
Replace static quick actions with QuickActions component.
Keep existing stats grid and recent list.

- [ ] **Step 2: Commit**

```bash
git add web/app/pages/dashboard.vue
git commit -m "feat(mission-control): upgrade dashboard to adaptive Mission Control"
```
