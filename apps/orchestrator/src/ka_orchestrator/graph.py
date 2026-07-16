"""Agent Graph 拓扑（阶段 2：Router/Researcher/Analyst 已接线）。"""

from __future__ import annotations

AGENT_GRAPH_MERMAID = """
flowchart TD
  U[User Message] --> R[Router Agent]
  R -->|qa / compare| Res[Researcher Agent]
  R -->|action| Res
  Res -->|Knowledge MCP| Res
  Res --> A[Analyst Agent]
  A -->|纯问答结束| Out[Answer + Citations]
  A -->|需行动| E[Executor Agent]
  E --> G[Critic / Guard]
  G -->|需确认| Wait[awaiting_confirmation]
  Wait -->|confirm| Biz[Business MCP]
  Wait -->|reject| Cancel[Cancel]
  G -->|冲突拦截| Block[Refuse / Degrade]
  Out --> Audit[audit_logs]
  Biz --> Audit
""".strip()

AGENT_NODES = [
    "router",
    "researcher",
    "analyst",
    "executor",
    "critic_guard",
]

ACTIVE_NODES_PHASE2 = ["router", "researcher", "analyst"]

EXTENSION_POINTS = {
    "llm": "packages/llm — ChatProvider / EmbeddingProvider → VolcengineDoubaoProvider",
    "parsers": "packages/parsers — DocumentParser → MarkdownParser / TextParser（PDF 后挂）",
    "auth": "packages/auth — AuthProvider → NoAuthProvider / DevHeaderAuthProvider",
    "mcp": "mcp_servers/* — Knowledge / Memory / Business / Comms（Comms 二期）",
}

AGENT_GRAPH_SUMMARY: dict[str, object] = {
    "nodes": AGENT_NODES,
    "active_nodes": ACTIVE_NODES_PHASE2,
    "mermaid": AGENT_GRAPH_MERMAID,
    "extension_points": EXTENSION_POINTS,
    "phase": 2,
}
