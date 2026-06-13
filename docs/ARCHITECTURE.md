# OASIS 架构文档

> OASIS (Open Agent Social Interaction Simulations) 是一个基于 LLM Agent 的大规模社交媒体模拟器，
> 最高支持百万级 Agent，模拟 Twitter / Reddit 上的用户行为，用于研究信息传播、群体极化、从众行为等社会现象。
>
> 整体采用 **PettingZoo 风格的 Env 接口 + 生产者-消费者异步消息架构**。

---

## 1. 分层总览

```mermaid
flowchart TB
    subgraph User["用户代码 / Examples 层"]
        EX["quick_start.py · reddit_simulation · twitter_simulation · group_chat ...<br/>核心调用: oasis.make() → env.reset() → env.step(actions) → env.close()"]
    end

    subgraph Env["Environment 层 (oasis/environment)"]
        OE["OasisEnv (env.py)<br/>• reset(): 启动 platform.running() 协程, 注册所有 agent<br/>• step(actions): 更新推荐表 → 并发执行动作 → 推进时钟<br/>• close(): 发送 EXIT, 落库收尾<br/>• llm_semaphore: 限制 LLM 并发 (默认128)"]
        ACT["动作封装 (env_action.py)<br/>ManualAction(预定义) / LLMAction(LLM决策)"]
    end

    subgraph Agent["Social Agent 层 (oasis/social_agent)"]
        SA["SocialAgent / SocialAction / SocialEnvironment / AgentGraph"]
    end

    subgraph Platform["Social Platform 层 (oasis/social_platform)"]
        PF["Platform / RecSys / Database / PlatformUtils"]
    end

    CH(["Channel (异步消息队列)<br/>生产者-消费者解耦"])

    User --> Env
    Env --> Agent
    Env --> Platform
    Agent <--> CH
    Platform <--> CH
```

---

## 2. 核心运行时架构（双协程 + Channel 解耦）

这是整个系统**最关键的设计**：Agent 与 Platform 通过 `Channel` 异步消息队列完全解耦，
Platform 作为一个独立的后台协程消费消息，串行处理数据库写入，避免 SQLite 并发冲突。

```mermaid
flowchart TB
    STEP["env.step(actions) — N 个 Agent 并发 (asyncio.gather)"]

    subgraph AgentBox["SocialAgent (agent.py) — 继承 camel.ChatAgent"]
        A1["perform_action_by_llm() → LLM 推理 → tool_calls"]
        A2["perform_action_by_data() → 直接执行指定动作"]
        A3["perform_interview() → 访谈问答"]
    end

    subgraph ActionBox["SocialAction (agent_action.py)"]
        AC["29 个 async 动作 → FunctionTool<br/>create_post / like_post / follow / ...<br/>perform_action(msg, type):<br/>① write_to_receive_queue<br/>② read_from_send_queue (轮询)"]
    end

    subgraph ChannelBox["Channel (channel.py)"]
        RQ["receive_queue (asyncio.Queue)<br/>Agent → Platform 请求"]
        SD["send_dict (AsyncSafeDict)<br/>Platform → Agent 响应"]
    end

    subgraph PlatformBox["Platform.running() — 独立后台协程 (消费者循环)"]
        PL["while True:<br/>receive_from() → getattr(self, action.value) → 执行 → send_to()<br/><br/>帖子: create_post/repost/quote_post<br/>互动: like/dislike/unlike (post & comment)<br/>关系: follow/unfollow/mute/unmute<br/>内容: create_comment/search/trend/refresh<br/>治理: report_post · 群聊: create/join/leave/send/listen<br/>电商: purchase_product · 访谈: interview<br/>update_rec_table(): 刷新推荐系统 (每 step 开头)"]
    end

    subgraph Support["数据与算法支撑"]
        PU["PlatformUtils<br/>_execute_db_command<br/>_record_trace<br/>_add_comments_to_posts<br/>_get_post_type<br/>_check_self_rating"]
        RS["RecSys (recsys.py)<br/>random / reddit(hot_score)<br/>twitter(TF-IDF·MiniLM)<br/>twhin-bert(嵌入+时间衰减)"]
        DB[("SQLite Database<br/>16 张表")]
    end

    STEP --> A1 & A2 & A3
    A1 & A2 & A3 --> AC
    AC -->|"(msg_id, agent_id, message, action)"| RQ
    RQ --> PL
    PL -->|"(msg_id, agent_id, result)"| SD
    SD -.轮询读取.-> AC
    PL --> PU
    PL --> RS
    PU --> DB
    RS --> DB
```

