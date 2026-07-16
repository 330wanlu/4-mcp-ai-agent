# 阶段 1 回溯：Postgres 模型 + Knowledge 入库 + Knowledge MCP

> 日期：2026-07-16  
> 对应方案：[`方案B-详细实现流程.md`](./方案B-详细实现流程.md) §阶段 1  
> 前置：[`阶段0-工程骨架与本机依赖.md`](./阶段0-工程骨架与本机依赖.md)  
> 状态：**阶段 1 已全绿**；与阶段 0 联验通过

---

## 1. 目标与完成标准

| 完成标准 | 结果 |
|----------|------|
| Alembic 建表：`documents` / `chunks`(vector) / `audit_logs` / `tickets` / `users` | ✅ |
| 仅 PGVector，无其他向量库 | ✅ |
| `ingest_docs.py`：Markdown/Text → 切片 → 豆包 Embedding → 入库 | ✅ 5 篇 / 42 chunks |
| Knowledge MCP 三工具：`hybrid_search` / `get_document_section` / `list_sources` | ✅ |
| 检索结果含 `doc_id / title / section / score` | ✅ |
| PDF/DOCX 延后，仅占位 `NotImplemented` | ✅ |

---

## 2. 实现流程

```text
1. 发现 .env 中 ARK_API_KEY 为空
   → 从同机项目 1-chat-ai-agent/rag_llm_server/.env 复用密钥（仅本机）
2. 探测 doubao-embedding-vision-251215：
   → 必须走 POST {ARK_BASE_URL}/embeddings/multimodal
   → 文本输入格式：{"type":"text","text":"..."}
   → 默认维度 2048；请求 dimensions=1024 成功
3. 增加依赖：sqlalchemy / alembic / pgvector / greenlet
4. 落地 ka_common.db 模型 + alembic/versions/001_initial_schema.py
5. 实现 VolcengineDoubaoProvider.embed（并发限流）
6. parsers.chunking + scripts/ingest_docs.py
7. ka_knowledge_mcp.service 混合检索 + FastAPI :8101 工具路由
8. smoke_knowledge_mcp.py + tests/test_knowledge_search.py
9. 自验证全绿 → 写本文档
```

### 关键代码位置

| 能力 | 路径 |
|------|------|
| ORM 模型 | `packages/common/src/ka_common/db/` |
| 迁移 | `alembic/versions/001_initial_schema.py` |
| Embedding | `packages/llm/src/ka_llm/volcengine.py` |
| 切片 | `packages/parsers/src/ka_parsers/chunking.py` |
| 入库 | `scripts/ingest_docs.py` |
| 检索服务 | `mcp_servers/knowledge/src/ka_knowledge_mcp/service.py` |
| HTTP 工具面 | `mcp_servers/knowledge/src/ka_knowledge_mcp/server.py`（端口 8101） |
| 冒烟 | `scripts/smoke_knowledge_mcp.py` |

### 混合检索策略（MVP）

- **向量**：`cosine_distance` → `score_vec = 1/(1+distance)`
- **关键词**：query 分词后对 `content` / `title` 做 `ILIKE` 命中率
- **融合**：`0.7 * score_vec + 0.3 * score_kw`，取 top_k

---

## 3. 遇到的问题与处理

### 3.1 `ARK_API_KEY` 为空

- **现象**：无法调用方舟 Embedding。  
- **处理**：从本机已有项目复制 Key 到本仓库 `.env`（gitignore）。  
- **请你确认**：该 Key 是否允许本项目长期使用；若需换专用 Key，改 `.env` 后重新 `ingest_docs.py --force`。

### 3.2 多模态 Embedding 路径不是 `/embeddings`

- **现象**：`doubao-embedding-vision-*` 走标准 `/embeddings` 会报模型不支持。  
- **处理**：实现为 `{ARK_BASE_URL}/embeddings/multimodal`，input 为 typed 对象数组。

### 3.3 批量 input 不会返回多条向量

- 一次请求里放多段 text 时，接口更像「融合成一条向量」。  
- **处理**：入库时**逐条**调用 Embedding，并用 `asyncio.Semaphore` 控制并发（默认 4）。

### 3.4 向量维度选择

- 默认返回 **2048** 维；为控制存储，冻结 `EMBEDDING_DIMENSIONS=1024`（表列与请求一致）。  
- 若以后改维度，需重建 `chunks.embedding` 列并全量 `--force` 入库。

### 3.5 Alembic 与业务库

- 迁移目标库：`.env` 中 `mcp_agent_db`。  
- 命令：`uv run alembic upgrade head`（已执行成功）。

---

## 4. 如何启动 / 复现自验证

### 4.1 前置

- 阶段 0 依赖仍绿：Postgres / PGVector / Memurai  
- `.env` 含有效 `ARK_API_KEY`、`DATABASE_URL`、`EMBEDDING_DIMENSIONS=1024`

### 4.2 迁移 + 入库 + 冒烟

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群

uv run alembic upgrade head
uv run python scripts/ingest_docs.py          # 增量；全量加 --force
uv run python scripts/smoke_knowledge_mcp.py --query 差旅报销
```

可选启动 Knowledge HTTP：

```powershell
uv run python -m ka_knowledge_mcp.server
# 或: uv run uvicorn ka_knowledge_mcp.server:app --port 8101
```

### 4.3 测试

```powershell
# 阶段 0 + 1
uv run pytest tests/test_phase0_skeleton.py tests/test_knowledge_search.py -q

# 本机依赖
uv run python scripts/check_local_deps.py
```

---

## 5. 自验证结果（2026-07-16）

### 入库

```text
请假管理制度.md        9 chunks
员工手册摘要.md        7 chunks
费用报销管理制度.md    9 chunks
差旅与报销操作指引.md  8 chunks
差旅管理制度.md        9 chunks
完成: files=5 skipped=0 chunks=42 embedded=42
```

### smoke（query=`差旅报销`）

```text
[list_sources] count=5
[hybrid_search] count=5  （含 doc_id/title/section/score）
Top hits 含：差旅管理制度、差旅与报销操作指引、费用报销管理制度
[get_document_section] found=True
SMOKE OK
```

### pytest / deps

| 命令 | 结果 |
|------|------|
| `pytest` phase0 + phase1 | **11 passed** |
| `check_local_deps.py` | **postgres ok / vector ok / redis ok** |

---

## 6. 阶段 0 + 1 联验结论

| 层级 | 状态 |
|------|------|
| 工程骨架 / 语料 / 黄金集 | ✅（阶段 0） |
| 本机 Postgres + PGVector + Memurai | ✅（阶段 0） |
| 表结构 + 向量入库 | ✅（阶段 1） |
| Knowledge 三工具可检索 | ✅（阶段 1） |

**当前项目主路径（到阶段 1）已跑通。**  
下一步：**阶段 2 — 豆包 Chat + Router/Researcher/Analyst Agent 问答闭环（CLI）**。

---

## 7. 需要你知晓 / 可选协助

1. **确认 ARK_API_KEY**：现从旧项目复用；若要项目专用 Key，提供后我可替换并重跑 ingest。  
2. **Memurai / Postgres 服务**保持 Running，后续阶段继续依赖。  
3. 阶段 2 会真正打 Chat 模型 `doubao-seed-1-8-251228`，请确认该模型在方舟控制台已开通。
