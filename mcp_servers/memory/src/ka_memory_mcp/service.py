"""Memory MCP：会话摘要 + 用户偏好（PostgreSQL）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ka_common.db.models import SessionSummary, UserPreference
from ka_common.db.session import session_scope

TOOLS = (
    "get_session_summary",
    "upsert_session_summary",
    "get_user_preference",
    "upsert_user_preference",
)


def get_session_summary(
    session_id: str, *, session: Session | None = None
) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        row = s.get(SessionSummary, session_id)
        if row is None:
            return {
                "found": False,
                "session_id": session_id,
                "summary": "",
                "turns": [],
                "meta": {},
            }
        return {"found": True, **_summary_dict(row)}

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def upsert_session_summary(
    session_id: str,
    *,
    summary: str,
    user_id: str | None = None,
    turns: list[Any] | None = None,
    meta: dict[str, Any] | None = None,
    append_turn: dict[str, Any] | None = None,
    session: Session | None = None,
) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        row = s.get(SessionSummary, session_id)
        if row is None:
            row = SessionSummary(
                session_id=session_id,
                user_id=user_id,
                summary=summary or "",
                turns=list(turns or []),
                meta=dict(meta or {}),
            )
            s.add(row)
        else:
            row.summary = summary if summary is not None else (row.summary or "")
            if user_id is not None:
                row.user_id = user_id
            if turns is not None:
                row.turns = list(turns)
            if meta is not None:
                row.meta = {**(row.meta or {}), **meta}
        if append_turn is not None:
            current = list(row.turns or [])
            current.append(append_turn)
            # 保留最近 20 轮，避免无限膨胀
            row.turns = current[-20:]
        s.flush()
        return {"found": True, "upserted": True, **_summary_dict(row)}

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def get_user_preference(
    user_id: str, *, session: Session | None = None
) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        row = s.get(UserPreference, user_id)
        if row is None:
            return {
                "found": False,
                "user_id": user_id,
                "preferences": {},
                "notes": "",
            }
        return {"found": True, **_pref_dict(row)}

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def upsert_user_preference(
    user_id: str,
    *,
    preferences: dict[str, Any] | None = None,
    notes: str | None = None,
    merge: bool = True,
    session: Session | None = None,
) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        row = s.get(UserPreference, user_id)
        prefs = dict(preferences or {})
        if row is None:
            row = UserPreference(
                user_id=user_id,
                preferences=prefs,
                notes=notes or "",
            )
            s.add(row)
        else:
            if merge:
                row.preferences = {**(row.preferences or {}), **prefs}
            else:
                row.preferences = prefs
            if notes is not None:
                row.notes = notes
        s.flush()
        return {"found": True, "upserted": True, **_pref_dict(row)}

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def _summary_dict(row: SessionSummary) -> dict[str, Any]:
    return {
        "session_id": row.session_id,
        "user_id": row.user_id,
        "summary": row.summary or "",
        "turns": list(row.turns or []),
        "meta": dict(row.meta or {}),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _pref_dict(row: UserPreference) -> dict[str, Any]:
    return {
        "user_id": row.user_id,
        "preferences": dict(row.preferences or {}),
        "notes": row.notes or "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
