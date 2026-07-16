# 方案 B 详细实现流程：Knowledge Action Cluster（已按本地约束修订）

> 选定方案：`MCP-AI-Agent集群-Knowledge-Action方案.md`  
> 目标：按「后端 / AI 服务优先，前端最后」落地；**实现过程由助手用脚本/pytest 跑通**  
> 修订日期：2026-07-16

---

## 修订纪要（相对初版的冻结决策）

| # | 你的要求 | 本方案落点 |
|---|----------|------------|
| 1 | 本地实现，不要 Docker | 本机安装/使用已有 **PostgreSQL、Redis**；各服务用 `uv run` / 脚本本地启动 |
| 2 | 后期可扩展、可优化 | Provider / Parser / Auth / MCP 插件化预留接口；目录按可演进设计 |
| 3 | 向量 = 本地 Postgres + PGVector | **唯一向量方案**：PostgreSQL + PGVector（本地向量库，不上 Chroma/Qdrant） |
| 4 | Python + uv | 全项目 **Python 3.11+**，包管理锁定为 **uv** |
| 5 | 火山引擎豆包 | Chat：`doubao-seed-1-8-251228`；Embedding：`doubao-embedding-vision-251215` |
| 6 | 文档解析、鉴权 MVP 可暂不做 | **先不实现**；预留 `DocumentParser` / `AuthProvider` 接口，需要时再加 |
| 7 | 冻结语料域 | **公司制度 + 差旅 / 报销 / 请假**（语料先用 Markdown/纯文本即可） |

---

## 0. 开发顺序总原则

**基础设施（本机库）→ MCP / AI 服务 → 编排与业务 API → 前端。**

```text
① 工程骨架（uv workspace）+ 本机 Postgres/Redis 连通
② MCP Server（Knowledge / Business…）     ← 工具层
③ LLM 封装（火山豆包）+ Agent Graph       ← 智能层
④ FastAPI 业务 API + 审计（鉴权可后置）   ← 后端层
⑤ 评测脚本（可无 UI）
⑥ 前端 Chat Console                       ← 最后
⑦ README / 本地启动脚本 / Demo
```

- Agent 集群价值在协作 + 工具 + 治理，用 API / CLI 验证即可  
- 前端只可视化已跑通能力；过早做 UI 易返工  
- **跑通主路径：助手执行 pytest / smoke / CLI，不要求你点界面排障**

---

## 1. 系统拆分（本地多进程，无 Docker）

| 服务 | 职责 | 技术 |
|------|------|------|
| **AI 服务（Orchestrator）** | Agent Graph、调豆包、调 MCP、任务状态 | Python + LangGraph（或自研图）+ Redis |
| **后台服务（API）** | 会话、发消息、审批确认、审计查询 | FastAPI + PostgreSQL |
| **前端（Chat Console）** | 对话、引用、轨迹、确认写操作 | React/Vue + TS（最后做） |

| 组件 | 职责 | 本地说明 |
|------|------|----------|
| **MCP Servers** | Knowledge / Memory / Business… | 本机独立进程或同仓库多入口 |
| **Redis** | 会话活状态、Agent 图进度 | 本机安装并启动 |
| **PostgreSQL + PGVector** | 业务/审计 + **知识切片向量** | 本机库；等价于本地向量数据库 |
| **火山方舟 API** | Chat + Embedding | 外网 API，密钥放 `.env` |

本地进程拓扑：

```text
[Browser]（阶段 6+）
    │ HTTP
    ▼
[chat-console] ──HTTP──► [api / FastAPI :8000]
                              │
                              ├──► 本机 PostgreSQL+PGVector（业务+审计+向量）
                              ├──► 本机 Redis（会话/任务状态）
                              └──► [orchestrator :8001]
                                        │ MCP HTTP
                                        ├── knowledge-mcp :8101
                                        ├── memory-mcp :8102
                                        └── business-mcp :8103
```

启动方式示例（无 Docker）：

