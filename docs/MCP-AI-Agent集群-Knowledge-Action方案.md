# MCP AI Agent 集群备选方案：Knowledge Action Cluster

> 定位：已选定落地的方案 B（相对 DevOps 方案 A）。  
> 侧重点：**更强的 AI / 多 Agent 智能属性**，业务壳为「企业知识问答 + 可行动执行」。  
> 日期：2026-07-15｜**约束修订：2026-07-16**（见文末「落地约束」）  
> 详细实现步骤以 `方案B-详细实现流程.md` 为准。

---

## 1. 一句话结论

**备选主方向：做「知识问答 + 工具行动」多 Agent 集群（Knowledge Action Cluster）。**

用户用自然语言提需求（例如「帮我查上季度报销政策，并给张三开一张符合规则的差旅申请草稿」），集群内多个 AI Agent 协作完成：

理解意图 → 检索知识 → 交叉验证 → 规划行动 →（可选）调用业务工具执行 → 产出可引用答案与审计记录。

这是典型的 **AI Agent 集群项目**：大模型负责推理与协作，MCP 负责连接知识库与业务系统。

---

## 2. 和方案 A（DevOps）的核心差异

| 维度 | 方案 A：DevOps Copilot | 方案 B：Knowledge Action（本文件） |
|------|------------------------|-------------------------------------|
| AI 感观 | 偏运维自动化，AI 是大脑 | **AI 更显眼**：对话、推理、检索、规划是主界面 |
| 触发方式 | 告警/事件驱动 | **自然语言对话驱动** |
| Agent 协作重点 | 分诊→调查→执行 | **理解→检索→推理→规划→执行→评审** |
| 业务壳 | IT 事件响应 | 企业内部知识 + 行动助手 |
| 市场需求 | 高（SRE/平台） | **更高覆盖面**（全员可用的企业 AI 助手） |
| 架构完整度 | 极高（审批、写操作多） | 高（检索+行动+引用+权限） |
| 作品集观感 | 「我会企业级运维 Agent」 | 「我会多 Agent 智能协作与落地」 |
| 适合人群 | 想走平台/SRE/基础设施 | **想突出 AI Agent / LLM 应用能力** |

两套底层都可以共用同一套：**MCP Gateway + Orchestrator + MCP Server 池**。  
差别主要在 **Agent 角色设计、交互形态、垂直场景**。

---

## 3. 市场依据：为什么这个方向也「能卖」

### 3.1 企业最普遍的 AI 刚需

几乎所有组织都有同一类问题：

1. 知识散落在 Confluence / Notion / 飞书 / 共享盘 / 代码注释  
2. 员工反复问「政策是什么」「流程怎么走」「上次怎么处理的」  
3. 只回答不够，还希望 AI **顺便办一件事**（建工单、填表、发通知、生成草稿）

这正好对应 2026 年高频场景里的：

- **Internal Knowledge Search（RAG + 引用）**  
- **Conversational Agent + Tool Use（问答后可行动）**  
- **Multi-Agent 分工**（检索员、分析员、执行员、质检员）

### 3.2 市场在买什么（AI 视角）

不只是「能聊天」，而是：

| 能力 | 为什么值钱 |
|------|------------|
| 多 Agent 分工协作 | 单 Agent 易幻觉、易越权；分工后更稳 |
| 可引用答案（Citation） | 企业要能追到来源文档 |
| 检索后行动（RAG → Action） | 从「答问题」升级到「办事情」 |
| 权限与审批 | 不同角色看到的知识、能执行的动作不同 |
| MCP 标准化接工具 | 换模型/换客户端不重写集成 |

一句话：**这是「企业 AI 助手」赛道，MCP 是连接层，多 Agent 是智能层。**

---

## 4. 产品定位

### 4.1 对外一句话

> **基于 MCP 的企业多 Agent 智能助手：能查得准、说得出出处、在权限内能办事。**

### 4.2 典型用户故事

1. **纯问答**  
   「试用期员工年假怎么算？」→ 检索制度文档 → 给出答案 + 引用段落。

2. **对比推理**  
   「A 方案和 B 方案的发布规范差在哪？」→ 多文档检索 → Analyst Agent 对比 → 结构化结论。

3. **问答后行动**  
   「根据差旅政策，帮我起草一趟上海出差申请，并创建待办。」→ 检索政策 → 生成符合规则的草稿 → 调用 Ticket/Todo MCP 创建（可要求确认）。

4. **跨系统聚合**  
   「上周客户投诉里，和支付相关的有哪些，对应工单状态？」→ 知识库 + CRM/工单 MCP 联合查询 → 汇总报告。

---

## 5. 目标架构（AI 集群形态）

