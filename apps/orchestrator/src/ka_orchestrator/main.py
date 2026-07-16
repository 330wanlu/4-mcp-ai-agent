"""Orchestrator 入口：QA + 确认闸门。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ka_orchestrator.confirmation import (
    confirm_pending_action,
    get_pending_actions,
    reject_pending_action,
)
from ka_orchestrator.graph import AGENT_GRAPH_SUMMARY
from ka_orchestrator.pipeline import run_qa_pipeline
from ka_orchestrator.redis_state import SessionStore


class QARequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None
    user_id: str = "local-dev"
    top_k: int = Field(default=5, ge=1, le=20)


class ConfirmRequest(BaseModel):
    user_id: str = "local-dev"


class RejectRequest(BaseModel):
    user_id: str = "local-dev"
    reason: str | None = None


def create_app() -> FastAPI:
    application = FastAPI(
        title="Knowledge Action Cluster Orchestrator",
        version="0.4.0",
        description="阶段 4：问答 + Executor/Guard + 确认闸门",
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "orchestrator", "phase": "4"}

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

    @application.get("/sessions/{session_id}/pending-actions")
    async def pending(session_id: str) -> dict[str, Any]:
        store = SessionStore()
        try:
            return await get_pending_actions(session_id, store=store)
        finally:
            await store.close()

    @application.post("/sessions/{session_id}/confirm")
    async def confirm(session_id: str, body: ConfirmRequest) -> dict[str, Any]:
        store = SessionStore()
        try:
            return await confirm_pending_action(
                session_id, user_id=body.user_id, store=store
            )
        finally:
            await store.close()

    @application.post("/sessions/{session_id}/reject")
    async def reject(session_id: str, body: RejectRequest) -> dict[str, Any]:
        store = SessionStore()
        try:
            return await reject_pending_action(
                session_id, user_id=body.user_id, reason=body.reason, store=store
            )
        finally:
            await store.close()

    return application


app = create_app()
