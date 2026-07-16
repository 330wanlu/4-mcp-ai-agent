# Knowledge Action Cluster

基于 MCP 的企业多 Agent 智能助手（方案 B）：制度知识问答 + 可确认行动。

详细阶段计划见 [`docs/方案B-详细实现流程.md`](docs/方案B-详细实现流程.md)。  
阶段 0 回溯文档见 [`docs/阶段0-工程骨架与本机依赖.md`](docs/阶段0-工程骨架与本机依赖.md)。

## 冻结约束

- **无 Docker**：本机 PostgreSQL + Redis（Memurai）+ `uv run` 多进程
- **向量库**：PostgreSQL + PGVector（不上 Chroma/Qdrant）
- **模型**：火山豆包 Chat `doubao-seed-1-8-251228` / Embedding `doubao-embedding-vision-251215`
- **语料域**：公司制度 + 差旅 / 报销 / 请假
- **鉴权 / PDF 解析**：MVP 不做，已预留 `AuthProvider` / `DocumentParser`

## 本机依赖（无 Docker）— 当前开发机约定

### 1. Python + uv

- Python **3.11+**（当前：3.13）
- `uv sync`（项目已配置清华 PyPI 镜像）

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群
uv sync
```

### 2. PostgreSQL + PGVector

| 项 | 值 |
|----|-----|
| 安装目录 | `E:\AI\postgreSQL\install` |
| 服务 | `postgresql-x64-18` |
| 数据库 | `mcp_agent_db` |
| PGVector 归档 | `E:\AI\PGVector_18`（v0.8.3 for PG18） |
| 连接串 | 见 `.env` 的 `DATABASE_URL` |

```text
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@localhost:5432/mcp_agent_db
```

扩展已启用：`CREATE EXTENSION vector` → version **0.8.3**。

### 3. Redis（Memurai）

| 项 | 值 |
|----|-----|
| 软件 | Memurai Developer 4.1.2 |
| 安装目录 | `E:\AI\Memurai` |
| 服务 | `Memurai` |
| 端口 | 6379 |

```text
REDIS_URL=redis://localhost:6379/0
```

验证：`E:\AI\Memurai\memurai-cli.exe ping` → `PONG`。

### 4. 火山方舟 Key（阶段 1+）

```powershell
# .env 已从 .env.example 落地；补 ARK_API_KEY
```

## 阶段 0 自检（已全绿）

```powershell
uv sync
uv run python scripts/check_local_deps.py
# postgres ok / vector ok / redis ok

uv run pytest tests/test_phase0_skeleton.py -q
# 5 passed
```

## 目录速览

```text
apps/           # api / orchestrator（chat-console 后期）
mcp_servers/    # knowledge / memory / business / comms
packages/       # common / llm / parsers / auth / mcp_clients
data/corpus/    # 制度语料（Markdown）
data/golden_set/# 10 问答 + 5 行动任务
scripts/        # check_local_deps 等
docs/           # 方案与阶段文档
```

## 本地端口（约定）

| 服务 | 端口 |
|------|------|
| api | 8000 |
| orchestrator | 8001 |
| knowledge-mcp | 8101 |
| memory-mcp | 8102 |
| business-mcp | 8103 |
| postgres | 5432 |
| redis / Memurai | 6379 |

```powershell
uv run uvicorn ka_api.main:app --reload --port 8000
uv run uvicorn ka_orchestrator.main:app --reload --port 8001
```

## 当前进度

- [x] 阶段 0：uv 骨架、语料、黄金集、扩展点、本机依赖全绿
- [x] 阶段 1：PGVector 入库 + Knowledge MCP（三工具可检索）
- [ ] 阶段 2：豆包 + Agent 问答闭环
- [ ] 阶段 3+：见方案文档

阶段 1 回溯：[`docs/阶段1-知识入库与Knowledge-MCP.md`](docs/阶段1-知识入库与Knowledge-MCP.md)。

### 阶段 1 常用命令

```powershell
uv run alembic upgrade head
uv run python scripts/ingest_docs.py
uv run python scripts/smoke_knowledge_mcp.py --query 差旅报销
uv run pytest tests/test_phase0_skeleton.py tests/test_knowledge_search.py -q
```