```
┌─────────────────────────────────────────────────────────────┐
│  Clients：Web Chat / Cursor / Claude / 企微·飞书 Bot         │
└────────────────────────────┬────────────────────────────────┘
                             │ 自然语言 + MCP
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP Gateway                                                │
│  - 用户身份 / 租户 / 角色权限                                │
│  - 工具与知识源目录聚合                                      │
│  - 审计：谁问了什么、调了哪些工具、看了哪些文档              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Multi-Agent Orchestrator（AI 集群大脑）                    │
│  - 会话记忆 / 任务状态（Redis）                             │
│  - 工作流图：Router → 并行专家 → Reducer → Action Gate      │
│  - 模型路由：便宜模型做路由，强模型做推理                   │
│  - 人机确认：涉及写操作必须二次确认                         │
└───┬──────────┬──────────┬──────────┬──────────┬─────────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
 Router    Researcher  Analyst   Executor   Critic/Guard
 Agent      Agent       Agent     Agent      Agent
    │          │          │          │          │
    └──────────┴────┬─────┴──────────┴──────────┘
                    │ 通过 MCP 调用
                    ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │ Knowledge│ │ Memory   │ │ Business │ │ Comms    │
     │ MCP Pool │ │ MCP Pool │ │ MCP Pool │ │ MCP Pool │
     │ 文档/向量 │ │ 会话/画像 │ │ 工单/CRM │ │ 通知/邮件 │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 5.1 Agent 角色（突出「AI 集群」）

| Agent | 职责 | 是否强依赖 LLM |
|-------|------|----------------|
| Router Agent | 意图分类、拆子任务、选专家 | 是（可用小模型） |
| Researcher Agent | 检索知识、召回证据、附引用 | 是 |
| Analyst Agent | 对比、归纳、计算、形成结论 | 是（强模型） |
| Executor Agent | 调业务 MCP 执行动作 | 是 + 工具 |
| Critic / Guard Agent | 检查幻觉、越权、缺引用、政策冲突 | 是（质检） |

这比「一个 ChatBot + RAG」更接近你要的 **AI Agent 集群**：有分工、有辩论/质检、有行动闸门。

### 5.2 和「普通 RAG 聊天机器人」的区别

| 普通 RAG Bot | 本方案 Knowledge Action Cluster |
|--------------|----------------------------------|
| 单 Agent | 多 Agent 协作 |
| 只回答 | 回答 + 可执行行动 |
| 工具直连 | MCP Gateway 统一治理 |
| 引用可有可无 | 引用与审计为一等公民 |
| 难控越权 | Guard + 权限 + 审批 |

---

## 6. 技术选型（已按落地约束冻结）

| 模块 | 选型 | 说明 |
|------|------|------|
| 语言 / 包管理 | **Python 3.11+ + uv** | 全项目统一 |
| 运行方式 | **本机多进程，不用 Docker** | 本机 PostgreSQL、Redis |
| 编排 | LangGraph / 自研 Agent Graph | Router→Research→Analyze→Execute→Critique |
| Chat 模型 | 火山引擎 **doubao-seed-1-8-251228** | `packages/llm` Provider 可换 |
| Embedding | 火山引擎 **doubao-embedding-vision-251215** | 切片向量化 |
| 检索 / 向量库 | **本地 PostgreSQL + PGVector** | 即本地向量数据库；可加关键词混合检索 |
| MCP | 官方 Python MCP SDK | 知识、业务、通知分 Server |
| API | FastAPI | 会话 / 审批 / 审计；鉴权后挂 |
| 鉴权 / 文档解析 | **MVP 不做**，预留接口 | `AuthProvider` / `DocumentParser` |
| 语料域 | **公司制度 + 差旅/报销/请假** | 先用 Markdown/纯文本 |
| 评测 | 黄金集 + 引用命中 + 任务成功率 | AI 差异化关键 |
| 前端 | Chat UI + 引用 + Agent 轨迹 | 最后做 |

**扩展原则：** Provider / Parser / Auth / MCP 插件化，方便后期优化，不推翻骨架。

**刻意突出 AI 的两个加分项：**

1. **Agent 轨迹可视化**：每一步哪个 Agent、用了什么证据、为何路由。  
2. **评测集**：20–50 条真实问答/任务，能量化「有没有变好」。

---

## 7. MVP 路线图（建议 6–8 周）

### Phase 0（3–5 天）：定 AI 闭环

- **语料域已冻结**：公司制度 + 差旅 / 报销 / 请假  
- 定义 10 个黄金问题 + 5 个「问答后行动」任务  
- 画清 Agent 图；鉴权/解析仅留扩展点  
- uv 工程骨架 + 本机 Postgres/Redis/PGVector 检查（无 Docker）

### Phase 1（1–2 周）：多 Agent 问答跑通

- Knowledge MCP：`search` / `get_chunk` / `list_sources`  
- Router + Researcher + Analyst 三 Agent  
- Chat UI 展示答案 + 引用  
- 无写操作，先把「答得准」做稳

### Phase 2（1–2 周）：升级为可行动集群

- Business MCP：`create_ticket` / `create_draft` / `notify`  
- Executor + Critic/Guard  
- 写操作必须确认  
- Gateway：身份、审计、工具策略

### Phase 3（1–2 周）：AI 产品化

- Agent 协作时间线（集群感）  
- 评测报告：引用命中率、拒答率、任务完成率  
- 记忆 MCP：用户偏好 / 近期上下文  
- README + Demo 脚本 + 架构说明

### Phase 4（可选）：第二技能包

- 挂上第二个知识域（例如「产品 FAQ」）证明可扩展  
- 或增加「对抗质检」：故意注入错误文档，看 Guard 能否拦住

---

## 8. 最小 MCP 工具集

### Knowledge MCP

- `hybrid_search`：混合检索  
- `get_document_section`：按章节取原文  
- `list_citations`：返回引用元数据  

### Memory MCP

- `get_session_summary` / `upsert_user_preference`

### Business MCP

- `create_ticket` / `update_ticket` / `create_document_draft`

### Comms MCP（可二期）

- `send_notification` / `post_channel_message`

### Gateway 策略示例

- 实习生：只读知识，禁止 Business 写接口  
- 经理：可读 + 可创建草稿，发送通知需确认  
- 管理员：可配置知识源与策略

---

## 9. 仓库结构建议

```text
mcp-ai-agent-cluster/
  apps/
    gateway/
    orchestrator/           # Agent Graph 在这里
    chat-console/           # 对话 + 引用 + Agent 轨迹
  agents/
    router/
    researcher/
    analyst/
    executor/
    critic/
  mcp-servers/
    knowledge/
    memory/
    business/
    comms/
  packages/
    llm/                    # Provider 抽象
    eval/                   # 黄金集与评测
    shared/
  data/
    corpus/                 # 示例知识库
    golden-set/
  deploy/
    docker-compose.yml
  docs/
    architecture.md
    agent-graph.md
    eval-report.md
