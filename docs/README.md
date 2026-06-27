# Mintlify Starter Kit

### Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mintlify) to preview the documentation changes locally. To install, use the following command

```
npm i -g mintlify
```

Run the following command at the root of your documentation (where docs.json is)

```
mintlify dev
```

**Note:** The `docs.json` file is the core configuration that defines your docs' navigation and layout, making it essential for Mintlify to properly run and preview your site.

### Publishing Changes

Our GitHub App is already installed and seamlessly propagates changes from the OASIS repo to https://docs.oasis.camel-ai.org/. Updates are automatically deployed to production whenever changes are pushed to the main branch.

### Troubleshooting

- Mintlify dev isn't running - Run `mintlify install` it'll re-install dependencies.
- Page loads as a 404 - Make sure you are running in a folder with `docs.json`

---

# 万象 WANXIANG · 场景模板与可插拔扩展

> 以下章节为基于 OASIS 改造的商业化产品「万象 WANXIANG」专属文档。
> 完整系统设计见 `docs/superpowers/specs/2026-06-13-wanxiang-design.md`；部署说明见 `docs/deployment.md`。

万象提供**三大开箱即用场景模板**，覆盖品牌方最高频的研究需求。客户不需要手写 `ScenarioConfig`，只需选模板、填空、发起模拟即可。

## 三大场景模板

### 1. `consumer_concept_test` 消费洞察 · 新品概念测试

**模板做什么**：让虚拟人群在多个新品方向（口味/包装/卖点等）中**选一个**（`CHOOSE` 决策），输出群体偏好排序与份额。

**典型客户与场景**：

| 场景 | 谁用 | 替代了什么 |
|------|------|----------|
| 快消新品口味/包装方向选型 | 元气森林/喜茶/三顿半 的品牌经理 | 几万块 + 6 周的消费者焦点小组 |
| 饮料/零食 SKU 砍掉哪个 | 大型快消 BU 总监 | 内部直觉拍板 + 上市后试错 |
| 化妆品色号/香型筛选 | 美妆品牌产品经理 | 小批量打样 + 线下试用会 |
| 快餐新菜单菜品 A/B/C | 麦当劳/瑞幸 的菜单委员会 | 单店试卖几周看 POS 数据 |
| APP 功能命名/图标选择 | 互联网产品经理 | 用户调研问卷 |
| 品牌 logo / slogan 投票 | 品牌升级项目组 | 设计公司主观推荐 |

**变量**：品牌名、品类、产品名、零售价、候选数量
**结果**：群体首选 + 每个候选的份额（例如"青提 60% / 白桃 30% / 海盐荔枝 10%"）+ 推荐结论

### 2. `marketing_ad_ab_test` 营销预测 · 广告创意 A/B

**模板做什么**：给虚拟人群看一条广告创意文案 + 投放渠道，**评 0-10 购买意愿分**（`RATE` 决策），输出群体均值、p25-p75 置信带、min/max。

**典型客户与场景**：

| 场景 | 谁用 | 替代了什么 |
|------|------|----------|
| 同产品三版广告文案选哪版上 | 品牌方 + 4A 广告公司 | 小预算试投 + 几天数据后停 |
| 种草/带货文案投前预判转化 | 小红书 MCN / 抖音直播代运营 | 凭经验拍 + 跑数据 |
| 抖音/小红书/视频号 同创意不同渠道哪个好 | 媒介投放经理 | 多渠道试投烧钱 |
| 不同卖点（功能/情感/价格）哪个最打 | 营销策划 / Brand Strategy | 焦点小组定性分析 |
| 春节/618/双 11 节点 campaign 预演 | 大促筹备组 | 历史数据外推 + 直觉 |
| 广告投放前的"红蓝军"对抗推演 | 大型品牌的 Insights 团队 | 4A 提案后内部辩论 |
| 代言人海报 A/B/C 哪个最讨喜 | 娱乐营销 / PR 团队 | 内部投票 |

**变量**：品牌、产品、品类、广告文案、定价、投放渠道
**结果**：均值评分 + 置信带（例如"群体均值 6.8，p25-p75 是 5-8"）+ 完整 Markdown 报告

