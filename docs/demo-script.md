# 演示脚本（约 3–5 分钟）

适用：本地已按 [`README.md`](../README.md) 启动 API + Chat Console，或只用 CLI。

## 准备

```powershell
cd E:\AI\zwl_ai\4-MCP服务-Agent集群
uv run python scripts/check_local_deps.py
# 一键：powershell -File scripts\start_local.ps1
# 或分步：scripts\dev_api.ps1  +  scripts\dev_chat_console.ps1
```

- UI：http://127.0.0.1:5173  
- API 文档：http://127.0.0.1:8000/docs  
- 建议 `.env`：`AUTH_PROVIDER=dev_header`

---

## 路径 A：Chat Console（推荐给观众看）

### 1. 进入（15 秒）

入口输入 `demo` → **进入控制台**。点出品牌 **KA Console** 与三栏结构。

### 2. 纯问答 + 引用（约 1 分钟）

点芯片 **纯问答**（试用期年假）。

展示：

- 左侧答案含制度要点  
- 右侧 **引用**：文档名 / 章节 / snippet  
- 右侧 **轨迹**：`memory → router → researcher → analyst → critic_guard`

口述：不是单次 Chat，是可追踪的多 Agent + 可核对出处。

### 3. 对比归纳（约 1 分钟）

点 **对比归纳**（差旅 vs 报销 / 请客户吃饭科目）。

展示：多文档引用、跨制度结论。

### 4. 行动 + 确认闸门（约 1.5 分钟）

点 **行动确认**（起草上海出差申请 + 待办）。

展示：

1. 状态变为待确认；侧栏 **待确认** 出现行动摘要  
2. 强调：**确认前不会写 tickets**  
3. 点 **确认执行** → 落库；或点 **驳回** → 无工单  

可选加戏：再问「没有出差申请能不能报销机票」→ Guard **拦截**（`blocked`）。

### 5. 收尾（30 秒）

打开 [`eval-report.md`](./eval-report.md) 或说：`uv run python scripts/run_eval.py` 有黄金集评测（引用命中 / 行动闸门 / Guardrails），不是纯 Demo。

---

## 路径 B：无 UI（CLI，适合验收）

```powershell
# 问答
uv run python scripts/demo_cli.py --question "试用期员工年假怎么算？"

# 黄金问答（约 7/10+ 引用）
uv run python scripts/demo_cli.py --golden --limit 10

# 行动闸门（确认前无单 / 确认后有单 / ACT-05 拦截）
uv run python scripts/demo_cli.py --action
```

计时可用：

```powershell
powershell -File scripts\smoke_phase7.ps1 -SkipPytest
```

---

## 演示禁忌

- 不要跳过确认直接暗示「已创建工单」  
- 不要在观众面前改 `.env` 密钥  
- 网络/豆包慢时先说明「正在调方舟，等几秒」
