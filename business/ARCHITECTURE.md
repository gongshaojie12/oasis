# OASIS 项目系统架构与代码流程说明

## 1. 项目概述

OASIS（Open Agent Social Interaction Simulations）是一个可扩展的开源社交媒体模拟器，由 CAMEL-AI.org 开发。它利用大语言模型（LLM）驱动的智能体来模拟社交平台（如 Twitter 和 Reddit）上最多一百万用户的行为。该项目旨在研究信息传播、群体极化、羊群效应等复杂社会现象。

**技术栈**：Python 3.10+、asyncio 异步框架、SQLite 数据库、CAMEL-AI 框架、Sentence Transformers / TwHIN-BERT 推荐模型、igraph / Neo4j 图引擎。

---

## 2. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        OasisEnv (环境层)                         │
│   oasis/environment/env.py                                      │
│   - reset() / step() / close()                                  │
│   - 协调 Agent、Platform、推荐系统的交互                          │
├───────────────┬─────────────────────────┬───────────────────────┤
│  AgentGraph   │     Channel (通信层)     │    Platform (平台层)   │
│  (社交图谱)    │  oasis/social_platform/ │  oasis/social_platform│
│  agent_graph  │  channel.py             │  /platform.py         │
│               │  异步消息队列            │  平台业务逻辑 + DB     │
├───────────────┴─────────────────────────┴───────────────────────┤
│                     SocialAgent (智能体层)                        │
│   oasis/social_agent/agent.py                                    │
│   - 继承 CAMEL ChatAgent                                         │
│   - LLM 驱动决策 / 手动预定义行为 / 人机交互                       │
├─────────────────────────────────────────────────────────────────┤
│                    底层支撑模块                                    │
│   Database (SQLite)  │  RecSys (推荐系统)  │  Clock (沙盒时钟)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详解

### 3.1 环境层 (Environment)

| 文件 | 说明 |
|------|------|
| `oasis/environment/env.py` | 核心环境类 `OasisEnv`，统一编排仿真流程 |
| `oasis/environment/env_action.py` | 定义 `ManualAction`（手动预定义动作）和 `LLMAction`（LLM 自主动作）|
| `oasis/environment/make.py` | 工厂函数 `make()`，快速创建 `OasisEnv` 实例 |

**`OasisEnv` 核心方法**：

- **`__init__(agent_graph, platform, database_path, semaphore)`**：初始化环境，创建平台实例和通信 Channel，通过 `semaphore` 控制 LLM 并发数（默认 128）。
- **`reset()`**：启动平台的异步事件循环（`platform.running()`），并将所有智能体注册（Sign Up）到平台。
- **`step(actions)`**：一个仿真步骤的核心。先更新推荐表（`update_rec_table`），然后并发执行所有智能体的动作（`asyncio.gather`）。
- **`close()`**：发送 `EXIT` 信号停止平台，关闭仿真。

### 3.2 智能体层 (Social Agent)

| 文件 | 说明 |
|------|------|
| `oasis/social_agent/agent.py` | `SocialAgent` 类，继承 CAMEL 的 `ChatAgent` |
| `oasis/social_agent/agent_action.py` | `SocialAction` 类，封装 28 种社交操作 |
| `oasis/social_agent/agent_environment.py` | `SocialEnvironment` 类，为 Agent 构建环境感知文本 |
| `oasis/social_agent/agent_graph.py` | `AgentGraph` 类，管理社交关系图（支持 igraph/Neo4j） |
| `oasis/social_agent/agents_generator.py` | 智能体批量生成工具函数 |

**`SocialAgent` 关键设计**：

- **继承 ChatAgent**：复用 CAMEL 框架的对话能力和记忆管理。
- **三种行为模式**：
  - `perform_action_by_llm()`：LLM 观察环境后自主选择 Tool Call 执行动作。
  - `perform_action_by_data(func_name, *args)`：按预定义数据执行指定动作。
  - `perform_action_by_hci()`：人机交互模式，用户手动选择动作。