### 3. `brand_sentiment_probe` 品牌舆情 · 情感探测

**模板做什么**：给虚拟人群看一段品牌相关事件描述（正面/负面/中性都可以），输出群体**情感极性 -1~+1**（`SENTIMENT` 决策）+ 分布。

**典型客户与场景**：

| 场景 | 谁用 | 替代了什么 |
|------|------|----------|
| 危机公关声明发出前预测人群反应 | 品牌 PR 总监、危机公关咨询 | 公关公司主观判断 + 发出去赌 |
| 代言人黑红事件影响估算 | 大型品牌的代言决策委员会 | 等舆情爆开看数据 |
| 新品发布会演讲稿 / 致用户信测情绪 | 创始人/CEO 团队、IR 团队 | 内部 review + 法务过稿 |
| 政策/监管动作对品牌情感影响 | 公共事务 / 政府关系部门 | 外部咨询报告 |
| 行业事件波及自家品牌的"溅射"评估 | 同行业品牌（友商应对） | 监测舆情滞后反应 |
| 新闻稿/产品文案"会不会引战"预演 | 内容审核 / Brand Safety 团队 | 内部审稿会 + 律师 |
| B2B 客户对自家服务变更的情绪预判 | SaaS / 企业服务的客户成功团队 | 客户访谈 + 调研 |
| NGO/品牌联名 / 立场表达 对核心用户冲击 | 品牌策略 + 法务 | 焦点小组 |

**变量**：品牌名、事件描述、事件时间
**结果**：群体情感均值（例如"+0.42 偏正面"或"-0.31 偏负面"）+ 分布带 + 报告

## 三大场景对比一览

| 维度 | 消费洞察（CHOOSE） | 营销预测（RATE） | 品牌舆情（SENTIMENT） |
|------|------------------|----------------|--------------------|
| **决策类型** | 多选一 | 0-10 评分 | -1~+1 情感极性 |
| **典型问题** | "选哪个？" | "买不买？" | "怎么看？" |
| **决策环节** | 新品立项前 | 投放/发布前 | 事件应对前 |
| **替代的传统方法** | 焦点小组、问卷 | 小预算试投 | 公关公司直觉 |
| **客户预算敏感度** | 中-高（产品决策权重大） | 高（投放成本动辄百万） | 高（危机一次几千万） |

## 销售切入建议

- **快消/美妆/餐饮** → 主推 ①+②（产品决策频繁、预算稳定）
- **互联网/SaaS/科技品牌** → 主推 ②+③（投放预算大、舆情敏感）
- **大型 B2C 品牌** → 三个都用（一年至少 10+ 次研究需求）
- **4A 广告公司/咨询公司** → 把它当工具集成进自己的服务，加价转售

---

## 场景可插拔：一个 YAML 文件就能加新场景

万象的场景层是**完全可插拔**的（详见 spec §3 第三层"场景插件层"）。客户来一个新需求，不用改任何代码，只需在 `wanxiang/scenarios/templates/` 新建一个 yaml 文件，立即被 API 列出可用。

### 新增场景的 3 个步骤

**步骤 1**：在 `wanxiang/scenarios/templates/` 下新建 `<your_template_id>.yaml`，格式：

```yaml
id: pricing_van_westendorp
name: 定价测试 · Van Westendorp 价格敏感度
description: 测人群对一个产品的可接受价格区间。
decision_kind: willingness_to_pay  # 对应 L1 动作 WTP
material_template: |
  {brand} 即将推出新产品「{product_name}」（{category}）。
  产品特性：{features}
question_template: |
  你愿意为这个产品支付多少钱？请给出一个具体数字（单位：元）。
variables:
  - name: brand
    label: 品牌名
    type: text
    required: true
  - name: product_name
    label: 产品名
    type: text
    required: true
  - name: category
    label: 品类
    type: text
    required: true
  - name: features
    label: 产品特性描述
    type: text
    required: true
default_options: null  # 数值类不需要 options
```

