# 阶段 4 回溯：Business MCP + Executor + 审批闸门

> 日期：2026-07-17  
> 对应方案：`[方案B-详细实现流程.md](./方案B-详细实现流程.md)` §阶段 4
> 前置：阶段 0 / 1 / 2 / 3  
> 状态：**阶段 4 已全绿**；与阶段 0–3 联验通过

---

## 1. 目标与完成标准


| 完成标准                                         | 结果                         |
| -------------------------------------------- | -------------------------- |
| Business MCP → Postgres `tickets`            | ✅ `create/update/get/list` |
| Executor 起草 `action_plan`（确认前不落库）            | ✅                          |
| Critic/Guard 冲突拦截                            | ✅ 含 ACT-05 无出差单报销          |
| Redis `awaiting_confirmation`                | ✅                          |
| API：`pending-actions` / `confirm` / `reject` | ✅                          |
| 黄金行动约 3/5 正确 `action_type`                   | ✅（单测断言 ≥3）                 |
| 未 confirm 无工单；confirm 后有工单 + 审计              | ✅                          |


---

## 2. 实现流程

```text
1. Business MCP service + HTTP :8103（tickets CRUD）
2. BusinessMcpClient（local/http）
3. Executor：LLM + 启发式 → action_plan（不写库）
4. Guard：refuse / 无出差单报销拦截
5. confirmation：confirm→create_ticket+audit；reject→清空 pending
6. 扩展 pipeline：intent=action → Executor → Guard
7. API 路由 pending/confirm/reject；demo_cli --action
8. tests/test_action_gate.py → 文档
```

### 关键代码位置


| 能力            | 路径                                                         |
| ------------- | ---------------------------------------------------------- |
| Business 服务   | `mcp_servers/business/src/ka_business_mcp/service.py`      |
| Business HTTP | `mcp_servers/business/src/ka_business_mcp/server.py`       |
| 客户端           | `packages/mcp_clients/src/ka_mcp_clients/business.py`      |
| Executor      | `apps/orchestrator/src/ka_orchestrator/agents/executor.py` |
| Guard         | `apps/orchestrator/src/ka_orchestrator/agents/guard.py`    |
| 确认闸门          | `apps/orchestrator/src/ka_orchestrator/confirmation.py`    |
| 流水线           | `apps/orchestrator/src/ka_orchestrator/pipeline.py`        |
| API 行动路由      | `apps/api/src/ka_api/routers/actions.py`                   |
| Demo          | `scripts/demo_cli.py --action`                             |
| 测试            | `tests/test_action_gate.py`                                |


### 行动闭环

```
用户（起草、创建待办等操作）
  → 路由分发器（意图=操作行为）→ 检索处理器 → 分析处理器
  → 执行器（执行方案）→ 权限校验器
       ├─ 拦截分支：状态=已拦截，无待处理任务、无业务工单
       └─ 放行分支：状态=待确认，Redis存储待执行操作队列
            → 调用确认接口 → 业务层MCP生成工单 + 记录操作执行审计日志
            → 调用驳回接口 → 清空待执行队列 + 记录操作驳回审计日志（不生成工单）
```

```text
User（起草/创建待办等）
  → Router(intent=action) → Researcher → Analyst
  → Executor(action_plan) → Guard
       ├─ blocked：status=blocked，无 pending，无 tickets
       └─ allowed：status=awaiting_confirmation，Redis pending_action
            → POST confirm → Business MCP 写 tickets + audit action_execute
            → POST reject  → 清空 pending + audit action_reject（无工单）
```

### 支持的 action_type

- `create_travel_draft_and_todo`
- `create_leave_draft_and_todo`
- `create_ticket`
- `create_document_draft_and_todo`
- `refuse_or_require_travel_order`（Guard 拦截，不进确认）

---

## 3. 遇到的问题与处理

### 3.1 Router 可能把「起草/创建待办」判成 qa

- **处理**：Router 增加启发式纠偏（起草/创建待办/开单等关键词 → `action`）。

### 3.2 Executor 模型偶发 action_type 不准

- **处理**：启发式优先覆盖「无出差单报机票」等拦截场景；缺 tickets 时按类型补默认草稿。

### 3.3 确认前绝不能落库

- **处理**：Executor 只写 Redis `pending_action`；仅 `confirm_pending_action` 调 Business `create_ticket`。

### 3.4 上次全量联验命令被中断

- **说明**：非逻辑卡死；`test_action_gate` 已先绿，中断后继续补跑 `demo_cli --action` 与 0–4 联验。

### 3.5 需要你帮忙的

**目前没有。** 保持 Postgres / Memurai Running 即可。

---

## 4. 如何启动 / 复现自验证

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群

# 黄金行动 + 闸门（确认前无单 / 确认后有单 / 拦截无单）
uv run python scripts/demo_cli.py --action

# 阶段 4 测试
uv run pytest tests/test_action_gate.py -q

# 阶段 0–4 联验
uv run pytest tests/test_phase0_skeleton.py tests/test_knowledge_search.py tests/test_agent_qa_flow.py tests/test_api_chat.py tests/test_action_gate.py -q

uv run python scripts/check_local_deps.py
```

API 示例：

```powershell
uv run uvicorn ka_api.main:app --reload --port 8000
# POST /chat/sessions → POST .../messages（行动话术）
# GET  .../pending-actions → POST .../confirm 或 .../reject
```

---

## 5. 自验证结果（2026-07-17）

### demo_cli --action

```text
=== action_type hit: 5/5 (need >=3) ===
=== gate checks ok: 5/5 ===
DEMO_EXIT=0
```


| ACT    | action_type                      | 闸门                    |
| ------ | -------------------------------- | --------------------- |
| ACT-01 | ✅ create_travel_draft_and_todo   | ✅ confirm → 2 tickets |
| ACT-02 | ✅ create_leave_draft_and_todo    | ✅ confirm → 2 tickets |
| ACT-03 | ✅ create_ticket                  | ✅ confirm → 1 ticket  |
| ACT-04 | ✅ create_document_draft_and_todo | ✅ confirm → 2 tickets |
| ACT-05 | ✅ refuse_or_require_travel_order | ✅ blocked，无 tickets   |


### pytest / deps


| 检查项                   | 结果                                     |
| --------------------- | -------------------------------------- |
| `pytest` 阶段 0+1+2+3+4 | **26 passed**                          |
| `check_local_deps.py` | **postgres ok / vector ok / redis ok** |


---

## 6. 阶段 0–4 联验结论


| 层级                       | 状态  |
| ------------------------ | --- |
| 工程骨架 / 本机依赖              | ✅ 0 |
| PGVector + Knowledge MCP | ✅ 1 |
| 豆包 Agent 问答              | ✅ 2 |
| FastAPI Chat/审计          | ✅ 3 |
| Business + 审批闸门          | ✅ 4 |


**当前项目主路径（到阶段 4）已跑通。**  
下一步：**阶段 5 — Memory + Guard 增强 + 评测**。

---

## 7. 需要你知晓 / 可选协助

1. **无需额外操作**；保持 Postgres / Memurai Running。
2. 写操作务必走 confirm；前端阶段 6 不得绕过闸门。
3. 可选：单独启动 Business MCP `uv run python -m ka_business_mcp.server`（默认 local 进程内即可）。