- **环境感知**：通过 `SocialEnvironment.to_text_prompt()` 获取当前推荐帖子、关注者数量、群聊消息等信息，转换为自然语言 Prompt 提供给 LLM。
- **Tool Calling**：每种社交操作（如 `create_post`、`like_post`、`follow`）都被包装为 `FunctionTool`，LLM 通过 OpenAI 兼容的 Function Calling 机制选择并执行。

**`AgentGraph` 社交图谱**：

- 支持两种后端：`igraph`（本地高性能图库）和 `Neo4j`（分布式图数据库）。
- 管理 Agent 节点和 Follow 关系边。
- 提供图可视化功能。

### 3.3 平台层 (Social Platform)

| 文件 | 说明 |
|------|------|
| `oasis/social_platform/platform.py` | `Platform` 类，社交平台核心逻辑（~1600行）|
| `oasis/social_platform/channel.py` | `Channel` 类，Agent 与 Platform 间的异步消息通道 |
| `oasis/social_platform/database.py` | SQLite 数据库创建与查询工具 |
| `oasis/social_platform/recsys.py` | 推荐系统实现（4种算法）|
| `oasis/social_platform/typing.py` | 枚举类型定义（`ActionType`, `RecsysType`, `DefaultPlatformType`）|
| `oasis/social_platform/config/` | 配置类（`UserInfo`, `Neo4jConfig`）|

**`Platform` 核心机制**：

- **异步事件循环 (`running()`)**：平台以一个持续运行的异步任务存在，不断从 `Channel` 读取消息，根据 `ActionType` 分发到对应的处理函数。
- **数据库模型**：使用 SQLite 存储 16 张表（user、post、follow、mute、like、dislike、report、trace、rec、comment、comment_like、comment_dislike、product、group、group_member、group_message）。
- **trace 表**：记录所有智能体的操作日志，用于后续分析。

**`Channel` 通信机制**：

```
Agent ──write_to_receive_queue──> [receive_queue] ──> Platform (处理请求)
Agent <──read_from_send_queue──── [send_dict]     <── Platform (返回结果)
```

- 使用 `asyncio.Queue` 作为接收队列。
- 使用异步安全字典 `AsyncSafeDict` 作为发送缓冲。
- 每个请求分配唯一 `UUID`，实现请求-响应匹配。

### 3.4 推荐系统 (RecSys)

系统内置 4 种推荐算法：

| 算法类型 | 枚举值 | 说明 |
|---------|--------|------|
| 随机推荐 | `random` | 随机抽取帖子推荐给用户 |
| Reddit 热度排序 | `reddit` | 基于 Reddit 的 Hot Score 算法（likes - dislikes + 时间衰减）|
| TwHIN-BERT 个性化 | `twhin-bert` | 使用 Twitter 的 TwHIN-BERT 模型计算用户画像与帖子的语义相似度 |
| 基于历史行为 | `twitter` | 使用 SentenceTransformer 结合用户 like/dislike 历史的协同过滤 |

推荐流程：每个 `step()` 开始时调用 `update_rec_table()`，更新每个用户的推荐帖子列表（存储在 `rec` 表中）。Agent 执行 `refresh` 操作时，从 `rec` 表中取出推荐帖子 + 关注用户的帖子。

### 3.5 时钟系统 (Clock)

`oasis/clock/clock.py` 中的 `Clock` 类：

- 维护沙盒内的虚拟时间，支持时间加速（默认 60 倍）。
- `time_step` 记录当前仿真步数，每次 `step()` 后递增。

### 3.6 动作类型 (ActionType)

系统定义了 **30 种**动作类型：