**步骤 2**：保存即生效。`GET /v1/templates` 自动列出新模板（无需重启可在开发环境立即看到；生产 Docker 部署重启容器一次）。

**步骤 3**：客户立即可用：
```bash
curl -X POST http://localhost:8000/v1/templates/pricing_van_westendorp/instantiate \
  -H "X-API-Key: <key>" -H "Content-Type: application/json" \
  -d '{"values":{"brand":"X","product_name":"Y","category":"Z","features":"..."},"options":null}'
```
返回的 `scenario` 直接喂给 `POST /v1/simulate` 或 `POST /v1/simulations/async` 即可。

### 5 个延展场景示例（按需快速实现）

| id | 决策类型 | 用途 | 目标客户 |
|----|---------|------|---------|
| `pricing_van_westendorp` | WTP | 定价敏感度测试，找最优价格区间 | 新品定价决策、SaaS 套餐定价 |
| `feature_priority_choose` | CHOOSE | APP/产品功能优先级投票 | 互联网产品经理、SaaS PM |
| `email_subject_click_test` | CLICK_PROBABILITY | 邮件/推送标题点击率预测 | EDM 团队、增长团队 |
| `policy_acceptance_probe` | SENTIMENT | 用户规则/隐私政策改动接受度 | 平台运营、合规团队 |
| `event_sponsorship_fit` | RATE | 赛事/IP/综艺 赞助匹配度评估 | 品牌赞助决策 |

### 为什么"可插拔"是商业杠杆

- **谈客户时**：可以承诺"两天内交付你定制的场景模板"——而代码改动通常 < 30 行
- **运营时**：每加一个高价值场景，整条产品线（API/UI/计费）零修改自动可用
- **扩展生态**：未来可以让第三方咨询公司贡献模板（类似 Notion 模板市场）

完整设计与未来场景路线图见 `docs/superpowers/specs/2026-06-13-wanxiang-design.md` §M3/§M4 章节。

---

## 运营成本与服务器扩容

### 测算前提

万象的服务端**只做两件事**：(1) 渲染 prompt → 发 HTTP 给 DeepSeek，(2) 收响应 → 写库。LLM 推理在 DeepSeek 远端，本地不吃 GPU。所以 LLM 是**主要变动成本**，服务器是**次要固定成本**。

实测关键数据（基于实际 228 维 persona 渲染 + scenario 注入）：

| 项目 | 值 |
|---|---|
| Persona system prompt | ~2,900 tokens（中文 228 维特质渲染） |
| Scenario user message | ~300 tokens |
| LLM 回复（JSON）| ~200 tokens |
| **单次 LLM 调用 input** | **~3,200 tokens** |
| **单次 LLM 调用 output** | **~200 tokens** |

### DeepSeek 价格（V4 系列，单位 RMB / 1M tokens）

| 模型 | 输入(缓存命中) | 输入(未命中) | 输出 |
|---|---|---|---|
| **deepseek-v4-flash** ⭐推荐 | ¥0.02 | ¥1 | ¥2 |
| deepseek-v4-pro（高保真） | ¥0.025 | ¥3 | ¥6 |

### 三档模式每 agent LLM 调用次数

| 模式 | 单 agent 调用次数 | 说明 |
|---|---:|---|
| **decision_only**（L1）| 1 次 | 看完 material 直接决策 |
| **social**（L1+L2, rounds=3）| 5 次 | 1 baseline + 3 social + 1 final（甲方案） |
| **platform**（L1+L2+L3, rounds=3）| 5 次 + dialect 增量 | 每次 input +200 tok 方言上下文 |

### Prompt Caching 的关键作用

- **同一 agent 多次调用**（social/platform 模式）：第 2-5 次的 2,900 token persona 部分**命中缓存**（¥1 → ¥0.02，省 50 倍）
- **跨 agent 不命中**：每个 agent persona 不同，无法跨 agent 缓存
- `decision_only` 单次调用 → 缓存无收益

### Token 消耗估算（每 agent）

