"""Business MCP 客户端：默认进程内。"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from ka_common.config import Settings, get_settings

Mode = Literal["local", "http"]


class BusinessMcpClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        mode: Mode = "local",
        timeout: float = 30.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.mode = mode
        self.timeout = timeout
        self.base_url = self.settings.business_mcp_url.rstrip("/")

    async def create_ticket(
        self,
        *,
        ticket_type: str,
        title: str,
        payload: dict[str, Any] | None = None,
        created_by: str | None = None,
        status: str = "draft",
    ) -> dict[str, Any]:
        if self.mode == "local":
            from ka_business_mcp.service import create_ticket

            return create_ticket(
                ticket_type=ticket_type,
                title=title,
                payload=payload,
                created_by=created_by,
                status=status,
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/tools/create_ticket",
                json={
                    "ticket_type": ticket_type,
                    "title": title,
                    "payload": payload or {},
                    "created_by": created_by,
                    "status": status,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def list_tickets(
        self,
        *,
        created_by: str | None = None,
        ticket_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if self.mode == "local":
            from ka_business_mcp.service import list_tickets

            return list_tickets(
                created_by=created_by, ticket_type=ticket_type, limit=limit
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/tools/list_tickets",
                params={
                    k: v
                    for k, v in {
                        "created_by": created_by,
                        "ticket_type": ticket_type,
                        "limit": limit,
                    }.items()
                    if v is not None
                },
            )
            resp.raise_for_status()
            return list(resp.json().get("tickets") or [])
