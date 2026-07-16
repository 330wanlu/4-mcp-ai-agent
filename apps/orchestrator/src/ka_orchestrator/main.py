"""Orchestrator 入口：健康检查 + Graph + QA 流水线。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ka_orchestrator.graph import AGENT_GRAPH_SUMMARY
from ka_orchestrator.pipeline import run_qa_pipeline
from ka_orchestrator.redis_state import SessionStore


class QARequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None
    user_id: str = "local-dev"
    top_k: int = Field(default=5, ge=1, le=20)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Knowledge Action Cluster Orchestrator",
        version="0.2.0",
        description="阶段 2：Router → Researcher → Analyst 问答闭环",
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "orchestrator", "phase": "2"}

    @application.get("/graph")
    async def graph() -> dict[str, object]:
        return AGENT_GRAPH_SUMMARY

    @application.post("/qa")
    async def qa(body: QARequest) -> dict[str, Any]:
        return await run_qa_pipeline(
            body.question,
            session_id=body.session_id,
            user_id=body.user_id,
            top_k=body.top_k,
        )

    @application.get("/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, Any]:
        store = SessionStore()
        try:
            state = await store.load(session_id)
        finally:
            await store.close()
        if state is None:
            return {"found": False, "session_id": session_id}
        return {"found": True, **state}

    return application


app = create_app()
