# 阶段 5 回溯：Memory + Guard 增强 + 评测

> 日期：2026-07-18  
> 对应方案：[`方案B-详细实现流程.md`](./方案B-详细实现流程.md) §阶段 5  
> 前置：阶段 0 / 1 / 2 / 3 / 4  
> 状态：**阶段 5 已全绿**；与阶段 0–5 联验通过

---

## 1. 目标与完成标准

| 完成标准 | 结果 |
|----------|------|
| Memory MCP：会话摘要 + 用户偏好落 Postgres | ✅ |
| Guard：无引用 / 域外 → 降级拒答 | ✅ |
| Guard：行动与制度冲突拦截 | ✅（含 ACT-05） |
| `run_eval.py` + 评测报告 | ✅ 见 [`eval-report.md`](./eval-report.md) |
| `tests/test_guardrails.py` | ✅ 7 passed |
| 阶段 0–5 联验 | ✅ |

---

## 2. 实现流程

```text
1. Alembic 002：session_summaries + user_preferences
2. Memory MCP service / HTTP :8102 / MemoryMcpClient
3. Guard 增强：
   - run_answer_guard：无命中 / 无引用 / 域外闲聊 → degraded
   - run_guard：行动冲突 + 空 tickets 拦截
4. pipeline：Memory.load → Router → Researcher → Analyst
   → Answer Guard →（action）Executor → Action Guard → Memory.upsert
5. scripts/run_eval.py + docs/eval-report.md
6. tests/test_guardrails.py；修正旧 phase/trace 断言
7. 自验证 0–5 → 本文档
```

### 关键代码位置

| 能力 | 路径 |
|------|------|
| Memory 模型 | `packages/common/src/ka_common/db/models.py` |
| 迁移 | `alembic/versions/002_memory_tables.py` |
| Memory 服务 | `mcp_servers/memory/src/ka_memory_mcp/service.py` |
| Memory HTTP | `mcp_servers/memory/src/ka_memory_mcp/server.py` |
| 客户端 | `packages/mcp_clients/src/ka_mcp_clients/memory.py` |
| Guard | `apps/orchestrator/src/ka_orchestrator/agents/guard.py` |
| 流水线 | `apps/orchestrator/src/ka_orchestrator/pipeline.py` |
| Graph | `apps/orchestrator/src/ka_orchestrator/graph.py` |
| 评测 | `scripts/run_eval.py` |
| 测试 | `tests/test_guardrails.py` |

### 流水线（阶段 5）

```text
User
  → Memory.load（会话摘要 + 用户偏好）
  → Router → Researcher(Knowledge) → Analyst(+memory_context)
  → Answer Guard
       ├─ degraded：无引用 / 域外 → 拒答关键结论
       └─ pass：继续
  →（intent=action）Executor → Action Guard
       ├─ blocked：无 pending / 无 tickets
       └─ awaiting_confirmation → confirm 后 Business 落库
  → Memory.upsert（摘要 + last_domain 偏好）
  → audit_logs
```

### Memory 工具

- `get_session_summary` / `upsert_session_summary`
- `get_user_preference` / `upsert_user_preference`

---

## 3. 遇到的问题与处理

### 3.1 域外问题仍被向量近邻命中

- **处理**：Answer Guard 增加域外关键词硬规则；相关度过低也降级。

### 3.2 `enable_actions=False` 时跳过 Answer Guard

- **现象**：Router 偶发把闲聊判成 `action`，关闭行动时既不跑 Executor 也不跑质检。
- **处理**：`intent != action` **或** `not enable_actions` 时都跑 Answer Guard。

### 3.3 旧测试断言仍写 phase=4 / 精确 trace

- **处理**：改为 phase=5，并断言 trace「包含」memory/router/…/critic_guard。

### 3.4 全量联验慢

- **原因**：真实调用火山豆包；黄金 10+5 条约 4–5 分钟属正常，不是卡死。

### 3.5 需要你帮忙的

**目前没有。** 保持 Postgres / Redis Running，`.env` 火山 Key 有效即可。

---

## 4. 如何复现自验证

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群

uv run alembic upgrade head

# 阶段 5
uv run pytest tests/test_guardrails.py -q
uv run python scripts/run_eval.py

# 阶段 0–5 联验
uv run pytest tests/test_phase0_skeleton.py tests/test_knowledge_search.py tests/test_agent_qa_flow.py tests/test_api_chat.py tests/test_action_gate.py tests/test_guardrails.py -q

uv run python scripts/check_local_deps.py
```

---

## 5. 自验证结果（2026-07-18）

### run_eval.py

```text
QA citation: 10/10
Actions type/gate: 5/5
Guardrails: 4/4
EVAL_EXIT=0
```

详见 [`eval-report.md`](./eval-report.md)。

### pytest / deps

| 检查项 | 结果 |
|--------|------|
| `test_guardrails.py` | **7 passed** |
| `pytest` 阶段 0+1+2+3+4+5 | **33 passed**（修 phase 断言后；首轮 32 passed + 1 旧断言失败已修） |
| `check_local_deps.py` | **postgres ok / vector ok / redis ok** |

---

## 6. 阶段 0–5 联验结论

| 层级 | 状态 |
|------|------|
| 工程骨架 / 本机依赖 | ✅ 0 |
| PGVector + Knowledge MCP | ✅ 1 |
| 豆包 Agent 问答 | ✅ 2 |
| FastAPI Chat/审计 | ✅ 3 |
| Business + 审批闸门 | ✅ 4 |
| Memory + Guard + 评测 | ✅ 5 |

**当前项目主路径（到阶段 5）已跑通。**  
下一步：**阶段 6 — 前端 Chat Console**。

---

## 7. 需要你知晓

1. 写操作仍必须走 confirm；前端不得绕过闸门。
2. 评测报告：`docs/eval-report.md`、`data/eval_reports/latest.*`。
3. 联验慢是因为真实 LLM，不是死锁。