```bash
# 终端各开一个，或用 scripts/dev_*.ps1 / .sh 聚合
uv run uvicorn apps.api.main:app --reload --port 8000
uv run uvicorn apps.orchestrator.main:app --reload --port 8001
uv run python -m mcp_servers.knowledge
# …其余 MCP 同理
```

---

## 2. 完整技术栈清单（已冻结）

### 2.1 核心栈

| 类别 | 选型 | 用途 |
|------|------|------|
| 语言 | **Python 3.11+** | 全栈后端 / AI / MCP |
| 包管理 | **uv**（唯一） | 依赖锁定、`uv sync` / `uv run` |
| Web | **FastAPI** | API、可选日后承载 Gateway |
| 活状态 | **本机 Redis** | 会话、Agent 任务状态 |
| 持久化 + 向量 | **本机 PostgreSQL + PGVector** | 业务/审计 + 切片 embedding |
| Chat 模型 | **火山引擎** `doubao-seed-1-8-251228` | Router / 分析 / 生成 |
| Embedding | **火山引擎** `doubao-embedding-vision-251215` | 知识切片向量化 |
| 前端 | Vite + React/Vue + TS | Chat Console（后期） |
| 服务划分 | API / Orchestrator / MCP / 前端 | 便于扩展为更多 Agent/MCP |

### 2.2 配套技术

| 类别 | 选型 | 说明 |
|------|------|------|
| MCP SDK | 官方 Python MCP SDK | Knowledge / Business 等 |
| Agent 编排 | LangGraph 或自研状态机 | 可替换，接口稳定即可 |
| ORM / 迁移 | SQLAlchemy 2.x + Alembic | Postgres 模型 |
| Redis 客户端 | redis-py | 会话状态 |
| 配置 | pydantic-settings + `.env` | 含火山 API Key / Endpoint |
| HTTP | httpx | 调方舟、服务间调用 |
| 日志 | structlog 或 JSON logging | request_id / session_id |
| 测试 | pytest + httpx | 阶段自动验收 |
| 评测 | 自研 `run_eval.py` + 黄金集 | 引用命中、行动成功率 |
| 可观测 | OpenTelemetry（**二期**） | 跨 Agent/MCP Trace |

### 2.3 明确延后（预留接口，本阶段不实现）

| 能力 | MVP | 扩展点（方便以后加） |
|------|-----|----------------------|
| **鉴权 / JWT / 角色** | 暂不做；API 可用固定本地用户或 `X-User-Id` 头 | `AuthProvider` 协议 + `apps/api` 依赖注入位 |
| **PDF/Word 文档解析** | 暂不做；语料用 **Markdown / 纯文本** | `DocumentParser` 协议；ingest 管道可插拔 |
| Docker / K8s | **不做** | 日后若需要再加 `deploy/`，当前不依赖 |
| 企微/飞书通知 | 二期 Comms MCP | MCP 目录预留 `comms/` |
| 模型微调 | 不做 | `packages/llm` Provider 可换模型名 |

### 2.4 扩展与优化设计原则（贯穿全程）

1. **`packages/llm`**：`ChatProvider` / `EmbeddingProvider` 抽象；当前只实现 `VolcengineDoubaoProvider`  
2. **`packages/parsers`**：`DocumentParser` 接口；MVP 仅 `MarkdownParser` / `TextParser`  
3. **`packages/auth`**：`AuthProvider` 接口；MVP 用 `NoAuthProvider` 或 `DevHeaderAuthProvider`  
4. **MCP 按域独立进程/包**：新增知识域或工具 = 新 Server，不改 Orchestrator 内核  
5. **Agent 节点可插拔**：Graph 边可配置；后续加 Agent 不推翻骨架  
6. **配置全部进 `.env`**：换模型、换库、开鉴权靠配置，少改业务代码  

### 2.5 推荐仓库结构

