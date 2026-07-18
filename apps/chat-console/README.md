# KA Chat Console（阶段 6）

Vite + React + TypeScript 对话控制台：对话、引用面板、Agent 轨迹、待确认行动。

## 启动

```powershell
# 终端 1：API（需 Postgres / Redis / 火山 Key）
cd E:\AI\zwl_ai\4-MCP服务-Agent集群
uv run uvicorn ka_api.main:app --reload --port 8000

# 终端 2：前端
cd apps\chat-console
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173  

开发代理：`/api/*` → `http://127.0.0.1:8000/*`  
也可用 `VITE_API_BASE=http://127.0.0.1:8000` 直连。

## 开发用户

入口页输入 User Id（写入请求头 `X-User-Id`）。API 需 `AUTH_PROVIDER=dev_header` 或默认 `none`（仍会带上头，无鉴权时忽略）。

## 三条主用户故事芯片

1. 纯问答：试用期年假  
2. 对比归纳：差旅 vs 报销  
3. 行动确认：起草上海出差申请 + 待办（须点「确认执行」才落库）

## 构建 / 冒烟

```powershell
npm run build
npm run smoke
```