| 模式 | 调用次数 | 输入(未命中) | 输入(命中缓存) | 输入合计 | 输出 |
|---|---:|---:|---:|---:|---:|
| `decision_only` | 1 | 3,200 | 0 | 3,200 | 200 |
| `social` (rounds=3) | 5 | 4,400 | 11,600 | 16,000 | 1,000 |
| `platform` (rounds=3) | 5 | 5,400 | 11,600 | 17,000 | 1,000 |

> social 拆分：第 1 次 3,200 全 miss；第 2-5 次每次 3,200（其中 2,900 命中 persona 缓存，300 fresh）。
> platform：每次额外 +200 tokens 方言上下文。

### Token 消耗估算（按 agent 规模 × 模式）

单位：M = million tokens，B = billion tokens

| Agent 数 | `decision_only` 输入/输出 | `social` 输入miss / 输入hit / 输出 | `platform` 输入miss / 输入hit / 输出 |
|---:|---:|---:|---:|
| 1,000 | 3.2M / 0.2M | 4.4M / 11.6M / 1.0M | 5.4M / 11.6M / 1.0M |
| 5,000 | 16M / 1M | 22M / 58M / 5M | 27M / 58M / 5M |
| 10,000 | 32M / 2M | 44M / 116M / 10M | 54M / 116M / 10M |
| **100,000** | **320M / 20M** | **440M / 1.16B / 100M** | **540M / 1.16B / 100M** |
| 200,000 | 640M / 40M | 880M / 2.32B / 200M | 1.08B / 2.32B / 200M |
| 500,000 | 1.6B / 100M | 2.2B / 5.8B / 500M | 2.7B / 5.8B / 500M |
| **1,000,000** | **3.2B / 200M** | **4.4B / 11.6B / 1B** | **5.4B / 11.6B / 1B** |

### Caching 省了多少（100K agents · social 模式）

| 维度 | 无 caching | 有 caching | 省下 |
|---|---:|---:|---:|
| 输入 token 全部走未命中价 | 1.6B × ¥1/M = **¥1,600** | 440M × ¥1/M + 1,160M × ¥0.02/M = **¥463** | **¥1,137 (−71%)** |
| 输出 token (不受 caching 影响) | 100M × ¥2/M = ¥200 | ¥200 | — |
| **总成本** | **¥1,800** | **¥663** | **¥1,137 (−63%)** |

> 这就是为什么 social/platform 模式即便每个 agent 多 5 倍调用次数，单 agent 成本只翻 2 倍——**caching 把 persona 的开销摊薄到几乎免费**。

### 成本估算（deepseek-v4-flash，含 caching 优化）

| Agent 数 | decision_only | social(3 轮) | platform(3 轮) |
|---:|---:|---:|---:|
| 1,000 | ¥3.6 | ¥6.6 | ¥7.3 |
| 5,000 | ¥18 | ¥33 | ¥36.5 |
| 10,000 | ¥36 | ¥66 | ¥73 |
| **100,000** | **¥360** | **¥660** | **¥730** |
| 200,000 | ¥720 | ¥1,320 | ¥1,460 |
| 500,000 | ¥1,800 | ¥3,300 | ¥3,650 |
| **1,000,000** | **¥3,600** | **¥6,600** | **¥7,300** |

### V4-Pro 高保真对比

| Agent 数 | pro decision_only | pro social(3 轮) | pro platform(3 轮) |
|---:|---:|---:|---:|
| 1,000 | ¥10.8 | ¥19.8 | ¥21.9 |
| 100,000 | ¥1,080 | ¥1,980 | ¥2,190 |
| 1,000,000 | ¥10,800 | ¥19,800 | ¥21,900 |

### 生产环境保守版（含重试 + 输出长尾）

实际跑模拟时**加 ×1.1 重试 + ×1.2 输出长尾系数**（≈ ×1.32 修正）：

| Agent 数 | flash 保守 social | pro 保守 social |
|---:|---:|---:|
| 1,000 | ¥9 | ¥27 |
| 10,000 | ¥90 | ¥270 |
| 100,000 | ¥900 | ¥2,700 |
| 1,000,000 | ¥9,000 | ¥27,000 |