```text
mcp-knowledge-action-cluster/
  pyproject.toml                 # uv 工作区根
  uv.lock
  apps/
    api/                         # FastAPI（会话/审批/审计；鉴权可后挂）
    orchestrator/                # Agent Graph + 调 MCP + 调豆包
    chat-console/                # 前端（最后）
  mcp_servers/
    knowledge/
    memory/
    business/
    comms/                       # 占位，二期
  packages/
    common/                      # 配置、日志、schema
    llm/                         # Provider 抽象 + 火山实现
    parsers/                     # DocumentParser 接口 + md/text
    auth/                        # AuthProvider 接口 + NoAuth/Dev
    mcp_clients/
  data/
    corpus/                      # 公司制度+差旅/报销/请假（md/txt）
      policies/
      travel/
      reimbursement/
      leave/
    golden_set/
  scripts/
    check_local_deps.py          # 检查本机 Postgres/Redis/扩展
    ingest_docs.py
    smoke_knowledge_mcp.py
    demo_cli.py
    run_eval.py
    dev_api.ps1 / dev_api.sh     # 本地启动辅助（可选）
  docs/
  tests/
  .env.example
  README.md
```

**无 `deploy/docker-compose.yml` 依赖。** 本机自行保证 PostgreSQL（含 `vector` 扩展）与 Redis 已运行。

---

## 3. 数据职责划分

| 数据 | 存哪里 | 说明 |
|------|--------|------|
| 当前对话、Agent 图游标、中间草稿 | **Redis** | TTL；key 按 `session_id` |
| 工单 / 草稿 / 待办 | **PostgreSQL** | Business |
| 审计事件 | **PostgreSQL** | 必落库 |
| 文档元数据 | **PostgreSQL** | |
| 文档切片 + embedding | **PostgreSQL + PGVector** | **本地向量库** |
| 用户偏好摘要 | **PostgreSQL**（Memory） | Redis 可缓存 |
| 用户/角色表 | PostgreSQL 可先建表 | **鉴权逻辑后期再挂** |

原则：**编排活状态 → Redis；业务/审计/向量真相 → PostgreSQL(+PGVector)。**

### 3.1 关于「本地 PostgreSQL + PGVector = 本地向量库」

是的，理解正确：

- 切片文本与 `embedding` 列存在同一 Postgres  
- 用 PGVector 做相似度检索（可再加简单关键词/全文作混合检索）  
- **不上**独立 Chroma/Qdrant/Milvus；减少组件，符合本地开发  

入库链路：

```text
data/corpus/**/*.md
  →（MVP）Markdown/Text Parser
  → 切片
  → 火山 doubao-embedding-vision-251215
  → 写入 Postgres chunks + vector 列
  → Knowledge MCP hybrid_search 查询
```

---

## 4. 垂直语料域（已冻结）

**域：公司制度 + 差旅 / 报销 / 请假**

建议目录：

```text
data/corpus/
  policies/           # 综合制度、员工手册摘要等
  travel/             # 差旅标准、审批流程
  reimbursement/      # 报销科目、票据要求
  leave/              # 年假/事假/病假/试用期规则
```

阶段 0 需准备：

- 至少 **5–10 篇** Markdown/纯文本（可虚构但结构像真制度）  
- 黄金集：**10 条问答**（带来源文档名）+ **5 条行动任务**（如「按差旅政策起草上海出差申请并创建待办」）  

三条主用户故事（必须覆盖）：

1. 纯问答 + 引用（如试用期年假）  
2. 对比/归纳（如差旅与报销边界）  
3. 问答后行动 + 确认（创建差旅/请假相关草稿或工单）  

---

## 5. 分阶段实现流程

> 预估 **6–8 周**（可按业余节奏拉长）。  
> 每阶段有完成标准；**验收由脚本/pytest 自动跑通**。

---

### 阶段 0：立项冻结与工程骨架（3–5 天）

**目标：** 冻需求、搭 uv 骨架、确认本机库可用。

#### 做什么

