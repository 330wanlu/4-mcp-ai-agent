"""Business MCP HTTP 入口（端口 8103）。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ka_business_mcp.service import (
    TOOLS,
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket,
)

PORT = 8103


class CreateTicketRequest(BaseModel):
    ticket_type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    status: str = "draft"


class UpdateTicketRequest(BaseModel):
    ticket_id: str
    title: str | None = None
    status: str | None = None
    payload: dict[str, Any] | None = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Business MCP",
        version="0.4.0",
        description="阶段 4：tickets 写操作（须经确认闸门后调用）",
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "business-mcp", "port": PORT, "tools": list(TOOLS)}

    @app.get("/tools")
    async def tools() -> dict[str, Any]:
        return {"tools": list(TOOLS)}

    @app.post("/tools/create_ticket")
    async def tool_create(body: CreateTicketRequest) -> dict[str, Any]:
        return create_ticket(
            ticket_type=body.ticket_type,
            title=body.title,
            payload=body.payload,
            created_by=body.created_by,
            status=body.status,
        )

    @app.post("/tools/update_ticket")
    async def tool_update(body: UpdateTicketRequest) -> dict[str, Any]:
        return update_ticket(
            body.ticket_id,
            title=body.title,
            status=body.status,
            payload=body.payload,
        )

    @app.get("/tools/get_ticket/{ticket_id}")
    async def tool_get(ticket_id: str) -> dict[str, Any]:
        return get_ticket(ticket_id)

    @app.get("/tools/list_tickets")
    async def tool_list(
        created_by: str | None = None,
        ticket_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        rows = list_tickets(created_by=created_by, ticket_type=ticket_type, limit=limit)
        return {"count": len(rows), "tickets": rows}

    return app


app = create_app()


def describe() -> dict[str, object]:
    return {
        "name": "business",
        "port": PORT,
        "tools": list(TOOLS),
        "phase": 4,
        "status": "ready",
    }


def main() -> None:
    import uvicorn

    print(f"[business-mcp] starting on :{PORT} tools={list(TOOLS)}")
    uvicorn.run("ka_business_mcp.server:app", host="127.0.0.1", port=PORT, reload=False)


if __name__ == "__main__":
    main()
