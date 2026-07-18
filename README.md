# Knowledge Action Cluster

基于 MCP 的企业多 Agent 智能助手（**方案 B**）：制度知识问答 + 可确认行动。

> **无 Docker** · 本机 PostgreSQL+PGVector · Redis/Memurai · `uv` · 火山豆包

| 文档 | 说明 |
|------|------|
| [`docs/方案B-详细实现流程.md`](docs/方案B-详细实现流程.md) | 阶段计划与验收 |
| [`docs/architecture.md`](docs/architecture.md) | 架构速览 |
| [`docs/demo-script.md`](docs/demo-script.md) | 3–5 分钟演示脚本 |
| [`docs/agent-graph.md`](docs/agent-graph.md) | Agent 图 |
| [`docs/eval-report.md`](docs/eval-report.md) | 最新评测摘要 |

---

## 冻结约束

- **无 Docker**：本机 PostgreSQL + Redis（Memurai）+ `uv run` 多进程  
- **向量库**：PostgreSQL + PGVector（不上 Chroma/Qdrant）  
- **模型**：Chat `doubao-seed-1-8-251228` / Embedding `doubao-embedding-vision-251215`  
- **语料域**：公司制度 + 差旅 / 报销 / 请假  
- **鉴权 / PDF**：MVP 预留 `AuthProvider` / `DocumentParser`；Console 可用 `dev_header`

---

## 从零启动（本机）

### 1. 准备依赖

| 组件 | 要求 |
|------|------|
| Python | 3.11+（推荐 3.13）+ [uv](https://github.com/astral-sh/uv) |
| PostgreSQL | 含 `vector` 扩展；库名建议 `mcp_agent_db` |
| Redis | 端口 6379（本机可用 Memurai） |
| Node.js | 18+（仅 Chat Console） |
| 火山方舟 | `.env` 中 `ARK_API_KEY` |

本机约定示例（可按实际改）：

| 项 | 值 |
|----|-----|
| Postgres 服务 | `postgresql-x64-18` |
| 数据库 | `mcp_agent_db` |
| Redis | Memurai `E:\AI\Memurai` → `6379` |

### 2. 安装与配置

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群
uv sync
copy .env.example .env
# 编辑 .env：DATABASE_URL / REDIS_URL / ARK_API_KEY
# Chat Console 建议：AUTH_PROVIDER=dev_header

uv run python scripts/check_local_deps.py
# 期望：postgres ok / vector ok / redis ok

uv run alembic upgrade head
uv run python scripts/ingest_docs.py
```

### 3. 启动服务

**方式 A — 一键（推荐）**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1
```

会新开两个窗口：API `:8000` + Chat Console `:5173`。

**方式 B — 分步**

```powershell
# 终端 1：API（默认 ORCHESTRATOR_MODE=local，MCP 进程内调用）
powershell -File scripts\dev_api.ps1

# 终端 2：前端
powershell -File scripts\dev_chat_console.ps1
```

| 入口 | URL |
|------|-----|
| Chat Console | http://127.0.0.1:5173 |
| API / OpenAPI | http://127.0.0.1:8000/docs |

可选独立进程（一般不必）：

```powershell
powershell -File scripts\dev_orchestrator.ps1   # :8001，需 ORCHESTRATOR_MODE=http
uv run python -m ka_knowledge_mcp.server      # :8101
uv run python -m ka_memory_mcp.server         # :8102
uv run python -m ka_business_mcp.server       # :8103
```

### 4. 快速 Demo（无 UI）

```powershell
uv run python scripts/demo_cli.py --question "试用期员工年假怎么算？"
uv run python scripts/demo_cli.py --action
uv run python scripts/run_eval.py
```

完整演示话术见 [`docs/demo-script.md`](docs/demo-script.md)。

---

## 端口约定

| 服务 | 端口 |
|------|------|
| chat-console | 5173 |
| api | 8000 |
| orchestrator | 8001 |
| knowledge-mcp | 8101 |
| memory-mcp | 8102 |
| business-mcp | 8103 |
| postgres | 5432 |
| redis / Memurai | 6379 |

---

## 目录速览

```text
apps/
  api/              # FastAPI Chat / 确认 / 审计
  orchestrator/     # Agent Graph
  chat-console/     # Vite React UI
mcp_servers/        # knowledge / memory / business / comms(占位)
packages/           # common / llm / parsers / auth / mcp_clients
data/corpus/        # 制度 Markdown
data/golden_set/    # 10 问答 + 5 行动
scripts/            # 启动 / 入库 / demo / 评测 / 冒烟
docs/               # 方案、阶段回溯、架构、演示
tests/              # pytest 验收
```

---

## 自验证 / 联验

```powershell
# 阶段 7 冒烟（依赖 + demo 计时 + 全量 pytest，较慢）
powershell -File scripts\smoke_phase7.ps1

# 或仅 demo（跳过 pytest）
powershell -File scripts\smoke_phase7.ps1 -SkipPytest

# 全量测试
uv run pytest -q
```

前端构建：

```powershell
cd apps\chat-console
npm install
npm run build
npm run smoke
```

---

## 进度（阶段 0–7）

- [x] 0 工程骨架与本机依赖  
- [x] 1 PGVector + Knowledge MCP  
- [x] 2 豆包 Agent 问答闭环  
- [x] 3 FastAPI Chat / 审计  
- [x] 4 Business + 审批闸门  
- [x] 5 Memory + Guard + 评测  
- [x] 6 Chat Console 前端  
- [x] 7 本地收尾与演示文档  

阶段回溯：`docs/阶段0-…` … `docs/阶段7-本地收尾与演示.md`

二期（阶段 8）：JWT 鉴权、PDF/DOCX、Comms、SSE、OTel 等，见方案文档。