1. 确认语料域已冻结（本节第 4 章）  
2. 写黄金集初稿到 `data/golden_set/`  
3. `uv init` / workspace：`apps`、`packages`、`mcp_servers`、`tests`  
4. `.env.example`（火山 Key、Postgres、Redis、模型名）  
5. `scripts/check_local_deps.py`：检测 Postgres 可连、`CREATE EXTENSION vector`、Redis PING  
6. Agent Graph mermaid 草图；扩展点清单（Auth/Parser 空实现即可）  
7. **不引入 Docker**

#### 完成标准

- [ ] `uv sync` 成功  
- [ ] 本机 Postgres + Redis 连通；PGVector 扩展可用  
- [ ] 语料目录与黄金集文件就位  
- [ ] README 写明：如何装/连本机 Postgres、Redis（无 Docker 步骤）  

#### 自我验证

```bash
uv sync
uv run python scripts/check_local_deps.py
# 期望：postgres ok / vector ok / redis ok
```

---

### 阶段 1：Postgres 模型 + Knowledge 入库（约 1 周）

**目标：** 制度语料进 PGVector，Knowledge MCP 可检索。

#### 做什么

1. Alembic 建表：`documents`、`chunks`（含 vector 列）、`audit_logs`、`tickets`；`users` 表可先建空壳给后期鉴权  
2. **仅启用 PGVector**（不引入其他向量库）  
3. `ingest_docs.py`：只走 Markdown/Text Parser → 切片 → **豆包 Embedding** → 入库  
4. Knowledge MCP：`hybrid_search` / `get_document_section` / `list_sources`  
5. `DocumentParser` 接口就位；PDF/DOCX 类 `NotImplemented` 或未注册  

#### 完成标准

- [ ] 差旅/报销/请假相关语料入库 ≥ 5 篇  
- [ ] Knowledge MCP 三工具可被 smoke 调用  
- [ ] 检索结果含 `doc_id / title / section / score`  

#### 自我验证

```bash
uv run python scripts/ingest_docs.py
uv run python scripts/smoke_knowledge_mcp.py   # 如搜「差旅报销」
uv run pytest tests/test_knowledge_search.py -q
```

---

### 阶段 2：豆包 LLM + 最小 Agent Graph（问答闭环）（约 1–1.5 周）

**目标：** `问题 → Router → Researcher → Analyst → 带引用答案`（CLI 即可）。

#### 做什么

1. `packages/llm`：`VolcengineDoubaoProvider`  
   - `chat()` → `doubao-seed-1-8-251228`  
   - `embed()` → `doubao-embedding-vision-251215`  
2. 三 Agent：Router / Researcher / Analyst（暂无 Executor）  
3. Orchestrator + Redis 任务状态  
4. 问答结束写 `audit_logs`  
5. `demo_cli.py` 打印答案 + citations + `agent_trace`  

#### 完成标准

- [ ] 黄金问答至少约 7/10 有合理引用  
- [ ] Redis 可见 `session:*`  
- [ ] Postgres 有审计行  
- [ ] Provider 抽象在，换模型名主要改配置  

#### 自我验证

```bash
uv run python scripts/demo_cli.py
uv run pytest tests/test_agent_qa_flow.py -q
```

---

### 阶段 3：FastAPI 暴露能力（鉴权可后置）（约 1 周）

**目标：** HTTP API 可供脚本与未来前端调用；**鉴权不做死，只留挂载点。**

#### 做什么

1. FastAPI `apps/api`  
   - `POST /chat/sessions`  
   - `POST /chat/sessions/{id}/messages`  
   - `GET /chat/sessions/{id}`（含 `agent_trace` / `citations`）  
   - `GET /audit/events`  
   - `GET /debug/sessions/{id}`（开发环境）  
2. **鉴权：** 使用 `NoAuthProvider` 或 `DevHeaderAuthProvider`（如 `X-User-Id: demo`）；  
   - **不实现**完整 login/JWT；路由层预留 `Depends(get_current_user)`  
3. 调 Orchestrator（推荐本机 HTTP `:8001`）  
4. CORS、统一错误码、日志  
5. `/docs` 可打开（可选对照，验收靠 pytest）  

#### 完成标准

