# 架构速览（Knowledge Action Cluster）

> 方案 B · 本地多进程 · **无 Docker**  
> 详细 Agent 图见 [`agent-graph.md`](./agent-graph.md)

## 一句话

MCP 驱动的多 Agent 集群：能查制度、带引用回答、在确认闸门下起草差旅/请假等行动。

## 进程拓扑

```text
[Browser :5173]  Chat Console
       │ HTTP /api → proxy
       ▼
[API :8000]  FastAPI（会话 / 消息 / 确认 / 审计）
       │ ORCHESTRATOR_MODE=local（默认）
       ▼
[Orchestrator 进程内]  Agent Graph + 豆包
       ├── Knowledge MCP（local 或 :8101）→ PGVector
       ├── Memory MCP（local 或 :8102）→ Postgres
       └── Business MCP（local 或 :8103）→ tickets
              │
              ├── PostgreSQL + PGVector（业务 / 审计 / 向量 / Memory）
              └── Redis / Memurai（会话活状态 / pending_action）
```

默认开发路径：**只起 API + 前端** 即可（Orchestrator / MCP 走进程内 `local`）。  
需要拆进程时再起 `:8001` / `:8101–8103`，并把 `.env` 切到 `http`。

## 分层

| 层 | 职责 | 位置 |
|----|------|------|
| 前端 | 对话、引用、轨迹、确认 | `apps/chat-console` |
| 业务 API | Chat / 审批 / 审计 / 弱鉴权 | `apps/api` |
| 编排 | Router→Researcher→Analyst→Executor→Guard + Memory | `apps/orchestrator` |
| MCP | Knowledge / Memory / Business（Comms 占位） | `mcp_servers/*` |
| 共享包 | llm / auth / parsers / mcp_clients / common | `packages/*` |

## 数据职责

| 数据 | 存哪里 |
|------|--------|
| 会话游标、pending_action、agent_trace（活状态） | Redis |
| 文档切片 + embedding | Postgres + PGVector |
| tickets / audit_logs / session_summaries / user_preferences | Postgres |

## 扩展点（MVP 已留接口）

| 扩展点 | 当前 | 二期 |
|--------|------|------|
| `ChatProvider` / `EmbeddingProvider` | 火山豆包 | 换模型名/厂商 |
| `AuthProvider` | none / dev_header | JWT/角色 |
| `DocumentParser` | Markdown/Text | PDF/DOCX |
| MCP 域 | Knowledge/Memory/Business | Comms、更多业务域 |

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
| redis | 6379 |

## 主路径

```text
提问 → Memory.load → Router → Knowledge 检索 → Analyst(+引用)
  → Answer Guard（无引用/域外降级）
  →（action）Executor → Action Guard → awaiting_confirmation
  → 用户 confirm → Business 写 tickets + 审计
  → Memory.upsert
```
