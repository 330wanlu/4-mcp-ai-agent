"""Knowledge MCP HTTP 入口（端口 8101）：暴露三工具供 smoke / 后续 Orchestrator 调用。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ka_knowledge_mcp.service import (
    TOOLS,
    get_document_section,
    hybrid_search,
    list_sources,
)

PORT = 8101


class HybridSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class GetSectionRequest(BaseModel):
    doc_id: str
    section: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Knowledge MCP",
        version="0.1.0",
        description="阶段 1：hybrid_search / get_document_section / list_sources",
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "knowledge-mcp", "port": PORT, "tools": list(TOOLS)}

    @app.get("/tools")
    async def tools() -> dict[str, Any]:
        return {"tools": list(TOOLS)}

    @app.post("/tools/hybrid_search")
    async def tool_hybrid_search(body: HybridSearchRequest) -> dict[str, Any]:
        hits = await hybrid_search(body.query, top_k=body.top_k)
        return {"query": body.query, "count": len(hits), "results": hits}

    @app.post("/tools/get_document_section")
    async def tool_get_section(body: GetSectionRequest) -> dict[str, Any]:
        return get_document_section(body.doc_id, body.section)

    @app.get("/tools/list_sources")
    async def tool_list_sources() -> dict[str, Any]:
        sources = list_sources()
        return {"count": len(sources), "sources": sources}

    return app


app = create_app()


def describe() -> dict[str, object]:
    return {
        "name": "knowledge",
        "port": PORT,
        "tools": list(TOOLS),
        "phase": 1,
        "status": "ready",
    }


def main() -> None:
    import uvicorn

    print(f"[knowledge-mcp] starting on :{PORT} tools={list(TOOLS)}")
    uvicorn.run("ka_knowledge_mcp.server:app", host="127.0.0.1", port=PORT, reload=False)


if __name__ == "__main__":
    main()