> 额外项：`Sweep` 模式 ×N (变量组合数)；`Causal/Counterfactual` 各 ×3-5；`LLM 报告解读` +1 次调用/sim（可忽略）。

### 商业定价反推（spec D9 三价位档）

| 档位 | 100K agent 成本 (flash) | 建议定价 | 倍数 | 毛利率 |
|---|---:|---:|---:|---:|
| decision_only（基础）| ¥360 | ¥2,000-5,000 | 5-15× | ≥80% |
| social（专业）| ¥660 | ¥8,000-15,000 | 12-25× | ≥90% |
| platform（企业）| ¥730 | ¥20,000-50,000 | 30-70× | ≥95% |

---

## 服务器配置 — 不一定要随 agent 数升

### 资源消耗模型

| 维度 | 单 agent | 100 万 agent |
|---|---|---|
| 内存（in-flight）| ~17 KB | **不是 17 GB** — `asyncio.Semaphore` 并发上限把任意时刻在飞数控在 ~100 → **稳定 < 100 MB** |
| CPU | 几 µs prompt 渲染 + JSON 解析 | 1 核撑几千 RPS（IO-bound, 瓶颈在 DeepSeek 不在你） |
| 出网带宽 | ~6 KB 往返 | 100 万 × 6 KB ≈ 6 GB / sim 总流量 |
| SQLite 写入 | ~1 KB trace | 1 GB / sim — SQLite ~1K/s 紧；PG ~10K/s 轻松 |

**核心观察**：内存因 asyncio 并发上限而**与 N 解耦**；CPU 因任务 IO-bound 而**几乎不长**。

### 真正的瓶颈不在服务器，在 DeepSeek RPM

| Agent 数 | flash (2500 RPM) 最短墙钟 | 服务器是否需要升级 |
|---:|---:|---|
| 1,000 | ~25 秒 | ❌ 不需要 |
| 5,000 | ~2 分钟 | ❌ |
| 10,000 | ~4 分钟 | ❌ |
| 100,000 | ~40 分钟 | ❌ |
| 200,000 | ~80 分钟 | 🟡 SQLite 写吞吐开始紧 |
| 500,000 | ~3.3 小时 | 🟡 建议切 PG |
| 1,000,000 | ~6.7 小时 | 🟡 切 PG + 分 batch |

> 你买更大服务器**不能让单次 100 万 agent 模拟跑得更快** — DeepSeek API 才是天花板。要快只能去申请企业版提升 RPM。

### 推荐配置阶梯

| 阶段 | 触发条件 | 服务器 | 数据库 | 队列 | 月成本 |
|---|---|---|---|---|---:|
| **Stage 0 MVP** | ≤ 100K agent/sim，≤ 5 并发 sim | 2C4G（云轻量）| SQLite 单文件 | 进程内 asyncio | **~¥100** |
| **Stage 1 付费期** | ≤ 500K agent/sim，10-30 并发 sim | 4C8G | SQLite 或托管 PG | uvicorn workers=2 | ~¥300-500 |
| **Stage 2 规模化** | ≥ 500K agent/sim 或 50+ 并发 sim | 8C16G | **PostgreSQL** RDS | **Redis + Celery** | ~¥1,500-3,000 |
| **Stage 3 平台化** | > 100 万 agent/sim 常态化 | 多机 + 负载均衡 | PG 主从 | Redis Cluster + Celery 多 worker | ~¥5,000+ |

### 真正"必须升配"的 3 个监控信号

不是看 agent 数，看这 3 个指标：

1. **uvicorn worker CPU 持续 > 70%** → 加 workers 或升核数
2. **SQLite WAL 文件 > 200 MB / 写 latency > 100 ms** → 切 PG
3. **asyncio.Semaphore wait time > LLM call time** → 升并发 cap + 升带宽 / OS fd limit

### 不需要升配的常见误区

- 单次 1 万 agent：默认 2C4G + DeepSeek 完全够，4 分钟出结果
- 100 万 agent 但**一周跑一次**：MVP 配置 + 凌晨长跑即可
- 5 万 agent × 30 并发租户：4C8G + PG 够，但要在 `wanxiang/api/tenancy.py` 加**租户级 RPM 配额**避免相互饿死