| 类别 | 动作 |
|------|------|
| 帖子操作 | `create_post`, `repost`, `quote_post`, `report_post` |
| 帖子互动 | `like_post`, `unlike_post`, `dislike_post`, `undo_dislike_post` |
| 评论操作 | `create_comment`, `like_comment`, `unlike_comment`, `dislike_comment`, `undo_dislike_comment` |
| 用户关系 | `follow`, `unfollow`, `mute`, `unmute` |
| 信息获取 | `refresh`, `search_posts`, `search_user`, `trend` |
| 群聊功能 | `create_group`, `join_group`, `leave_group`, `send_to_group`, `listen_from_group` |
| 其他 | `sign_up`, `do_nothing`, `purchase_product`, `interview`, `exit`, `update_rec_table` |

Twitter 默认动作集：`create_post`, `like_post`, `repost`, `follow`, `do_nothing`, `quote_post`

Reddit 默认动作集：`like_post`, `dislike_post`, `create_post`, `create_comment`, `like_comment`, `dislike_comment`, `search_posts`, `search_user`, `trend`, `refresh`, `do_nothing`, `follow`, `mute`

---

## 4. 主要代码流程

### 4.1 仿真启动流程

```
用户代码 (e.g., quick_start.py)
│
├─ 1. 创建 LLM 模型 (ModelFactory.create)
├─ 2. 创建 AgentGraph 并添加 SocialAgent
├─ 3. oasis.make() → OasisEnv.__init__()
│      ├─ 创建 Channel（异步消息通道）
│      ├─ 创建 Platform（含 SQLite 数据库初始化）
│      └─ 根据 DefaultPlatformType 配置推荐系统参数
│
├─ 4. env.reset()
│      ├─ asyncio.create_task(platform.running())  # 启动平台事件循环
│      └─ generate_custom_agents()
│            ├─ 连接 Channel 到所有 Agent
│            └─ 并发执行所有 Agent 的 sign_up 操作
│
├─ 5. env.step(actions)  ── 可重复调用多轮 ──
│      ├─ platform.update_rec_table()  # 更新推荐表
│      └─ asyncio.gather(*tasks)      # 并发执行所有动作
│            ├─ ManualAction → agent.perform_action_by_data()
│            └─ LLMAction   → agent.perform_action_by_llm()
│
└─ 6. env.close()
       ├─ 发送 EXIT 信号
       └─ 等待平台任务结束
```

### 4.2 LLM 智能体决策流程

```
perform_action_by_llm()
│
├─ 1. env.to_text_prompt()
│      ├─ action.refresh()  →  获取推荐帖子列表
│      ├─ 查询 follower/following 数量
│      └─ listen_from_group()  →  获取群聊消息
│      → 拼接为环境描述文本
│
├─ 2. 构造 User Message
│      "Please perform social media actions after observing
│       the platform environments..."
│
├─ 3. self.astep(user_msg)  →  调用 LLM (通过 CAMEL ChatAgent)
│      └─ LLM 返回 Tool Calls（函数名 + 参数）
│
└─ 4. 执行 Tool Call
       └─ e.g., create_post("Hello World!")
             ├─ channel.write_to_receive_queue()  # 发送到平台
             ├─ Platform 处理请求、写入数据库
             └─ channel.read_from_send_queue()    # 读取结果
```

### 4.3 Agent-Platform 消息通信流程

```
SocialAction.create_post("Hello")
│
├─ perform_action(message="Hello", type="create_post")
│    ├─ channel.write_to_receive_queue((agent_id, "Hello", "create_post"))
│    │    └─ 生成 UUID，放入 receive_queue
│    │
│    └─ channel.read_from_send_queue(message_id)
│         └─ 轮询 send_dict 直到收到响应
│
Platform.running() (持续运行的事件循环)
│    ├─ channel.receive_from()  →  取出消息
│    ├─ 根据 ActionType 分发到对应处理函数
│    │    e.g., _create_post() → INSERT INTO post ...
│    ├─ 记录到 trace 表
│    └─ channel.send_to((message_id, agent_id, result))
```

---

## 5. 项目目录结构

