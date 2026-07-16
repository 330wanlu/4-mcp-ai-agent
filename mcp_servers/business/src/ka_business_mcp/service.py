"""Business MCP：tickets 读写（确认后才落库）。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ka_common.db.models import Ticket
from ka_common.db.session import session_scope


def create_ticket(
    *,
    ticket_type: str,
    title: str,
    payload: dict[str, Any] | None = None,
    created_by: str | None = None,
    status: str = "draft",
    session: Session | None = None,
) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        row = Ticket(
            id=str(uuid4()),
            ticket_type=ticket_type,
            title=title,
            status=status,
            payload=payload or {},
            created_by=created_by,
        )
        s.add(row)
        s.flush()
        return _to_dict(row)

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def update_ticket(
    ticket_id: str,
    *,
    title: str | None = None,
    status: str | None = None,
    payload: dict[str, Any] | None = None,
    session: Session | None = None,
) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        row = s.get(Ticket, ticket_id)
        if row is None:
            return {"found": False, "ticket_id": ticket_id}
        if title is not None:
            row.title = title
        if status is not None:
            row.status = status
        if payload is not None:
            row.payload = payload
        s.flush()
        return {"found": True, **_to_dict(row)}

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def get_ticket(ticket_id: str, *, session: Session | None = None) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        row = s.get(Ticket, ticket_id)
        if row is None:
            return {"found": False, "ticket_id": ticket_id}
        return {"found": True, **_to_dict(row)}

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def list_tickets(
    *,
    created_by: str | None = None,
    ticket_type: str | None = None,
    limit: int = 50,
    session: Session | None = None,
) -> list[dict[str, Any]]:
    def _run(s: Session) -> list[dict[str, Any]]:
        stmt = select(Ticket).order_by(desc(Ticket.created_at)).limit(limit)
        if created_by:
            stmt = stmt.where(Ticket.created_by == created_by)
        if ticket_type:
            stmt = stmt.where(Ticket.ticket_type == ticket_type)
        return [_to_dict(r) for r in s.scalars(stmt).all()]

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def count_tickets(*, session_id: str | None = None) -> int:
    """按 payload.session_id 计数（用于闸门断言）。"""
    with session_scope() as s:
        rows = s.scalars(select(Ticket)).all()
        if not session_id:
            return len(rows)
        return sum(1 for r in rows if (r.payload or {}).get("session_id") == session_id)


def _to_dict(row: Ticket) -> dict[str, Any]:
    return {
        "id": row.id,
        "ticket_type": row.ticket_type,
        "title": row.title,
        "status": row.status,
        "payload": row.payload or {},
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


TOOLS = ("create_ticket", "update_ticket", "get_ticket", "list_tickets")
