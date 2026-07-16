# 阶段 2 回溯：豆包 LLM + 最小 Agent Graph（问答闭环）

> 日期：2026-07-17  
> 对应方案：[`方案B-详细实现流程.md`](./方案B-详细实现流程.md) §阶段 2  
> 前置：[`阶段0-工程骨架与本机依赖.md`](./阶段0-工程骨架与本机依赖.md)、[`阶段1-知识入库与Knowledge-MCP.md`](./阶段1-知识入库与Knowledge-MCP.md)  
> 状态：**阶段 2 已全绿**；与阶段 0、1 联验通过

---

## 1. 目标与完成标准

| 完成标准 | 结果 |
|----------|------|
| `VolcengineDoubaoProvider.chat()` → `doubao-seed-1-8-251228` | ✅ |
| `embed()` 仍走 multimodal（阶段 1） | ✅ |
| 三 Agent：Router / Researcher / Analyst（暂无 Executor） | ✅ |
| Orchestrator + Redis 任务状态 `session:*` | ✅ |
| 问答结束写 `audit_logs` | ✅ |
| `demo_cli.py` 打印答案 + citations + agent_trace | ✅ |
| 黄金问答约 7/10 有合理引用 | ✅ **10/10** |
| Provider 抽象在，换模型名主要改配置 | ✅ `get_llm_provider()` + `.env` |

---

## 2. 实现流程

```text
1. 探测方舟 Chat：POST {ARK_BASE_URL}/chat/completions → HTTP 200
2. 实现 VolcengineDoubaoProvider.chat（支持 thinking=disabled 降延迟）
3. KnowledgeMcpClient（默认 local 进程内调 hybrid_search；可选 HTTP）
4. Orchestrator 流水线：
   Router（意图+检索改写）→ Researcher（Knowledge）→ Analyst（带引用答案）
5. Redis SessionStore：session:{id} JSON（current_node / status / trace）
6. Postgres audit_logs：agent_router / agent_researcher / qa_complete
7. scripts/demo_cli.py + tests/test_agent_qa_flow.py
8. 自验证：黄金 10/10 引用命中；pytest 15 passed；deps 全绿
9. 写本文档
```

### 关键代码位置

| 能力 | 路径 |
|------|------|
| Chat Provider | `packages/llm/src/ka_llm/volcengine.py` |
| Provider 工厂 | `packages/llm/src/ka_llm/factory.py` |
| Knowledge 客户端 | `packages/mcp_clients/src/ka_mcp_clients/knowledge.py` |
| Redis 会话 | `apps/orchestrator/src/ka_orchestrator/redis_state.py` |
| 审计 | `apps/orchestrator/src/ka_orchestrator/audit.py` |
| Router / Researcher / Analyst | `apps/orchestrator/src/ka_orchestrator/agents/` |
| 问答流水线 | `apps/orchestrator/src/ka_orchestrator/pipeline.py` |
| HTTP 入口 | `apps/orchestrator/src/ka_orchestrator/main.py`（`POST /qa`） |
| Demo CLI | `scripts/demo_cli.py` |
| 测试 | `tests/test_agent_qa_flow.py` |

### 问答闭环（阶段 2）

```text
User Question
  → Router（豆包 Chat，JSON：intent + search_query）
  → Researcher（Knowledge hybrid_search，top_k=5）
  → Analyst（豆包 Chat，基于资料生成答案；citations = 检索命中）
  → Redis session:* 状态 completed
  → Postgres audit_logs
```

- `intent=action` 时仅标注 note，**不写工单**（阶段 4 Executor）。
- citations 来自检索结果（含 `filename`），避免模型编造文档名。

---

## 3. 遇到的问题与处理

### 3.1 Chat 模型含 reasoning，延迟偏高

- **现象**：`doubao-seed-1-8-251228` 响应里有 `reasoning_content`，单次可偏慢。  
- **处理**：请求带 `thinking: {type: disabled}`；若不支持则自动回退去掉该字段。  
- **结果**：单题闭环约 10–15s，可接受。

