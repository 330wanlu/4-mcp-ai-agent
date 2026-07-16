"""Knowledge MCP 客户端：默认进程内调用；可选 HTTP。"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from ka_common.config import Settings, get_settings


Mode = Literal["local", "http"]


class KnowledgeMcpClient:
    """阶段 2：Orchestrator 通过本客户端检索；local 便于 CLI/pytest。"""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        mode: Mode = "local",
        timeout: float = 60.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.mode = mode
        self.timeout = timeout
        self.base_url = self.settings.knowledge_mcp_url.rstrip("/")

    async def hybrid_search(self, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        if self.mode == "local":
            from ka_knowledge_mcp.service import hybrid_search

            return await hybrid_search(query, top_k=top_k)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/tools/hybrid_search",
                json={"query": query, "top_k": top_k},
            )
            resp.raise_for_status()
            data = resp.json()
            return list(data.get("results") or [])

    async def list_sources(self) -> list[dict[str, Any]]:
        if self.mode == "local":
            from ka_knowledge_mcp.service import list_sources

            return list_sources()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/tools/list_sources")
            resp.raise_for_status()
            return list(resp.json().get("sources") or [])

    async def get_document_section(
        self, doc_id: str, section: str | None = None
    ) -> dict[str, Any]:
        if self.mode == "local":
            from ka_knowledge_mcp.service import get_document_section

            return get_document_section(doc_id, section)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/tools/get_document_section",
                json={"doc_id": doc_id, "section": section},
            )
            resp.raise_for_status()
            return resp.json()