- [ ] pytest/curl 跑通：建会话 → 提问 → 带回引用回复  
- [ ] `/debug/sessions/{id}` 可用  
- [ ] 代码中可见 Auth 扩展点，切换实现无需大改路由  

#### 自我验证

```bash
uv run pytest tests/test_api_chat.py -q
# 或 httpx/curl 脚本走主路径
```

---

### 阶段 4：Business MCP + Executor + 审批闸门（约 1–1.5 周）

**目标：** 差旅/请假等「能办事」，写操作必须确认。

#### 做什么

1. Business MCP → Postgres `tickets`  
2. Executor + Critic/Guard  
3. `awaiting_confirmation`（Redis）；确认前不落写  
4. API：`pending-actions` / `confirm` / `reject`  
5. 权限策略可先写死简单规则；**真正角色体系等 Auth 接入后再细化**  

#### 完成标准

- [ ] 黄金行动任务约 3/5 能出正确 `action_plan`  
- [ ] 未 confirm 无工单；confirm 后有工单 + 审计  

#### 自我验证

```bash
uv run python scripts/demo_cli.py --action
uv run pytest tests/test_action_gate.py -q
```

---

### 阶段 5：Memory + Guard + 评测（约 0.5–1 周）

#### 做什么

1. Memory MCP  
2. Guard：无引用降级/拒答；行动与制度冲突拦截  
3. `run_eval.py` + 报告  

#### 自我验证

```bash
uv run python scripts/run_eval.py
uv run pytest tests/test_guardrails.py -q
```

---

### 阶段 6：前端 Chat Console（最后，约 1–1.5 周）

#### 做什么

1. 对话 + 引用面板 + Agent 轨迹 + 待确认行动  
2. 只消费已有 API；登录页可先做「开发用户」占位，真实鉴权后补  

#### 完成标准

- [ ] UI 走通三条主用户故事  
- [ ] 轨迹能看出多 Agent  

---

### 阶段 7：本地收尾与演示（3–5 天）

#### 做什么

1. `scripts/` 本地一键/分步启动说明（**无 Docker**）  
2. README：本机 Postgres/Redis/uv/火山 Key、启动顺序、Demo  
3. `docs/demo-script.md`、精简 `architecture.md`  

#### 自我验证

```bash
# 按 README 从零启动本机依赖与各 uv 进程，跑 demo 脚本计时
uv run python scripts/demo_cli.py
uv run pytest -q
```

---

### 阶段 8（二期扩展，按需）

- 接入真实 **JWT/角色鉴权**（实现 `AuthProvider`）  
- 增加 **PDF/DOCX Parser**  
- Comms MCP、SSE 流式、OTel、第二知识域插件  
- （可选）日后才考虑容器化，**非本方案前提**  

---

## 6. 阶段依赖与硬规则

```text
0 骨架 → 1 Knowledge+PGVector → 2 豆包 Agent 问答
  → 3 FastAPI → 4 行动审批 → 5 评测 → 6 前端 → 7 收尾
```

1. 阶段 2 未绿不做前端  
2. 阶段 4 审批未稳，前端不得绕过确认  
3. 黄金集在阶段 0 就必须存在  
4. 全程不引入 Docker 作为运行依赖  

---

## 7. 每阶段产出物

| 阶段 | 关键产出 |
|------|----------|
| 0 | uv 工程、本机依赖检查、语料/黄金集、扩展点空壳 |
| 1 | PGVector 知识库、Knowledge MCP |
| 2 | 豆包 Orchestrator + CLI 问答闭环 |
| 3 | FastAPI Chat/审计 API（弱鉴权/无鉴权 + 扩展点） |
| 4 | Business MCP、审批闸门 |
| 5 | 评测报告、Guard、Memory |
| 6 | Chat Console |
| 7 | 本地启动文档 + Demo |

---

## 8. 本地端口约定

| 服务 | 端口 |
|------|------|
| chat-console | 5173 |
| api | 8000 |
| orchestrator | 8001 |
| knowledge-mcp | 8101 |
| memory-mcp | 8102 |
| business-mcp | 8103 |
| postgres | 5432（本机） |
| redis | 6379（本机） |