### 扩容前优先做的 6 件事

按 ROI 从高到低：

1. **批分片**：单 sim 100 万 → 拆 100 个 batch × 10K，串行 / 小并发跑，平滑 RPM 占用 + 内存可控
2. **租户级 DeepSeek RPM 配额**：避免单租户大 sim 把全平台 RPM 用完
3. **DeepSeek 企业账户**：升 RPM 限额（2500 → 自定义）比升服务器有效
4. **Prompt 前缀优化**：把 scenario 放到 system prefix 前面，跨 agent 共享前缀缓存（输入价省 50×）
5. **Redis + Celery**（spec §7.2 阶段 1）：进程队列搬到 Redis，多 worker 并行
6. 最后才是**升服务器规格**

### 一句话总结

> 对万象这套架构，**服务器扩容的重要性远低于 DeepSeek API 配额 + 任务调度软件层优化**。Stage 0 MVP（2C4G + SQLite + ¥100/月）就能撑到 10 万 agent/sim 级别；超过 50 万再切 4-8C/16GB + PG + Celery。"规模化"主要是**把任务调度做扎实**（分片、配额、重试、监控），而不是堆机器。



---

## 人群画像数据源（M1 数据接入）

人群画像（distribution）分三块：**demographic**（人口属性）/ **personality**（消费心理）/ **media**（媒介习惯）。
目前内置画像 `cn_census_2020`（第七次全国人口普查）仅覆盖 demographic；personality / media 需从下列来源补充。
**所有维度建议标注来源与年份**（不同来源口径/年份/样本范围不完全可比，多源拼接需注明，参考 Aaru 做法）。

上传方式：管理后台 `/admin/distributions` → 上传画像（JSON/YAML），或放入 `wanxiang/datasources/distributions/*.json` 随启动 seed。

### 数据合规说明（商用风险）

> ⚠️ 以下为基于公开规定的整理，**非法律意见**；正式商用 / 融资前请由专业律师做一次数据合规审查。

万象是商业产品，数据来源合规分级：

| 数据源 | 可商用 | 说明 |
|--------|:------:|------|
| **国家统计局**（七普 / 年鉴 / 公报） | ✅ 低风险 | 政府公开信息，未禁止商用；统计**数字是客观事实**，不受著作权保护，可提取再加工 |
| CNNIC 报告 | ✅ 基本可引用 | 标来源即可；勿整本转售 |
| 巨量算数 / 艾瑞 免费报告 | 🟡 看条款 | 引用数字一般可以；整篇转载需看各自授权 |
| **CFPS / CGSS** 学术微观数据 | ❌ 禁止商用 | 协议明确仅限学术/政策研究，**已决定不用** |
| 自有问卷 / CRM / 业务数据 | ✅ 完全自有 | 最干净，推荐作为未来种子 |

**用国家统计局数据要守的红线**（守住即接近零风险）：

1. ✅ **标注来源**：每个维度注明「数据来源：第七次全国人口普查」等（画像 description 已标）。
2. ✅ **只用数字、不转售整库**：提取统计值重新计算成分布 ✅；把整本年鉴/数据库原样转售或做成数据产品出售 ❌（可能侵犯汇编/数据库权）。
3. ✅ **优先从官网下载**（stats.gov.cn），避免第三方下载站（如 zgtjnj.org）的二次使用条款风险。
4. ✅ **不声称官方背书**：表述为「使用了公开统计数据」，而非「国家统计局授权/认证/合作」。
5. ✅ **加免责声明**：「结果为基于公开数据的概率预测，仅供参考，建议结合业务判断」（对应 spec §M5 诚实标注）。

**安全区 vs 红线**：拿公开数字喂进模拟引擎、卖「人群模拟预测」服务 = ✅ 安全（卖的是分析能力，非数据本身）；把统计数据原样打包成数据库出售 = ❌ 高风险。万象属于前者。

### demographic（人口属性）— 官方、免费

