"""Researcher Agent：调用 Knowledge MCP 检索。"""

from __future__ import annotations

from typing import Any

from ka_mcp_clients import KnowledgeMcpClient


async def run_researcher(
    search_query: str,
    *,
    knowledge: KnowledgeMcpClient,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    hits = await knowledge.hybrid_search(search_query, top_k=top_k)
    return hits
