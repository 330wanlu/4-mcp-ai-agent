# 阶段 3 回溯：FastAPI Chat / 审计 API（鉴权可后置）

> 日期：2026-07-17  
> 对应方案：[`方案B-详细实现流程.md`](./方案B-详细实现流程.md) §阶段 3  
> 前置：阶段 0 / 1 / 2  
> 状态：**阶段 3 已全绿**；与阶段 0–2 联验通过

---

## 1. 目标与完成标准

| 完成标准 | 结果 |
|----------|------|
| `POST /chat/sessions` | ✅ |
| `POST /chat/sessions/{id}/messages` → 带回引用回复 | ✅ |
| `GET /chat/sessions/{id}`（含 `agent_trace` / `citations`） | ✅ |
| `GET /audit/events` | ✅ |
| `GET /debug/sessions/{id}` | ✅ |
| Auth：`NoAuthProvider` / `DevHeaderAuthProvider` + `Depends(get_current_user)` | ✅ |
| 调 Orchestrator（`local` 同进程 / `http` :8001） | ✅ |
| CORS、统一错误码、`/docs` | ✅ |
| pytest 建会话 → 提问 → 带回引用 | ✅ |

---

## 2. 实现流程

```text
1. Settings 增加 ORCHESTRATOR_MODE / DEBUG_ENDPOINTS
2. ka_api.errors：ApiError + 统一 {"error":{code,message}}
3. OrchestratorClient：
   - local：进程内 run_qa_pipeline（pytest / 默认本机）
   - http：POST {ORCHESTRATOR_URL}/qa（多进程推荐）
4. 路由：chat / audit / debug；CORS；Depends(get_current_user)
5. tests/test_api_chat.py：主路径 + 404 + Auth 切换 + OpenAPI
6. 自验证 0–3 全绿 → 写本文档
```

### 关键代码位置

| 能力 | 路径 |
|------|------|
| API 入口 | `apps/api/src/ka_api/main.py` |
| 依赖注入 / Auth | `apps/api/src/ka_api/deps.py` |
| Orchestrator 客户端 | `apps/api/src/ka_api/orchestrator_client.py` |
| Chat 路由 | `apps/api/src/ka_api/routers/chat.py` |
| 审计 | `apps/api/src/ka_api/routers/audit.py` |
| Debug | `apps/api/src/ka_api/routers/debug.py` |
| 错误码 | `apps/api/src/ka_api/errors.py` |
| 测试 | `tests/test_api_chat.py` |

### HTTP 主路径

```text
POST /chat/sessions
  → Redis session:{id} status=created

POST /chat/sessions/{id}/messages  {"content":"..."}
  → Orchestrator QA（Router→Researcher→Analyst）
  → 返回 answer + citations + agent_trace
  → 写 audit_logs；更新 Redis

GET /chat/sessions/{id}
  → answer / citations / agent_trace / messages

GET /audit/events?session_id=...
GET /debug/sessions/{id}
```

### 鉴权扩展点

- `AUTH_PROVIDER=none` → 固定 `local-dev`
- `AUTH_PROVIDER=dev_header` → 读 `X-User-Id`
- 路由一律 `Depends(get_current_user)`；换 Provider 不改路由体

---

## 3. 遇到的问题与处理

### 3.1 pytest 不宜强依赖已启动的 :8001

- **现象**：若默认只走 HTTP，CI/本地单测需另启 Orchestrator。  
- **处理**：`ORCHESTRATOR_MODE=local|http`；默认与 pytest 用 `local`；多进程时改 `http` 并启动 `:8001`。

### 3.2 Settings `lru_cache` 与测试切换 Auth

- **现象**：改 `AUTH_PROVIDER` 后仍读到旧配置。  
- **处理**：测试里 `get_settings.cache_clear()`。

### 3.3 全局 Exception handler 会干扰校验错误

- **处理**：只注册 `ApiError` 处理器，保留 FastAPI 默认 422 / HTTPException。

### 3.4 未阻塞项（无需你操作）

- 本机 Postgres / Memurai / 方舟 Key 沿用阶段 0–2，本次未新增外部依赖。

---

## 4. 如何启动 / 复现自验证

### 4.1 前置

- 阶段 0–2 已绿；语料已入库；`.env` 含 `ARK_API_KEY`  
- 建议：`ORCHESTRATOR_MODE=local`（单测/本机一体）

### 4.2 仅 API（local 模式，不需另开 orchestrator）

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群
uv run uvicorn ka_api.main:app --reload --port 8000
# 浏览器打开 http://127.0.0.1:8000/docs
```

### 4.3 多进程 HTTP 模式（可选）

```powershell
# .env: ORCHESTRATOR_MODE=http
uv run uvicorn ka_orchestrator.main:app --reload --port 8001
uv run uvicorn ka_api.main:app --reload --port 8000
```

### 4.4 测试

```powershell
uv run pytest tests/test_api_chat.py -q
# 阶段 0–3 联验
uv run pytest tests/test_phase0_skeleton.py tests/test_knowledge_search.py tests/test_agent_qa_flow.py tests/test_api_chat.py -q
uv run python scripts/check_local_deps.py
```

### 4.5 手工 curl 示例

```powershell
# 建会话
curl -s -X POST http://127.0.0.1:8000/chat/sessions -H "Content-Type: application/json" -d "{\"title\":\"demo\"}"

# 发消息（替换 SESSION_ID）
curl -s -X POST http://127.0.0.1:8000/chat/sessions/SESSION_ID/messages -H "Content-Type: application/json" -d "{\"content\":\"试用期员工年假怎么算？\"}"
```

---

## 5. 自验证结果（2026-07-17）

| 检查项 | 结果 |
|--------|------|
| `pytest` 阶段 0+1+2+3 | **20 passed** |
| `test_api_chat`：建会话→提问→引用→debug→audit | ✅ |
| Auth `dev_header` 切换 | ✅ `X-User-Id: alice` |
| `/docs` + OpenAPI 路径齐全 | ✅ |
| `check_local_deps`（联验时） | postgres / vector / redis ok |

---

## 6. 阶段 0–3 联验结论

| 层级 | 状态 |
|------|------|
| 工程骨架 / 本机依赖 / 语料黄金集 | ✅ 阶段 0 |
| PGVector 入库 + Knowledge MCP | ✅ 阶段 1 |
| 豆包 Agent 问答闭环 + Redis + 审计 | ✅ 阶段 2 |
| FastAPI Chat/审计/Debug + Auth 挂载点 | ✅ 阶段 3 |

**当前项目主路径（到阶段 3）已跑通。**  
下一步：**阶段 4 — Business MCP + Executor + 审批闸门**。

---

## 7. 需要你知晓 / 可选协助

1. **无需额外操作**；保持 Postgres / Memurai Running 即可。  
2. **可选**：若要用独立 Orchestrator 进程，设 `ORCHESTRATOR_MODE=http` 并启动 `:8001`。  
3. **可选**：试 `AUTH_PROVIDER=dev_header`，请求头带 `X-User-Id`。  
4. 前端仍在阶段 6；现在可用 `/docs` 或 pytest/curl 验收。
