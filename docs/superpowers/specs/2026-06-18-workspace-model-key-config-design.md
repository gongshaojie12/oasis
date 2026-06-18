# 工作区级大模型 Key 配置 — 设计文档

- 日期:2026-06-18
- 状态:已批准设计,待写实现计划
- 作者:brainstorming 协作产出

## 1. 背景与问题

用户目前在界面上**没有任何地方**可以配置自己的大模型 API Key,导致所有模拟只能走 `stub`(假数据)provider,无法跑真实模型。

调查结论(代码事实):

- **后端解析链已存在但中间一级断了**:`wanxiang/api/tenancy.py:30` 的 `resolve_effective_model` 实现了"请求 model > 租户默认 `default_model_config` > stub 回落"三级策略,但新的 PG/SQLite workspace 路径里 `wanxiang/api/auth.py:88` 把 `default_model_config` 写死为 `None`,所以"工作区默认 key"这条链从未真正可用。
- **前端无 UI**:`SettingsView` 只管 name/locale;`ApiKeysView` 管的是平台自己签发的 key(调 WANXIANG API 用),**不是**用户的第三方大模型 key。
- **前端写死 stub**:`frontend/src/pages/LandingPage.tsx:172` 硬编码 `{ text, model: { provider: 'stub' } }`;`SandboxPage.tsx` 不传 model。即使后端能用真实模型,也没人能把 key 喂进去、且聊天永远走假模型。
- **无组织/总账户层**:系统最顶层就是 `workspace`,余额/充值/扣费/预算全挂在 workspace 上(`billing.py` 全是 `*_workspace`)。没有 `organization` 概念。

## 2. 目标与非目标

### 目标
- 用户能在「设置」页为当前工作区配置大模型 key,聊天/模拟自动使用该配置跑真实模型。
- 支持可扩展的 provider 列表(预设 + 自定义 OpenAI 兼容网关)。
- 打通后端 `resolve_effective_model` 的工作区默认这一级。

### 非目标(明确划界,防范围蔓延)
- 聊天时临时覆盖模型(留待未来增量)。
- 组织 / 公司总账户层(对标 OpenAI Platform 的 Organization;本次对标 ChatGPT Team,key 配在 workspace 层)。
- key 加密存储(本次明文 + 脱敏;加密作为未来独立加固任务)。
- provider 插件式注册框架(过度设计)。
- key 有效性"测试连接"按钮。

## 3. 关键决策汇总

| # | 维度 | 决定 |
|---|------|------|
| 1 | 配置粒度 | **workspace 层**(ChatGPT Team 式,不引入组织/总账户) |
| 2 | Provider 范围 | 可扩展 provider 列表 |
| 3 | 可扩展落地 | 预设表 + 自定义 OpenAI 兼容(后端一个 OpenAI 兼容 ModelCall + 静态预设表) |
| 4 | 存储方式 | 明文存储 + 读取脱敏(与现有 api key 存储一致) |
| 5 | 权限 | owner/admin 可改,member 只读脱敏(复用 `_require_admin_or_owner` / `_require_member`) |
| 6 | 入口 | 设置页新增"模型配置"卡片 |
| 7 | 聊天覆盖 | 不做临时覆盖,聊天用工作区默认;顺手修掉写死的 stub |
| 8 | 存储方案 | 方案一:新增独立 `workspace_model_config` 表 + 独立 store + 独立路由 |

## 4. 数据模型

### 4.1 新表 `workspace_model_config`(每工作区一行,主键 `workspace_id`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `workspace_id` | TEXT PK | 关联 workspace |
| `provider` | TEXT | 预设 id:`deepseek` / `openai` / `qwen` / `custom` / `stub` |
| `api_key` | TEXT | 明文存储(读取时脱敏) |
| `base_url` | TEXT nullable | OpenAI 兼容网关地址;预设可留空用默认,`custom` 时必填 |
| `model_name` | TEXT nullable | 模型名;留空用预设默认 |
| `updated_at` | TEXT | 最后修改时间(ISO) |
| `updated_by_user_id` | TEXT | 谁改的(审计) |

### 4.2 Provider 预设表(后端静态常量 `MODEL_PRESETS`,不入库)

