"""Agent Graph 拓扑（阶段 5：Memory + Guard 增强 + 评测已接线）。"""

from __future__ import annotations

AGENT_GRAPH_MERMAID = """
flowchart TD
  U[User Message] --> M[Memory MCP]
  M --> R[Router Agent]
  R -->|qa / compare| Res[Researcher Agent]
  R -->|action| Res
  Res -->|Knowledge MCP| Res
  Res --> A[Analyst Agent]
  A -->|纯问答| AG[Answer Guard]
  AG -->|有引用| Out[Answer + Citations]
  AG -->|无引用| Deg[Degrade / Refuse]
  A -->|需行动| E[Executor Agent]
  E --> G[Critic / Guard]
  G -->|需确认| Wait[awaiting_confirmation]
  Wait -->|confirm| Biz[Business MCP]
  Wait -->|reject| Cancel[Cancel]
  G -->|冲突拦截| Block[Refuse / Degrade]
  Out --> M2[Memory Upsert]
  Deg --> M2
  Wait --> M2
  Block --> M2
  M2 --> Audit[audit_logs]
  Biz --> Audit
""".strip()

AGENT_NODES = [
    "memory",
    "router",
    "researcher",
    "analyst",
    "executor",
    "critic_guard",
]

ACTIVE_NODES_PHASE5 = [
    "memory",
    "router",
    "researcher",
    "analyst",
    "executor",
    "critic_guard",
]

EXTENSION_POINTS = {
    "llm": "packages/llm — ChatProvider / EmbeddingProvider → VolcengineDoubaoProvider",
    "parsers": "packages/parsers — DocumentParser → MarkdownParser / TextParser（PDF 后挂）",
    "auth": "packages/auth — AuthProvider → NoAuthProvider / DevHeaderAuthProvider",
    "mcp": "mcp_servers/* — Knowledge / Memory / Business 就绪；Comms 二期",
}

AGENT_GRAPH_SUMMARY: dict[str, object] = {
    "nodes": AGENT_NODES,
    "active_nodes": ACTIVE_NODES_PHASE5,
    "mermaid": AGENT_GRAPH_MERMAID,
    "extension_points": EXTENSION_POINTS,
    "phase": 5,
}