| 来源 | 补充维度 | 下载地址 |
|------|---------|---------|
| 第七次全国人口普查主要数据 | 性别/年龄/城乡/学历/民族/省份（已入库 `cn_census_2020`） | https://www.stats.gov.cn/sj/pcsj/rkpc/d7c/ |
| 《中国人口普查年鉴-2020》**中册** | 就业 / 行业 / 职业（长表 10% 抽样；第四卷 4-1~4-6 表） | 官方 https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/indexch.htm （点 HTML→中册）／ 第三方逐表 https://www.zgtjnj.org/naviBooklist-n3022062702-1.html |
| 《中国人口普查年鉴-2020》**下册** | 婚姻状况（第五卷婚姻生育；8-3 老年人口婚姻状况等） | 官方同上（点 HTML→下册）／ 第三方逐表 https://www.zgtjnj.org/navibooklist-n3022062703-1.html |
| 中国统计年鉴（**注意：`ndsj` 综合年鉴，非普查年鉴**） | 收入分组、城乡收入、消费支出结构 | https://www.stats.gov.cn/sj/ndsj/ （选最新年份 indexch.htm） |
| 国民经济和社会发展统计公报（每年 2 月） | 人均可支配收入、五等分收入分组 | https://www.stats.gov.cn 首页「统计公报」 |

> ⚠️ 人口普查年鉴是**在线 HTML 光盘版，无整本下载按钮**，只能逐表浏览/复制：进官方页点绿色「HTML」→选 上/中/下册 →翻到对应表 →把网页表格复制进 Excel；或用上方第三方站逐表查看。只需取你要的 2-3 张表（如职业大类、婚姻状况），不必下整本。
> 区分两本：`pcsj/rkpc/7rp` = **人口普查年鉴**（婚姻/职业在此）；`ndsj` = **综合统计年鉴**（收入/GDP 在此），勿混。

### media（媒介 / 平台习惯）— 官方、免费

| 来源 | 补充维度 | 下载地址 |
|------|---------|---------|
| CNNIC《中国互联网络发展状况统计报告》（第55次，2025-01） | 网民规模、各应用渗透率（短视频/社交/电商/支付）、上网时长、城乡/年龄网民结构 | 中文 https://www.cnnic.net.cn/NMediaFile/2025/0220/MAIN1740036167004CKE0DITFO1.pdf ／ 英文 https://www.cnnic.com.cn/IDR/ReportDownloads/202505/P020250514564119130448.pdf ／ 全文页 https://www.100ec.cn/detail--6646318.html |
| CNNIC 历次报告列表 | 同上（按需取年份） | https://www.cnnic.net.cn → 统计报告 |

> 注：CNNIC 给的是**整体应用渗透率**，不是「抖音 vs 小红书 vs 微信」细分对比；细分平台画像见下方第三方报告。

### personality（消费心理）+ 平台细分 — 学术免费 / 第三方

公开官方统计基本没有「价格敏感度 / 尝鲜意愿」这类心理维度，真实来源：

| 来源 | 补充维度 | 获取 | 是否免费 |
|------|---------|------|---------|
| CGSS 中国综合社会调查（人大） | 价值观、消费态度、社会心理 | http://cgss.ruc.edu.cn | ⚠️ 免费但**禁止商用**（仅学术/政策） |
| CFPS 中国家庭追踪调查（北大） | 收入、消费、健康、态度 | https://www.isss.pku.edu.cn/cfps/ | ⚠️ 免费但**禁止商用**（协议第5条；商业产品勿用） |
| 巨量算数（抖音官方） | 平台用户画像、行业趋势 | https://trendinsight.oceanengine.com | ✅ 免费报告 |
| QuestMobile | 各 App 用户画像、渗透率 | https://www.questmobile.com.cn | 部分免费摘要 |
| 艾瑞咨询 | 品类消费、用户行为 | https://report.iresearch.cn | 部分免费 |
| 尼尔森 / 凯度（Nielsen / Kantar） | 消费者类型、价格敏感型占比 | 官网报告 / 采购 | 摘要免费，完整付费 |

### 处理流程