---

## 9. 环境变量（`.env.example`）

```text
# 本机库
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/ka_cluster
REDIS_URL=redis://localhost:6379/0

# 火山引擎（方舟）— 按你控制台实际 Endpoint 填写
ARK_API_KEY=...
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-seed-1-8-251228
EMBEDDING_MODEL=doubao-embedding-vision-251215

# 服务发现（本地）
KNOWLEDGE_MCP_URL=http://localhost:8101
BUSINESS_MCP_URL=http://localhost:8103
MEMORY_MCP_URL=http://localhost:8102
ORCHESTRATOR_URL=http://localhost:8001

# 鉴权（MVP 可关；预留）
AUTH_PROVIDER=none
# AUTH_PROVIDER=dev_header
# JWT_SECRET=  # 接入真实鉴权时再填

# 解析（MVP 仅 md/text）
PARSER_ENABLED=markdown,text
```

> `ARK_BASE_URL` 以你火山控制台文档为准；实现时在 `VolcengineDoubaoProvider` 内对接方舟兼容接口。

---

## 10. 自我验证总策略

1. **组件级**：smoke / pytest  
2. **链路级**：CLI 或 API 脚本打通用户故事  
3. **数据级**：Redis 有状态；Postgres 有审计/业务/向量行  

排障见第 11 节。

---

## 11. Debug 手段（以自动跑通为主）

> **主路径：助手用 pytest / smoke / CLI 跑通并修到绿。**  
> Swagger 可选对照，不要求你日常点界面排障。

### 11.1 谁负责跑通

| 方式 | 谁来做 | 用途 |
|------|--------|------|
| pytest / smoke / demo_cli / curl 脚本 | **实现过程自动执行（主路径）** | 验收、回归、定位 |
| Swagger `/docs` | 可选 | 对照请求/响应 |
| 前端 | 阶段 6+ 看观感 | 逻辑回后端测试 |

### 11.2 分层排查

```text
自动化脚本 → FastAPI → Orchestrator → 豆包 API / MCP → Redis / Postgres+PGVector
```

### 11.3 内建能力

- `agent_trace`、`audit_logs`、`GET /debug/sessions/{id}`  
- 结构化日志（`request_id` / `session_id` / `agent` / `mcp_tool`）  
- LLM Mock/Replay（单测可不打真实豆包）  
- 每阶段可重复 smoke 命令  

### 11.4 典型故障

| 现象 | 先查 |
|------|------|
| 胡编无引用 | 检索是否命中；citations 是否空 |
| 卡住不结束 | Redis `current_node`；是否待确认；豆包超时 |
| 工具失败 | MCP smoke 入参出参 |
| 确认无工单 | audit `execute` + `tickets` |
| Embedding/Chat 失败 | `.env` 模型名、Key、Base URL、方舟配额 |

### 11.5 自动跑通手势

```text
1. uv run pytest / smoke：建会话 → 发黄金问题
2. 断言 answer / citations / agent_trace
3. 失败则 debug session 或 Redis
4. 查 audit；再按 request_id 查豆包/MCP 日志
5. 写操作再跑 confirm 断言
```

---

## 12. 开发顺序结论

1. Knowledge MCP + PGVector 入库  
2. 豆包 + Agent Graph CLI 跑通  
3. FastAPI（鉴权后置）  
4. 行动审批  
5. 评测  
6. 前端  
7. 本地文档收尾  

---

## 13. 下一步（阶段 0）

1. 用 **uv** 初始化仓库骨架（无 Docker）  
2. 写 `check_local_deps.py` + `.env.example`（写入豆包两个模型名）  
3. 准备「制度 + 差旅/报销/请假」Markdown 语料与黄金集  
4. 落地 `llm` / `parsers` / `auth` 空接口与 NoAuth/Markdown 最小实现  

需要开工时直接说，我按本文阶段 0 开始搭骨架并跑通本机依赖检查。