### 3.2 `SessionStore.update` 参数冲突

- **现象**：`TypeError: got multiple values for argument 'session_id'`。  
- **原因**：`update(session_id, session_id=...)` 重复传参。  
- **处理**：字段里不再传 `session_id`，由 store 自行写入。

### 3.3 审计测试 `DetachedInstanceError`

- **现象**：Session 关闭后读 `AuditLog.event_type` 报错。  
- **处理**：在 `session_scope` 内先取出 `types` 集合再断言。

### 3.4 Windows 控制台中文乱码

- **现象**：PowerShell/GBK 下 `demo_cli` 打印中文乱码。  
- **说明**：数据本身是 UTF-8（Redis/Postgres/返回 JSON 正常）；CLI 已做 `_safe_print` 兜底，不影响验收。

### 3.5 未阻塞项（无需你操作）

- Chat / Embedding Key 复用阶段 1 的 `ARK_API_KEY`，模型名已在方舟可用。  
- Memurai / Postgres 保持 Running 即可。

---

## 4. 如何启动 / 复现自验证

### 4.1 前置

- 阶段 0：Postgres + PGVector + Memurai 绿  
- 阶段 1：语料已入库（≥5 篇）、Knowledge 可检索  
- `.env` 含有效 `ARK_API_KEY`、`LLM_MODEL=doubao-seed-1-8-251228`

### 4.2 Demo CLI

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群

# 单题
uv run python scripts/demo_cli.py --question "试用期员工年假怎么算？能不能请？"

# 黄金集 10 条（期望 citation ≥7/10）
uv run python scripts/demo_cli.py --golden --limit 10
```

可选启动 Orchestrator HTTP：

```powershell
uv run uvicorn ka_orchestrator.main:app --reload --port 8001
# POST http://127.0.0.1:8001/qa  {"question":"..."}
# GET  http://127.0.0.1:8001/sessions/{session_id}
```

### 4.3 测试与依赖

```powershell
uv run pytest tests/test_phase0_skeleton.py tests/test_knowledge_search.py tests/test_agent_qa_flow.py -q
uv run python scripts/check_local_deps.py
```

---

## 5. 自验证结果（2026-07-17）

### Demo 黄金集

```text
=== golden citation hit: 10/10 ===
```

| QA | 引用命中 | 说明 |
|----|----------|------|
| QA-01～QA-10 | ✅ 全部命中 | 引用 filename / title 与 `source_docs` 对齐 |

### pytest / deps / 数据

| 检查项 | 结果 |
|--------|------|
| `pytest` phase0 + phase1 + phase2 | **15 passed** |
| `check_local_deps.py` | **postgres ok / vector ok / redis ok** |
| Redis `session:*` | 可见（联验时约 30+ keys） |
| Postgres `audit_logs` | 有 `agent_router` / `agent_researcher` / `qa_complete` |

### 单题样例（试用期年假）

- intent: `qa`  
- citations 含：`请假管理制度.md`、`差旅与报销操作指引.md` 等  
- agent_trace：`router → researcher → analyst`

---

## 6. 阶段 0 + 1 + 2 联验结论

| 层级 | 状态 |
|------|------|
| 工程骨架 / 语料 / 黄金集 / 本机依赖 | ✅ 阶段 0 |
| PGVector 入库 + Knowledge 三工具 | ✅ 阶段 1 |
| 豆包 Chat + Agent 问答闭环 + Redis + 审计 | ✅ 阶段 2 |

**当前项目主路径（到阶段 2）已跑通。**  
下一步：**阶段 3 — FastAPI 暴露 Chat/审计 API（鉴权可后置）**。

---

## 7. 需要你知晓 / 可选协助

1. **无需额外操作**：Chat 模型已验证可用；本机 Postgres / Memurai 保持 Running。  
2. **可选**：若要换项目专用 `ARK_API_KEY` 或改 `LLM_MODEL`，改 `.env` 后重跑 `demo_cli.py --golden` 即可。  
3. **阶段 3 起**会把本流水线挂到 `apps/api` HTTP；前端仍最后做。
