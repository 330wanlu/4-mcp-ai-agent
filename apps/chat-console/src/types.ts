export type Citation = {
  doc_id?: string;
  title?: string;
  filename?: string;
  section?: string | null;
  score?: number | null;
  snippet?: string | null;
  source_path?: string;
};

export type AgentTraceStep = {
  agent?: string;
  action?: string;
  detail?: Record<string, unknown>;
};

export type PendingAction = {
  action_id?: string;
  action_type?: string;
  title?: string;
  summary?: string;
  tickets?: Array<Record<string, unknown>>;
  policy_notes?: string[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  agent_trace?: AgentTraceStep[];
  status?: string | null;
  intent?: string | null;
  note?: string | null;
  pending_action?: PendingAction | null;
  guard?: Record<string, unknown> | null;
};

export type DevUser = {
  userId: string;
  displayName: string;
};

export const STORY_CHIPS = [
  {
    id: "qa",
    label: "纯问答",
    text: "试用期员工年假怎么算？能不能请？",
  },
  {
    id: "compare",
    label: "对比归纳",
    text: "差旅制度和报销制度分别管什么？出差请客户吃饭记哪个科目？",
  },
  {
    id: "action",
    label: "行动确认",
    text: "按差旅政策起草一趟上海出差申请，并创建待办提醒我提交审批。",
  },
] as const;