```python
MODEL_PRESETS = [
  {"id": "deepseek", "label": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
   "default_model": "deepseek-chat", "needs_key": True, "allow_custom_base_url": False},
  {"id": "openai",   "label": "OpenAI",   "base_url": "https://api.openai.com/v1",
   "default_model": "gpt-4o-mini", "needs_key": True, "allow_custom_base_url": False},
  {"id": "qwen",     "label": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
   "default_model": "qwen-plus", "needs_key": True, "allow_custom_base_url": False},
  {"id": "custom",   "label": "自定义 (OpenAI 兼容)", "base_url": None,
   "default_model": None, "needs_key": True, "allow_custom_base_url": True},
  {"id": "stub",     "label": "测试桩 (无需 key)", "base_url": None,
   "default_model": None, "needs_key": False, "allow_custom_base_url": False},
]
```

新增主流 provider = 往 `MODEL_PRESETS` 加一行,不碰核心代码。

### 4.3 存储实现

- `wanxiang/api/model_config_store_sqlite.py` / `model_config_store_pg.py`,接口 `get(workspace_id) -> ModelConfigRecord | None` / `upsert(...)`,照搬现有 `*_store` 双实现 + 工厂模式。
- `app.py` 接线:`app.state.model_config_store = make_model_config_store(...)`。

## 5. 后端 API

### 5.1 新增路由 `wanxiang/api/routes/model_config.py`

```
GET  /v1/workspaces/{slug}/model-config     # member 可读, key 脱敏
PUT  /v1/workspaces/{slug}/model-config     # owner/admin 可写
GET  /v1/model-presets                       # 已登录即可读, 返回 MODEL_PRESETS
```

- `GET` 返回:`{provider, api_key_masked: "sk-****1234", base_url, model_name, has_key: bool, updated_at, updated_by}` —— **永不返回完整 key**。
- `PUT` 入参:`{provider, api_key?, base_url?, model_name?}`
  - 权限:`_require_admin_or_owner`(复用现有 helper,`workspaces.py:40`)。
  - 校验:`provider` 必须在预设表;预设 `needs_key=true` 且(入参无 key 且库里也无 key)→ 400;`custom` 且 `base_url` 空 → 400。
  - **key 留空 = 不改动已有 key**(前端拿不到完整 key,只能"想改才填");填了才覆盖。
  - 写入 `updated_by_user_id` + `updated_at`。

### 5.2 模型解析链接通(让配置真正生效)

1. 新增 OpenAI 兼容 ModelCall 实现 `wanxiang/models/openai_compatible.py`(用 `base_url + api_key + model_name`)。`deps.py` 的 `default_model_factory` 增加分支:provider 非 `stub` 走通用实现(deepseek 本就 OpenAI 兼容,可统一)。
2. **打通 workspace 默认级**:`resolve_effective_model`(或其调用点)改为从 `model_config_store` 按 `workspace_id` 读取配置,组装 `ModelConfig`,替代 `auth.py:88` 写死的 `None`。三级回落"请求 > 工作区默认 > stub"真正可用。
3. 解析时用 `MODEL_PRESETS` 补全 `base_url` / `default_model`(用户选预设未填 model_name 时用预设默认)。

### 5.3 安全边界

完整 key 仅出现在两处:写入存储时、解析模型实际发起 LLM 调用时。所有对外 JSON 一律脱敏。错误信息不回显完整 key。

## 6. 前端 UI

### 6.1 设置页「模型配置」卡片(`SettingsView.tsx`,排在 name/locale 卡片下)

加载:`GET /v1/model-presets` 填下拉;`GET /v1/workspaces/{slug}/model-config` 拿当前配置(脱敏)。

字段:
- **Provider 下拉**:DeepSeek / OpenAI / 通义千问 / 自定义 / 测试桩。
- **API Key**(`type=password`):已配过 → placeholder 显示脱敏值,留空表示不改动;没配过 → 空框;选 `stub` 时禁用/隐藏。
- **Base URL**:仅 provider=`custom` 时显示且必填;其它预设隐藏。
- **Model Name**:可选,placeholder 显示预设默认(如 `deepseek-chat`),留空用默认。
- **保存按钮**:调 `PUT`,成功 toast「已保存」。

### 6.2 权限适配

- member:所有输入框 `disabled`,隐藏保存按钮,提示「仅管理员可修改」。
- owner/admin:可编辑可保存。
- 角色判断:从 `GET /v1/workspaces/{slug}/members` 取当前用户 role(`SettingsView` 已有 slug)。

### 6.3 修掉写死的 stub(端到端闭环最后一环)