---

## 3. 一次 `env.step()` 的完整数据流（时序图）

```mermaid
sequenceDiagram
    participant U as 用户
    participant E as OasisEnv
    participant Ag as SocialAgent
    participant C as Channel
    participant P as Platform
    participant D as DB / RecSys

    U->>E: step(actions)
    E->>P: update_rec_table()
    P->>D: 计算推荐矩阵 → 写 rec 表

    Note over E,Ag: 对每个 agent 并发 (asyncio.gather)
    E->>Ag: LLMAction (信号量限流)
    Ag->>P: ① to_text_prompt() → refresh
    P->>D: 查 rec / post 表
    D-->>Ag: 返回环境观测
    Ag->>Ag: ② LLM 决策 → tool_calls
    Ag->>C: ③ 执行动作 → receive_queue
    C->>P: 消费消息 getattr 执行
    P->>D: 写业务表 + trace 表
    P-->>C: send_dict 返回 result
    C-->>Ag: read_from_send_queue
    Ag-->>E: 返回 response
    E->>E: time_step += 1 (Twitter)
    E-->>U: 完成
```

---

## 4. 支撑组件

```mermaid
flowchart LR
    subgraph G["AgentGraph (agent_graph.py) — 社交关系图"]
        G1["双后端: igraph(内存,默认) / Neo4jHandler(图数据库)"]
        G2["add/remove edge(follow), get_agent(s), visualize()"]
        G3["agent_mappings: {agent_id → SocialAgent}"]
    end

    subgraph SE["SocialEnvironment (agent_environment.py)"]
        SE1["to_text_prompt(): posts + followers + follows + groups → LLM 提示"]
    end

    subgraph UI["UserInfo (config/user.py) — 用户画像 → System Prompt"]
        UI1["to_twitter_system_message / to_reddit_system_message"]
        UI2["to_custom_system_message: 自定义模板"]
    end

    subgraph CL["Clock (clock/clock.py) — 沙盒时钟"]
        CL1["Reddit: 真实时间放大 k 倍 / Twitter: 离散 time_step"]
    end

    subgraph GEN["Agents Generator (agents_generator.py) — Agent 工厂"]
        GEN1["generate_reddit_agent_graph(JSON) / generate_twitter_agent_graph(CSV)"]
        GEN2["generate_agents_100w: 百万级(用 list 替代图换性能)"]
        GEN3["generate_custom_agents: reset 时批量注册"]
    end

    EXT["外部依赖: CAMEL-AI (ChatAgent/ModelFactory) · LLM (OpenAI/Qwen/vLLM)"]
```

---

## 5. 数据库实体关系 (ER)

```mermaid
erDiagram
    user ||--o{ post : 发布
    user ||--o{ comment : 评论
    user ||--o{ follow : 关注关系
    user ||--o{ mute : 屏蔽
    user ||--o{ trace : 行为日志
    user ||--o{ rec : 推荐表
    post ||--o{ comment : 拥有
    post ||--o{ like : 被点赞
    post ||--o{ dislike : 被踩
    post ||--o{ report : 被举报
    post ||--o{ post : 转发引用
    comment ||--o{ comment_like : 被点赞
    comment ||--o{ comment_dislike : 被踩
    chat_group ||--o{ group_member : 成员
    chat_group ||--o{ group_message : 消息
    product ||--o{ trace : 购买记录

    user {
        int user_id PK
        int agent_id
        text user_name
        text name
        text bio
        datetime created_at
        int num_followings
        int num_followers
    }
    post {
        int post_id PK
        int user_id FK
        int original_post_id FK
        text content
        text quote_content
        datetime created_at
        int num_likes
        int num_dislikes
        int num_shares
        int num_reports
    }
    trace {
        int user_id FK
        datetime created_at
        text action
        text info
    }
    rec {
        int user_id FK
        int post_id FK
    }
```

