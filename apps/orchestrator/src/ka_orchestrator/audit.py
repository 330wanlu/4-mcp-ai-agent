"""写入 Postgres audit_logs。"""

from __future__ import annotations

from typing import Any

from ka_common.db.models import AuditLog
from ka_common.db.session import session_scope


def write_audit(
    *,
    session_id: str | None,
    event_type: str,
    agent: str | None = None,
    user_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> str:
    with session_scope() as session:
        row = AuditLog(
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            agent=agent,
            detail=detail or {},
        )
        session.add(row)
        session.flush()
        return str(row.id)
