"""API 请求 / 响应模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    user_id: str
    status: str
    title: str | None = None


class PostMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class PostMessageResponse(BaseModel):
    session_id: str
    message_id: str
    intent: str | None = None
    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    note: str | None = None
    # 阶段 6：前端需要状态与待确认行动，避免二次猜测
    status: str | None = None
    pending_action: dict[str, Any] | None = None
    guard: dict[str, Any] | None = None


class SessionDetailResponse(BaseModel):
    found: bool
    session_id: str
    status: str | None = None
    user_id: str | None = None
    question: str | None = None
    answer: str | None = None
    intent: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    current_node: str | None = None
    title: str | None = None
    note: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    pending_action: dict[str, Any] | None = None
    guard: dict[str, Any] | None = None
