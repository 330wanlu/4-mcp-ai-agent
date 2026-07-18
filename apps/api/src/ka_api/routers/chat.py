"""Chat 会话与消息路由。"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from ka_api.deps import CurrentUser, OrchestratorDep
from ka_api.errors import ApiError
from ka_api.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    PostMessageRequest,
    PostMessageResponse,
    SessionDetailResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    user: CurrentUser,
    orch: OrchestratorDep,
) -> CreateSessionResponse:
    state = await orch.create_session(user_id=user.user_id, title=body.title)
    return CreateSessionResponse(
        session_id=state["session_id"],
        user_id=user.user_id,
        status=state.get("status") or "created",
        title=body.title,
    )


@router.post("/sessions/{session_id}/messages", response_model=PostMessageResponse)
async def post_message(
    session_id: str,
    body: PostMessageRequest,
    user: CurrentUser,
    orch: OrchestratorDep,
) -> PostMessageResponse:
    existing = await orch.get_session(session_id)
    if not existing.get("found"):
        raise ApiError(
            "SESSION_NOT_FOUND",
            f"会话不存在: {session_id}",
            status_code=404,
        )

    result = await orch.ask(
        question=body.content,
        session_id=session_id,
        user_id=user.user_id,
        top_k=body.top_k,
    )
    return PostMessageResponse(
        session_id=session_id,
        message_id=str(result.get("message_id") or uuid4()),
        intent=result.get("intent"),
        answer=str(result.get("answer") or ""),
        citations=list(result.get("citations") or []),
        agent_trace=list(result.get("agent_trace") or []),
        note=result.get("note"),
        status=result.get("status"),
        pending_action=result.get("pending_action"),
        guard=result.get("guard"),
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    user: CurrentUser,
    orch: OrchestratorDep,
) -> SessionDetailResponse:
    _ = user  # 鉴权挂载点：后续可按 user 做可见性校验
    state = await orch.get_session(session_id)
    if not state.get("found"):
        raise ApiError(
            "SESSION_NOT_FOUND",
            f"会话不存在: {session_id}",
            status_code=404,
        )
    return SessionDetailResponse(
        found=True,
        session_id=session_id,
        status=state.get("status"),
        user_id=state.get("user_id"),
        question=state.get("question"),
        answer=state.get("answer"),
        intent=state.get("intent"),
        citations=list(state.get("citations") or []),
        agent_trace=list(state.get("agent_trace") or []),
        current_node=state.get("current_node"),
        title=state.get("title"),
        note=state.get("note"),
        messages=list(state.get("messages") or []),
        pending_action=state.get("pending_action"),
        guard=state.get("guard"),
    )
