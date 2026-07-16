"""跨服务共用的轻量 schema（阶段 0 最小集）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_id: str
    title: str
    section: str | None = None
    score: float | None = None
    snippet: str | None = None


class AgentTraceStep(BaseModel):
    agent: str
    action: str
    detail: dict[str, Any] = Field(default_factory=dict)


class QAItem(BaseModel):
    id: str
    question: str
    expected_answer_points: list[str] = Field(default_factory=list)
    source_docs: list[str] = Field(default_factory=list)
    story: str | None = None  # qa | compare | action


class ActionTask(BaseModel):
    id: str
    task: str
    expected_action_type: str
    source_docs: list[str] = Field(default_factory=list)
    notes: str | None = None