- `LandingPage.tsx:172`:`{ text, model: { provider: 'stub' } }` → `{ text }`(不传 model,后端回落工作区默认)。
- `SandboxPage.tsx`:确认保持不传 model。
- 闭环:设置页配 key → 聊天发消息 → 后端用工作区默认配置跑真实模型。

### 6.4 i18n

新增文案走现有 `zh.json` / `en.json`。

## 7. 错误处理

| 场景 | 行为 |
|------|------|
| member 试图 PUT | 403 `workspace.requires_admin`;前端本就隐藏保存按钮(双重保险) |
| provider 不在预设表 | 400 非法 provider |
| `needs_key=true` 但无 key(入参与库都无) | 400「该 provider 需要 API Key」 |
| `custom` 但 base_url 空 | 400「自定义网关需填写 Base URL」 |
| 前端保存失败(网络/4xx) | toast 显示后端 `detail`(沿用现有 axios 处理) |
| LLM 调用失败(key 错/网关不通/超时) | 聊天/模拟接口已有 try/except,错误作为 `kind:"error"` 消息返回(`sandboxes.py:235-252`),不崩页 |
| key 错误时安全 | 报错不回显完整 key;脱敏配置仍可 GET |

## 8. 测试(pytest,沿用 `test/wanxiang/` 风格)

- `test_model_config_store.py` — store CRUD:upsert/get、key 留空不覆盖、updated_by 记录(SQLite)。
- `test_model_config_routes.py` — GET 脱敏 + `has_key`;PUT 校验(非法 provider / 缺 key / custom 缺 base_url → 400);权限(member GET 可读、PUT 403;owner/admin 可写);key 留空不覆盖。
- `test_model_presets.py` — `GET /v1/model-presets` 结构正确。
- 扩充 `test_tenant_model_default.py` — 三级回落:请求 model > workspace 配置 > stub;验证从 store 读 workspace 默认能正确组装 `ModelConfig`。
- 前端:`SettingsView` 加轻量 vitest 渲染测试(member 只读、字段随 provider 切换显隐)。

## 9. 与 OASIS 原生模型机制的关系(设计交叉验证)

上游 OASIS(CAMEL-AI)原生**也**支持"多个模型",但目的与本设计不同,两者互补、不冲突:

- **OASIS 原生 = 自建集群做负载均衡**。面向研究者在代码里跑大规模模拟(百万 agent)。模型是"实例列表",通过 `ModelManager(models=[...], scheduling_strategy='round_robin')`(`examples/twitter_simulation_vllm.py:42`)在多个**同质**后端间轮询分摊吞吐;key 走环境变量或 `ModelFactory.create(url=...)`;`deploy.py` 起多个 vLLM server、YAML 列出所有 `host:port`、`create_model_urls`(`examples/experiment/utils.py:14`)转 URL 列表喂给 ModelManager。
- **本设计(wanxiang)= 用户在界面选 provider 填 key**。面向终端用户/团队,"多个模型"指多个**异质** provider(DeepSeek/OpenAI/通义…)供选择,key 存数据库。这是 OASIS 原生完全没有的能力(它假设你会写 Python 配模型)。

**结论**:本设计不重做 OASIS 的负载均衡(不同层次的问题)。未来若某工作区需要"配多个 key 轮询提额度",当前数据模型(每工作区一行单配置)可平滑扩展为"一行存多个 key"再喂给 `ModelManager` —— 但这是 YAGNI,本次不做,设计上无需为它买单。

## 10. 涉及文件清单

新增:
- `wanxiang/api/model_config_store_sqlite.py`
- `wanxiang/api/model_config_store_pg.py`
- `wanxiang/api/routes/model_config.py`
- `wanxiang/models/openai_compatible.py`
- 测试:`test/wanxiang/test_model_config_store.py`、`test_model_config_routes.py`、`test_model_presets.py`

修改:
- `wanxiang/api/app.py`(接线 store + 注册路由)
- `wanxiang/api/deps.py`(`default_model_factory` 增加 OpenAI 兼容分支)
- `wanxiang/api/tenancy.py` 和/或 `auth.py`(打通 workspace 默认级,替代写死的 `None`)
- `wanxiang/api/schemas.py`(`ModelConfig` 扩展 provider 取值 + `base_url`)
- `frontend/src/views/SettingsView.tsx`(模型配置卡片)
- `frontend/src/pages/LandingPage.tsx`(去掉写死 stub)
- `frontend/src/locales/zh.json` / `en.json`(文案)
