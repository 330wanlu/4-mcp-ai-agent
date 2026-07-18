import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  ApiError,
  confirmAction,
  createSession,
  getMe,
  getPendingActions,
  postMessage,
  rejectAction,
} from "./api";
import type {
  AgentTraceStep,
  ChatMessage,
  Citation,
  DevUser,
  PendingAction,
} from "./types";
import { STORY_CHIPS } from "./types";

type SideTab = "citations" | "trace" | "pending";

const USER_KEY = "ka_console_user";

function loadUser(): DevUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as DevUser) : null;
  } catch {
    return null;
  }
}

function statusTag(status?: string | null) {
  if (!status) return null;
  if (status === "awaiting_confirmation")
    return <span className="tag warn">待确认</span>;
  if (status === "blocked" || status === "degraded")
    return <span className="tag danger">{status}</span>;
  if (status === "completed" || status === "confirmed")
    return <span className="tag ok">{status}</span>;
  return <span className="tag">{status}</span>;
}

export default function App() {
  const [user, setUser] = useState<DevUser | null>(() => loadUser());
  const [gateName, setGateName] = useState("demo");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sideTab, setSideTab] = useState<SideTab>("citations");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [trace, setTrace] = useState<AgentTraceStep[]>([]);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [sessionStatus, setSessionStatus] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const canSend = useMemo(
    () => Boolean(user && input.trim() && !busy),
    [user, input, busy],
  );

  async function ensureSession(currentUser: DevUser) {
    if (sessionId) return sessionId;
    const created = await createSession(currentUser.userId, "KA Console");
    setSessionId(created.session_id);
    return created.session_id;
  }

  async function enterConsole(e: FormEvent) {
    e.preventDefault();
    const name = gateName.trim() || "demo";
    const next: DevUser = { userId: name, displayName: name };
    setError(null);
    setBusy(true);
    try {
      await getMe(next.userId);
      localStorage.setItem(USER_KEY, JSON.stringify(next));
      setUser(next);
      const created = await createSession(next.userId, "KA Console");
      setSessionId(created.session_id);
      setMessages([]);
      setCitations([]);
      setTrace([]);
      setPending(null);
      setSessionStatus("created");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `无法连接 API（${err.message}）。请确认 :8000 已启动，或检查 Vite 代理。`
          : "进入控制台失败",
      );
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem(USER_KEY);
    setUser(null);
    setSessionId(null);
    setMessages([]);
    setPending(null);
    setCitations([]);
    setTrace([]);
    setSessionStatus(null);
  }

  async function sendText(text: string) {
    if (!user || !text.trim() || busy) return;
    setError(null);
    setBusy(true);
    const content = text.trim();
    setInput("");
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content,
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const sid = await ensureSession(user);
      const resp = await postMessage(user.userId, sid, content);
      const assistant: ChatMessage = {
        id: resp.message_id || `a-${Date.now()}`,
        role: "assistant",
        content: resp.answer,
        citations: resp.citations,
        agent_trace: resp.agent_trace,
        status: resp.status,
        intent: resp.intent,
        note: resp.note,
        pending_action: resp.pending_action,
        guard: resp.guard,
      };
      setMessages((prev) => [...prev, assistant]);
      setCitations(resp.citations || []);
      setTrace(resp.agent_trace || []);
      setSessionStatus(resp.status || null);
      setPending(resp.pending_action || null);

      if (resp.status === "awaiting_confirmation" && !resp.pending_action) {
        const pendingResp = await getPendingActions(user.userId, sid);
        const first = pendingResp.pending_actions?.[0] || null;
        setPending(first);
      }
      if (resp.status === "awaiting_confirmation") setSideTab("pending");
      else if ((resp.citations || []).length) setSideTab("citations");
      else setSideTab("trace");
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "发送失败，请稍后重试";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "system",
          content: `错误：${msg}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!user || !sessionId || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await confirmAction(user.userId, sessionId);
      setPending(null);
      setSessionStatus("confirmed");
      setSideTab("trace");
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          role: "system",
          content: `已确认并落库。tickets=${JSON.stringify(result.tickets || result)}`,
          status: "confirmed",
        },
      ]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "确认失败");
    } finally {
      setBusy(false);
    }
  }

  async function onReject() {
    if (!user || !sessionId || busy) return;
    setBusy(true);
    setError(null);
    try {
      await rejectAction(user.userId, sessionId, "用户在 Chat Console 驳回");
      setPending(null);
      setSessionStatus("rejected");
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          role: "system",
          content: "已驳回待确认行动，未写入工单。",
          status: "rejected",
        },
      ]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "驳回失败");
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="gate">
        <form className="gate-panel" onSubmit={enterConsole}>
          <div className="brand-mark">KA Console</div>
          <h1>开发用户入口</h1>
          <p>
            阶段 6 占位登录：写入 <code>X-User-Id</code>，真实鉴权后续再挂。
          </p>
          <label htmlFor="dev-user">显示名 / User Id</label>
          <input
            id="dev-user"
            value={gateName}
            onChange={(e) => setGateName(e.target.value)}
            placeholder="demo"
            autoFocus
          />
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "连接中…" : "进入控制台"}
          </button>
          <p className="hint">默认请求代理到 http://127.0.0.1:8000</p>
          {error ? <p className="hint" style={{ color: "var(--danger)" }}>{error}</p> : null}
        </form>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">KA Console</div>
          <div className="brand-sub">
            Knowledge Action · 引用 / 轨迹 / 确认闸门
            {sessionId ? ` · ${sessionId.slice(0, 8)}` : ""}
            {sessionStatus ? ` · ${sessionStatus}` : ""}
          </div>
        </div>
        <div className="user-chip">
          <span>{user.displayName}</span>
          <button type="button" onClick={logout}>
            切换用户
          </button>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <main className="workspace">
        <section className="panel chat-panel">
          <div className="messages">
            {messages.length === 0 ? (
              <div className="empty">
                <h2>三条主用户故事</h2>
                <p>点下方芯片即可走通问答、对比与行动确认。</p>
                <div className="chips">
                  {STORY_CHIPS.map((chip) => (
                    <button
                      key={chip.id}
                      type="button"
                      className="chip"
                      disabled={busy}
                      onClick={() => void sendText(chip.text)}
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`bubble ${m.role === "user" ? "user" : "assistant"}`}
                >
                  {m.content}
                  <div className="meta">
                    {m.intent ? <span className="tag">{m.intent}</span> : null}
                    {statusTag(m.status)}
                    {m.citations?.length ? (
                      <span className="tag">{m.citations.length} 引用</span>
                    ) : null}
                    {m.agent_trace?.length ? (
                      <span className="tag">{m.agent_trace.length} 步轨迹</span>
                    ) : null}
                  </div>
                </div>
              ))
            )}
            {busy ? (
              <div className="bubble assistant">Agent 集群处理中…</div>
            ) : null}
            <div ref={bottomRef} />
          </div>

          <div className="composer">
            <div className="chips" style={{ justifyContent: "flex-start" }}>
              {STORY_CHIPS.map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  className="chip"
                  disabled={busy}
                  onClick={() => setInput(chip.text)}
                >
                  {chip.label}
                </button>
              ))}
            </div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入制度问题，或起草差旅/请假行动…"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void sendText(input);
                }
              }}
            />
            <div className="composer-row">
              <span className="status-text">
                Enter 发送 · Shift+Enter 换行 · 写操作必须确认
              </span>
              <button
                className="primary"
                type="button"
                disabled={!canSend}
                onClick={() => void sendText(input)}
              >
                发送
              </button>
            </div>
          </div>
        </section>

        <aside className="panel side-panel">
          <div className="side-tabs">
            <button
              type="button"
              className={sideTab === "citations" ? "active" : ""}
              onClick={() => setSideTab("citations")}
            >
              引用
            </button>
            <button
              type="button"
              className={sideTab === "trace" ? "active" : ""}
              onClick={() => setSideTab("trace")}
            >
              轨迹
            </button>
            <button
              type="button"
              className={sideTab === "pending" ? "active" : ""}
              onClick={() => setSideTab("pending")}
            >
              待确认
            </button>
          </div>
          <div className="side-body">
            {sideTab === "citations" ? (
              <div className="side-section">
                {citations.length === 0 ? (
                  <p style={{ color: "var(--muted)" }}>暂无引用</p>
                ) : (
                  citations.map((c, i) => (
                    <article className="cite-item" key={`${c.doc_id}-${i}`}>
                      <h4>
                        [{i + 1}] {c.filename || c.title || "未命名文档"}
                      </h4>
                      <p>
                        {c.section ? `章节：${c.section}` : "章节：—"}
                        {c.score != null ? ` · score=${c.score}` : ""}
                      </p>
                      {c.snippet ? <p style={{ marginTop: "0.45rem" }}>{c.snippet}</p> : null}
                    </article>
                  ))
                )}
              </div>
            ) : null}

            {sideTab === "trace" ? (
              <div className="side-section">
                {trace.length === 0 ? (
                  <p style={{ color: "var(--muted)" }}>暂无 Agent 轨迹</p>
                ) : (
                  trace.map((step, i) => (
                    <article className="trace-item" key={`${step.agent}-${i}`}>
                      <h4>
                        <span className="agent">{step.agent || "agent"}</span>
                        {" · "}
                        {step.action || "step"}
                      </h4>
                      <p>
                        <code style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap" }}>
                          {JSON.stringify(step.detail ?? {}, null, 0).slice(0, 280)}
                        </code>
                      </p>
                    </article>
                  ))
                )}
              </div>
            ) : null}

            {sideTab === "pending" ? (
              <div className="side-section">
                {!pending ? (
                  <p style={{ color: "var(--muted)" }}>
                    当前没有待确认行动。发起「行动确认」故事后会出现在这里。
                  </p>
                ) : (
                  <div className="pending-box">
                    <h3>{pending.title || "待确认行动"}</h3>
                    <p>
                      <strong>类型</strong>：{pending.action_type || "—"}
                    </p>
                    <p style={{ marginTop: "0.45rem" }}>
                      {pending.summary || "无摘要"}
                    </p>
                    <p style={{ marginTop: "0.45rem" }}>
                      tickets：{pending.tickets?.length ?? 0}（确认前不会落库）
                    </p>
                    <div className="pending-actions">
                      <button
                        className="primary"
                        type="button"
                        disabled={busy}
                        onClick={() => void onConfirm()}
                      >
                        确认执行
                      </button>
                      <button
                        className="danger"
                        type="button"
                        disabled={busy}
                        onClick={() => void onReject()}
                      >
                        驳回
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </aside>
      </main>
    </div>
  );
}
