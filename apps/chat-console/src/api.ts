import type {
  AgentTraceStep,
  Citation,
  PendingAction,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code = "API_ERROR", status = 500) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(
  path: string,
  userId: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("X-User-Id", userId);
  headers.set("X-User-Roles", "employee");

  const resp = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const text = await resp.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { message: text };
  }

  if (!resp.ok) {
    const body = data as { message?: string; error?: string; code?: string };
    throw new ApiError(
      body?.message || body?.error || `HTTP ${resp.status}`,
      body?.code || "HTTP_ERROR",
      resp.status,
    );
  }
  return data as T;
}

export type MeResponse = {
  user_id: string;
  display_name: string;
  roles: string[];
};

export type CreateSessionResponse = {
  session_id: string;
  user_id: string;
  status: string;
  title?: string | null;
};

export type PostMessageResponse = {
  session_id: string;
  message_id: string;
  intent?: string | null;
  answer: string;
  citations: Citation[];
  agent_trace: AgentTraceStep[];
  note?: string | null;
  status?: string | null;
  pending_action?: PendingAction | null;
  guard?: Record<string, unknown> | null;
};

export type SessionDetail = {
  found: boolean;
  session_id: string;
  status?: string | null;
  messages?: Array<{
    id: string;
    role: string;
    content: string;
    citations?: Citation[];
    agent_trace?: AgentTraceStep[];
  }>;
  citations?: Citation[];
  agent_trace?: AgentTraceStep[];
  pending_action?: PendingAction | null;
  note?: string | null;
  guard?: Record<string, unknown> | null;
};

export async function getMe(userId: string) {
  return request<MeResponse>("/me", userId);
}

export async function createSession(userId: string, title?: string) {
  return request<CreateSessionResponse>("/chat/sessions", userId, {
    method: "POST",
    body: JSON.stringify({ title: title || "KA Chat" }),
  });
}

export async function postMessage(
  userId: string,
  sessionId: string,
  content: string,
) {
  return request<PostMessageResponse>(
    `/chat/sessions/${sessionId}/messages`,
    userId,
    {
      method: "POST",
      body: JSON.stringify({ content, top_k: 5 }),
    },
  );
}

export async function getSession(userId: string, sessionId: string) {
  return request<SessionDetail>(`/chat/sessions/${sessionId}`, userId);
}

export async function getPendingActions(userId: string, sessionId: string) {
  return request<{
    session_id: string;
    pending_actions: PendingAction[];
  }>(`/chat/sessions/${sessionId}/pending-actions`, userId);
}

export async function confirmAction(userId: string, sessionId: string) {
  return request<Record<string, unknown>>(
    `/chat/sessions/${sessionId}/confirm`,
    userId,
    { method: "POST", body: "{}" },
  );
}

export async function rejectAction(
  userId: string,
  sessionId: string,
  reason?: string,
) {
  return request<Record<string, unknown>>(
    `/chat/sessions/${sessionId}/reject`,
    userId,
    {
      method: "POST",
      body: JSON.stringify({ reason: reason || "用户驳回" }),
    },
  );
}
