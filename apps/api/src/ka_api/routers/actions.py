"""行动确认闸门 API。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ka_api.deps import CurrentUser, OrchestratorDep
from ka_api.errors import ApiError
from ka_orchestrator.confirmation import (
    confirm_pending_action,
    get_pending_actions,
    reject_pending_action,
)
from ka_orchestrator.redis_state import SessionStore

router = APIRouter(prefix="/chat", tags=["actions"])


class RejectBody(BaseModel):
    reason: str | None = None


@router.get("/sessions/{session_id}/pending-actions")
async def pending_actions(
    session_id: str,
    user: CurrentUser,
    orch: OrchestratorDep,
) -> dict[str, Any]:
    _ = user
    # 先确认会话存在
    state = await orch.get_session(session_id)
    if not state.get("found"):
        raise ApiError("SESSION_NOT_FOUND", f"会话不存在: {session_id}", status_code=404)
    store = SessionStore()
    try:
        return await get_pending_actions(session_id, store=store)
    finally:
        await store.close()


@router.post("/sessions/{session_id}/confirm")
async def confirm_action(
    session_id: str,
    user: CurrentUser,
    orch: OrchestratorDep,
) -> dict[str, Any]:
    state = await orch.get_session(session_id)
    if not state.get("found"):
        raise ApiError("SESSION_NOT_FOUND", f"会话不存在: {session_id}", status_code=404)
    store = SessionStore()
    try:
        result = await confirm_pending_action(
            session_id, user_id=user.user_id, store=store
        )
    finally:
        await store.close()
    if not result.get("ok"):
        code = str(result.get("error") or "CONFIRM_FAILED")
        raise ApiError(code, code, status_code=400, detail=result)
    return result


@router.post("/sessions/{session_id}/reject")
async def reject_action(
    session_id: str,
    user: CurrentUser,
    orch: OrchestratorDep,
    body: RejectBody | None = None,
) -> dict[str, Any]:
    state = await orch.get_session(session_id)
    if not state.get("found"):
        raise ApiError("SESSION_NOT_FOUND", f"会话不存在: {session_id}", status_code=404)
    store = SessionStore()
    try:
        result = await reject_pending_action(
            session_id,
            user_id=user.user_id,
            reason=(body.reason if body else None),
            store=store,
        )
    finally:
        await store.close()
    if not result.get("ok"):
        code = str(result.get("error") or "REJECT_FAILED")
        raise ApiError(code, code, status_code=400, detail=result)
    return result
