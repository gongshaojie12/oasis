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

