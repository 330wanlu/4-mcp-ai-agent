"""Memory MCP 客户端：默认进程内。"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from ka_common.config import Settings, get_settings

Mode = Literal["local", "http"]


class MemoryMcpClient:
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
        self.base_url = self.settings.memory_mcp_url.rstrip("/")

    async def get_session_summary(self, session_id: str) -> dict[str, Any]:
        if self.mode == "local":
            from ka_memory_mcp.service import get_session_summary

            return get_session_summary(session_id)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/tools/get_session_summary/{session_id}"
            )
            resp.raise_for_status()
            return resp.json()

    async def upsert_session_summary(
        self,
        session_id: str,
        *,
        summary: str,
        user_id: str | None = None,
        turns: list[Any] | None = None,
        meta: dict[str, Any] | None = None,
        append_turn: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.mode == "local":
            from ka_memory_mcp.service import upsert_session_summary

            return upsert_session_summary(
                session_id,
                summary=summary,
                user_id=user_id,
                turns=turns,
                meta=meta,
                append_turn=append_turn,
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/tools/upsert_session_summary",
                json={
                    "session_id": session_id,
                    "summary": summary,
                    "user_id": user_id,
                    "turns": turns,
                    "meta": meta,
                    "append_turn": append_turn,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_preference(self, user_id: str) -> dict[str, Any]:
        if self.mode == "local":
            from ka_memory_mcp.service import get_user_preference

            return get_user_preference(user_id)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/tools/get_user_preference/{user_id}"
            )
            resp.raise_for_status()
            return resp.json()

    async def upsert_user_preference(
        self,
        user_id: str,
        *,
        preferences: dict[str, Any] | None = None,
        notes: str | None = None,
        merge: bool = True,
    ) -> dict[str, Any]:
        if self.mode == "local":
            from ka_memory_mcp.service import upsert_user_preference

            return upsert_user_preference(
                user_id,
                preferences=preferences,
                notes=notes,
                merge=merge,
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/tools/upsert_user_preference",
                json={
                    "user_id": user_id,
                    "preferences": preferences or {},
                    "notes": notes,
                    "merge": merge,
                },
            )
            resp.raise_for_status()
            return resp.json()