> 共 16 张表：`user`, `post`, `comment`, `follow`, `mute`, `like`, `dislike`,
> `comment_like`, `comment_dislike`, `report`, `trace`(行为日志), `rec`(推荐表),
> `product`, `chat_group`, `group_member`, `group_message`。

---

## 6. 关键设计要点

| 设计 | 说明 |
|------|------|
| **生产者-消费者解耦** | Agent 与 Platform 不直接调用，全部经 `Channel` 异步队列；Platform 是单后台协程串行处理 DB 写入，避免 SQLite 并发冲突 |
| **PettingZoo 风格 API** | `make/reset/step/close`，动作以 `dict[Agent → Action]` 传入，对齐多智能体强化学习生态 |
| **两类动作** | `ManualAction`（脚本预设，含 INTERVIEW）/ `LLMAction`（LLM 自主决策，走信号量限流） |
| **动作即工具** | 29 个动作通过 CAMEL `FunctionTool` 暴露给 LLM，`available_actions` 控制每个 Agent 的动作空间 |
| **可插拔推荐系统** | 4 种算法对应 `RecsysType`：random / reddit(热度) / twitter(TF-IDF·MiniLM) / twhin-bert(嵌入)，每步 `step` 前刷新 `rec` 表 |
| **trace 表** | 记录所有 Agent 行为，是事后分析（信息传播、群体极化等）的核心数据 |
| **双图后端** | igraph(内存) 适合常规规模；Neo4j 适合大规模；百万级则退化为 list 以换取性能 |
| **双平台时间模型** | Reddit 用真实时间放大，Twitter 用离散 time_step |

---

## 7. 模块文件索引

| 模块 | 文件 | 职责 |
|------|------|------|
| 入口 | `oasis/__init__.py` | 导出公共 API |
| 环境 | `oasis/environment/env.py` | `OasisEnv` 主循环 (reset/step/close) |
| 环境 | `oasis/environment/env_action.py` | `ManualAction` / `LLMAction` |
| 环境 | `oasis/environment/make.py` | `make()` 工厂 |
| Agent | `oasis/social_agent/agent.py` | `SocialAgent` (继承 ChatAgent) |
| Agent | `oasis/social_agent/agent_action.py` | `SocialAction` (29 个动作工具) |
| Agent | `oasis/social_agent/agent_environment.py` | `SocialEnvironment` (环境观测→提示) |
| Agent | `oasis/social_agent/agent_graph.py` | `AgentGraph` / `Neo4jHandler` |
| Agent | `oasis/social_agent/agents_generator.py` | Agent 工厂函数 |
| 平台 | `oasis/social_platform/platform.py` | `Platform` 业务逻辑 (1642 行) |
| 平台 | `oasis/social_platform/channel.py` | `Channel` 异步消息队列 |
| 平台 | `oasis/social_platform/recsys.py` | 4 种推荐算法 |
| 平台 | `oasis/social_platform/database.py` | SQLite 建库/读写 |
| 平台 | `oasis/social_platform/platform_utils.py` | DB 工具 / trace 记录 |
| 平台 | `oasis/social_platform/typing.py` | `ActionType` / `RecsysType` / `DefaultPlatformType` |
| 平台 | `oasis/social_platform/config/user.py` | `UserInfo` 画像→system prompt |
| 时钟 | `oasis/clock/clock.py` | 沙盒时钟 |
</content>
