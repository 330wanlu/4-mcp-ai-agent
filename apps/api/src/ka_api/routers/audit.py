"""审计事件查询。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from ka_api.deps import CurrentUser
from ka_common.db.models import AuditLog
from ka_common.db.session import session_scope

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
async def list_audit_events(
    user: CurrentUser,
    session_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    _ = user
    with session_scope() as session:
        stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        if session_id:
            stmt = stmt.where(AuditLog.session_id == session_id)
        if event_type:
            stmt = stmt.where(AuditLog.event_type == event_type)
        rows = session.scalars(stmt).all()
        events = [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "session_id": r.session_id,
                "user_id": r.user_id,
                "event_type": r.event_type,
                "agent": r.agent,
                "detail": r.detail or {},
            }
            for r in rows
        ]
    return {"count": len(events), "events": events}