```
oasis/
├── oasis/                      # 核心库代码
│   ├── __init__.py             # 版本号 & 公开 API 导出
│   ├── clock/                  # 沙盒时钟
│   │   └── clock.py
│   ├── environment/            # 仿真环境
│   │   ├── env.py              # OasisEnv 核心类
│   │   ├── env_action.py       # ManualAction / LLMAction
│   │   └── make.py             # 工厂函数
│   ├── social_agent/           # 智能体模块
│   │   ├── agent.py            # SocialAgent (继承 ChatAgent)
│   │   ├── agent_action.py     # SocialAction (28种社交操作)
│   │   ├── agent_environment.py # SocialEnvironment (环境感知)
│   │   ├── agent_graph.py      # AgentGraph (igraph/Neo4j)
│   │   └── agents_generator.py # 批量生成智能体
│   ├── social_platform/        # 社交平台模块
│   │   ├── platform.py         # Platform 核心业务逻辑
│   │   ├── channel.py          # 异步消息通道
│   │   ├── database.py         # SQLite 数据库工具
│   │   ├── recsys.py           # 推荐系统 (4种算法)
│   │   ├── typing.py           # 枚举类型定义
│   │   ├── platform_utils.py   # 平台工具函数
│   │   ├── process_recsys_posts.py # 推荐帖子向量处理
│   │   └── config/             # 配置 (UserInfo, Neo4jConfig)
│   └── testing/                # 测试辅助工具
│       └── show_db.py
├── examples/                   # 使用示例
│   ├── quick_start.py          # 快速入门
│   ├── twitter_simulation_*.py # Twitter 仿真示例
│   ├── reddit_simulation_*.py  # Reddit 仿真示例
│   ├── group_chat_simulation.py # 群聊仿真
│   └── experiment/             # 实验脚本 (极化、反事实等)
├── generator/                  # 数据生成工具
│   ├── twitter/                # Twitter 用户画像生成
│   └── reddit/                 # Reddit 用户画像生成
├── visualization/              # 可视化分析工具
├── test/                       # 单元测试
│   ├── agent/                  # 智能体相关测试
│   └── infra/                  # 基础设施测试 (数据库, 推荐系统)
├── data/                       # 数据目录
├── docs/                       # 文档
├── deploy.py                   # 部署脚本
└── pyproject.toml              # 项目配置 (Poetry)
```

---

## 6. 关键设计模式

### 6.1 异步并发架构

整个系统基于 Python `asyncio` 构建：
- **Platform** 作为常驻异步任务处理请求。
- 多个 **Agent** 通过 `asyncio.gather` 并发执行动作。
- **Semaphore** 控制 LLM 并发调用数量，避免 API 限流。
- **Channel** 通过异步队列和异步安全字典实现非阻塞通信。

### 6.2 类 OpenAI Gym 接口

采用类似强化学习环境的 `make() → reset() → step() → close()` 接口设计，降低使用门槛：
```python
env = oasis.make(agent_graph=graph, platform=platform_type, database_path=path)
await env.reset()
await env.step(actions)
await env.close()
```

### 6.3 Agent-Platform 解耦

Agent 和 Platform 通过 Channel 解耦，实现：
- Agent 不直接操作数据库，所有操作通过消息传递。
- Platform 可独立替换或扩展。
- 支持大规模并发（百万级 Agent 场景）。

### 6.4 可扩展的动作系统

所有社交动作定义在 `ActionType` 枚举中，通过 `SocialAction` 统一封装为 CAMEL `FunctionTool`。新增动作只需：
1. 在 `ActionType` 添加枚举值。
2. 在 `SocialAction` 添加对应方法。
3. 在 `Platform` 实现处理逻辑。

---

## 7. 数据流总结

```
用户画像 (CSV/JSON)
      │
      ▼
  AgentGraph (社交图谱)
      │
      ▼
  SocialAgent (LLM 决策)
      │  ↑
      │  │ 环境感知 (推荐帖子 + 社交信息)
      ▼  │
    Channel (异步消息)
      │  ↑
      ▼  │
   Platform (业务处理)
      │  ↑
      ▼  │
   SQLite DB (持久化)
      │
      ▼
  分析/可视化 (visualization/)
```