```

---

## 10. 作品集叙事（AI 向）

### 推荐说法

> 我做了一个 MCP 驱动的多 Agent 智能集群：  
> Router / Researcher / Analyst / Executor / Critic 分工协作，  
> 通过 MCP Gateway 安全连接知识库与业务系统，  
> 既能给出带引用的答案，也能在权限与审批下执行行动。  
> 项目重点不是单次 Chat，而是 **可治理、可评测、可扩展的 AI Agent 集群架构**。

### 演示脚本（3 分钟）

1. 问一个需要跨文档的问题 → 展示多 Agent 轨迹与引用  
2. 提一个「生成并创建待办」的任务 → 展示审批闸门  
3. 用无权限账号尝试写操作 → 展示 Guard/Gateway 拦截  
4. 打开评测摘要 → 展示不是纯 Demo

---

## 11. 风险与边界

| 风险 | 应对 |
|------|------|
| 做成普通 RAG 聊天窗 | 强制多 Agent 图 + 轨迹 UI + Critic |
| 幻觉伤信任 | 无引用不答关键结论；Guard 检查 |
| 行动乱执行 | 默认只读，写操作二次确认 |
| 语料太假 | 自建「制度+差旅/报销/请假」Markdown，结构像真制度 |
| 只调 API 无工程 | 审计、评测、MCP 分层必须进 MVP；鉴权可后置但要留接口 |
| 本地环境差异 | 提供 `check_local_deps`；不依赖 Docker |

---

## 12. 方案状态

**已选定方案 B。** 与方案 A 的对比仅作历史参考。  
执行细节、阶段验收与 Debug 约定以 **`方案B-详细实现流程.md`** 为准。

---

## 13. 落地约束（2026-07-16）

1. 本地实现，**不用 Docker**  
2. 架构预留扩展（LLM/Parser/Auth/MCP 插件化）  
3. 向量：**PostgreSQL + PGVector**（本地向量库）  
4. **Python + uv**  
5. 模型：火山 **doubao-seed-1-8-251228** + **doubao-embedding-vision-251215**  
6. 文档解析、完整鉴权：**MVP 不做**，预留添加接口  
7. 语料域：**公司制度 + 差旅/报销/请假**  

---

## 14. 下一步

按 `方案B-详细实现流程.md` **阶段 0** 开工：uv 骨架、本机依赖检查、语料与黄金集。

---

## 15. 总结

> **Knowledge Action Cluster = 多 Agent 智能协作 + MCP 连接知识与业务 + 可引用、可行动、可治理。**

在本地 Postgres/Redis + 火山豆包约束下，先跑通「制度域问答 + 可确认行动」，再逐步挂鉴权、解析与更多 MCP。
