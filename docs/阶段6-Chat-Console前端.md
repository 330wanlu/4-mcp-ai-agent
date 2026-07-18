# 阶段 6 回溯：Chat Console 前端

> 日期：2026-07-18  
> 对应方案：[`方案B-详细实现流程.md`](./方案B-详细实现流程.md) §阶段 6  
> 前置：阶段 0–5  
> 状态：**阶段 6 已全绿**；与阶段 0–6 联验通过

---

## 1. 目标与完成标准

| 完成标准 | 结果 |
|----------|------|
| 对话 + 引用面板 + Agent 轨迹 + 待确认行动 | ✅ |
| 只消费已有 API（消息响应补了 status/pending 字段） | ✅ |
| 开发用户占位登录（`X-User-Id`） | ✅ |
| UI 走通三条主用户故事 | ✅ 芯片 + API 联测 |
| 轨迹能看出多 Agent | ✅ 侧栏 Trace |

三条主用户故事：

1. **纯问答 + 引用**：试用期年假  
2. **对比/归纳**：差旅 vs 报销边界  
3. **问答后行动 + 确认**：起草上海出差申请（确认前不落库）

---

## 2. 实现流程

```text
1. 扩展 API PostMessage/SessionDetail：status / pending_action / guard
2. Vite + React + TS 脚手架（apps/chat-console）
3. 开发用户入口 → 建会话 → 发消息
4. 侧栏：引用 / Agent 轨迹 / 待确认（confirm/reject）
5. 故事芯片 + 代理 /api → :8000
6. npm build + smoke + tests/test_chat_console.py
7. 0–6 联验 → 本文档
```

### 关键代码位置

| 能力 | 路径 |
|------|------|
| 前端入口 | `apps/chat-console/src/App.tsx` |
| API 客户端 | `apps/chat-console/src/api.ts` |
| 故事芯片 | `apps/chat-console/src/types.ts` |
| 样式 | `apps/chat-console/src/styles.css` |
| API 响应扩展 | `apps/api/src/ka_api/schemas.py` / `routers/chat.py` |
| 契约测试 | `tests/test_chat_console.py` |
| UI 冒烟 | `apps/chat-console/scripts/smoke_ui_contract.mjs` |

### 界面结构

```text
[开发用户入口]
    ↓
[KA Console]
  ├─ 对话区：消息气泡 + 故事芯片 + 输入框
  └─ 侧栏 Tab
       ├─ 引用：filename / section / snippet
       ├─ 轨迹：memory → router → researcher → analyst → …
       └─ 待确认：confirm / reject（不绕过闸门）
```

---

## 3. 遇到的问题与处理

### 3.1 `npm create vite` 因目录非空取消

- **处理**：手写 Vite/React/TS 配置与源码（目录已有 README 占位）。

### 3.2 消息接口原先不返回 status / pending_action

- **处理**：向后兼容地扩展 `PostMessageResponse` / `SessionDetailResponse`，前端可直接渲染待确认面板。

### 3.3 鉴权默认 `none` 时入口用户名不生效

- **说明**：`AUTH_PROVIDER=none` 时用户恒为 `local-dev`；Chat Console 建议 `.env` 设 `AUTH_PROVIDER=dev_header`。

### 3.4 需要你帮忙的

1. **启动 API**：`uv run uvicorn ka_api.main:app --reload --port 8000`  
2. **启动前端**：`cd apps/chat-console && npm run dev` → http://127.0.0.1:5173  
3. 保持 Postgres / Redis Running；可选把 `AUTH_PROVIDER=dev_header`

---

## 4. 如何启动 / 复现自验证

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群

# 前端构建 + 契约冒烟
cd apps\chat-console
npm install
npm run build
npm run smoke
cd ..\..

# 阶段 6 测试（含三条故事 API 联调，会调豆包）
uv run pytest tests/test_chat_console.py -q

# 阶段 0–6 联验
uv run pytest tests/test_phase0_skeleton.py tests/test_knowledge_search.py tests/test_agent_qa_flow.py tests/test_api_chat.py tests/test_action_gate.py tests/test_guardrails.py tests/test_chat_console.py -q

uv run python scripts/check_local_deps.py
```

手动 UI：

```powershell
# 终端 A
uv run uvicorn ka_api.main:app --reload --port 8000
# 终端 B
cd apps\chat-console; npm run dev
```

---

## 5. 自验证结果（2026-07-18）

### 前端

| 检查项 | 结果 |
|--------|------|
| `npm run build` | ✅ |
| `npm run smoke` | ✅ `SMOKE_EXIT=0` |
| `test_chat_console.py` | ✅ **5 passed** |

### pytest / deps

| 检查项 | 结果 |
|--------|------|
| `pytest` 阶段 0–6 | ✅ **38 passed**（约 4m49s） |
| `check_local_deps.py` | ✅ postgres / vector / redis ok |

---

## 6. 阶段 0–6 联验结论

| 层级 | 状态 |
|------|------|
| 工程骨架 / 本机依赖 | ✅ 0 |
| PGVector + Knowledge MCP | ✅ 1 |
| 豆包 Agent 问答 | ✅ 2 |
| FastAPI Chat/审计 | ✅ 3 |
| Business + 审批闸门 | ✅ 4 |
| Memory + Guard + 评测 | ✅ 5 |
| Chat Console 前端 | ✅ 6 |

**当前项目主路径（到阶段 6）已跑通。**  
下一步：**阶段 7 — 本地收尾与演示文档**。

---

## 7. 需要你知晓

1. 写操作必须在 UI 点「确认执行」；前端未提供绕过路径。  
2. 联验慢是因为真实 LLM。  
3. 前端不替代后端测试；故事正确性以 API/pytest 为准。