1. 下载报告（PDF/Excel）。图表型 PDF 可拆成图片，由模型读图提取数字（参见 `cn_census_2020` 的提取方式）。
2. 整理成画像 JSON（紧凑写法 `{"维度":{"取值":占比}}` 或双语 Plan-B 格式）。
3. 经 `/admin/distributions` 上传，或放入种子目录。
4. 每个维度在 description 注明来源 + 年份。


---

## 联合分布 / 合成人口路线（画像真实度升级）

当前画像是**各维度独立抽样（边际分布）**：性别、省份、职业各按全国比例独立抽，整体比例对，但组合可能不真实（如「西藏+金融+海归」）。要让虚拟人的**组合也符合现实**（省份↔职业↔婚姻等），需升级到**联合分布 / 合成人口**。

### 决策（已定）

- **算法：纯七普 IPF（迭代比例拟合）**，将来用**自有问卷**当种子升级为「IPF + 种子」。
- **不用 CFPS/CGSS 等学术微观数据**：虽含真实个体（理想种子），但**协议禁止商用**，万象是商业产品，违约有法律/声誉/尽调风险，且与「数据可信合规」卖点冲突。技术上虽难被发现，但不值得赌。
- **全维度联合真数据公开渠道拿不到**：七普只发布到两两/三三交叉表，微观个体记录涉隐私不公开。行业（含 Aaru）通用做法即「交叉表 + IPF 推断联合」，本质是高级合成，非真数据。

### 算法选型（无种子样本时）

| 算法 | 是否需种子 | 适用 |
|------|-----------|------|
| **IPF** | 否 | ✅ 当前最优，只靠交叉表即可 |
| IPU / 分层 IPF | 否 | 想加「家庭」层时升级 |
| 最大熵 | 否 | 与 IPF 同档，可选 |
| 贝叶斯网络 | 否（可只用交叉表） | 可解释，稍复杂 |
| 组合优化（模拟退火） | **是** | 有种子后才用 |
| 深度生成（CTGAN/VAE/扩散） | **是（大量微观）** | 黑箱、人口模拟不推荐 |

> 结论：**算法不是瓶颈，数据是**。无种子时 IPF/最大熵/IPU 即天花板（信息论上变不出约束里没有的相关性）。有了自有问卷种子后，真实度才能再上台阶。

### 要让 IPF 更接近真实，还需补的数据（均可商用）

| 数据 | 给 IPF 增加的约束 | 出处 | 状态 |
|------|------------------|------|------|
| 七普长表 就业/婚姻交叉表 | 省份×性别×{年龄/学历/职业/行业/婚姻} | 已下载 `docs/persons/jiuye` + `hunyin`（54 个 .xls，a/b/c=总表/城市/镇/乡村） | ✅ 已有 |
| **收入**（七普不普查收入，**关键缺口**） | 城乡/分省/分行业收入档；省份×职业×收入近似 | 《中国统计年鉴》https://www.stats.gov.cn/sj/ndsj/ ；各省统计年鉴 | ⬜ 待补 |
| 居民消费支出结构 | 八大类消费按城乡/收入档 | 中国统计年鉴 居民生活章 | ⬜ 待补 |
| 七普年鉴 上册 家庭/住房卷 | 家庭规模↔子女↔婚姻、住房 | 人口普查年鉴2020 上册 | ⬜ 可选 |

### 实施计划（明天起）

1. **第一步（小成本，~¥20）**：用现有 jiuye+hunyin 跑一版 IPF，生成合成人口样本，用真值表验证质量 → 看效果再决定是否接引擎。
2. **第二步（~¥150）**：效果满意后改造 `PersonaBuilder`（当前 `wanxiang/personas/builder.py` 是逐维度独立 `rng.choices`）支持联合分布抽样 + 画像格式 + 上传校验 + 前端 + 验证。
3. **将来**：自己做问卷调研（几百份即可，问卷星等）→ 自有、可商用、可公开来源的真实种子 → IPF 重加权升级。

> 现状：内置画像仅 `cn_census_2020`（七普 7 个真实 demographic 维度，边际分布）；personality/media 为合成占位；职业/婚姻维度尚未补入。
