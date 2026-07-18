"""Memory MCP HTTP 入口（端口 8102）。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ka_memory_mcp.service import (
    TOOLS,
    get_session_summary,
    get_user_preference,
    upsert_session_summary,
    upsert_user_preference,
)

PORT = 8102


class UpsertSessionSummaryRequest(BaseModel):
    session_id: str
    summary: str = ""
    user_id: str | None = None
    turns: list[Any] | None = None
    meta: dict[str, Any] | None = None
    append_turn: dict[str, Any] | None = None


class UpsertUserPreferenceRequest(BaseModel):
    user_id: str
    preferences: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    merge: bool = True


def create_app() -> FastAPI:
    app = FastAPI(
        title="Memory MCP",
        version="0.5.0",
        description="阶段 5：会话摘要 + 用户偏好",
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "memory-mcp",
            "port": PORT,
            "tools": list(TOOLS),
        }

    @app.get("/tools")
    async def tools() -> dict[str, Any]:
        return {"tools": list(TOOLS)}

    @app.get("/tools/get_session_summary/{session_id}")
    async def tool_get_summary(session_id: str) -> dict[str, Any]:
        return get_session_summary(session_id)

    @app.post("/tools/upsert_session_summary")
    async def tool_upsert_summary(body: UpsertSessionSummaryRequest) -> dict[str, Any]:
        return upsert_session_summary(
            body.session_id,
            summary=body.summary,
            user_id=body.user_id,
            turns=body.turns,
            meta=body.meta,
            append_turn=body.append_turn,
        )

    @app.get("/tools/get_user_preference/{user_id}")
    async def tool_get_pref(user_id: str) -> dict[str, Any]:
        return get_user_preference(user_id)

    @app.post("/tools/upsert_user_preference")
    async def tool_upsert_pref(body: UpsertUserPreferenceRequest) -> dict[str, Any]:
        return upsert_user_preference(
            body.user_id,
            preferences=body.preferences,
            notes=body.notes,
            merge=body.merge,
        )

    return app


app = create_app()


def describe() -> dict[str, object]:
    return {
        "name": "memory",
        "port": PORT,
        "tools": list(TOOLS),
        "phase": 5,
        "status": "ready",
    }


def main() -> None:
    import uvicorn

    print(f"[memory-mcp] starting on :{PORT} tools={list(TOOLS)}")
    uvicorn.run("ka_memory_mcp.server:app", host="127.0.0.1", port=PORT, reload=False)


if __name__ == "__main__":
    main()
