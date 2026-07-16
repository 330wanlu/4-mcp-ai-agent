"""确认闸门：confirm 才写 tickets；reject 清空 pending。"""

from __future__ import annotations

from typing import Any

from ka_mcp_clients import BusinessMcpClient
from ka_orchestrator.audit import write_audit
from ka_orchestrator.redis_state import SessionStore


async def confirm_pending_action(
    session_id: str,
    *,
    user_id: str = "local-dev",
    store: SessionStore | None = None,
    business: BusinessMcpClient | None = None,
) -> dict[str, Any]:
    store = store or SessionStore()
    business = business or BusinessMcpClient(mode="local")
    state = await store.load(session_id)
    if not state:
        return {"ok": False, "error": "SESSION_NOT_FOUND", "session_id": session_id}
    if state.get("status") != "awaiting_confirmation":
        return {
            "ok": False,
            "error": "NO_PENDING_ACTION",
            "session_id": session_id,
            "status": state.get("status"),
        }
    pending = state.get("pending_action")
    if not isinstance(pending, dict):
        return {"ok": False, "error": "NO_PENDING_ACTION", "session_id": session_id}

    created: list[dict[str, Any]] = []
    for t in pending.get("tickets") or []:
        payload = dict(t.get("payload") or {})
        payload["session_id"] = session_id
        payload["action_id"] = pending.get("action_id")
        payload["action_type"] = pending.get("action_type")
        row = await business.create_ticket(
            ticket_type=str(t.get("ticket_type") or "todo"),
            title=str(t.get("title") or pending.get("title") or "ticket"),
            payload=payload,
            created_by=user_id,
            status="draft",
        )
        created.append(row)

    write_audit(
        session_id=session_id,
        event_type="action_execute",
        agent="executor",
        user_id=user_id,
        detail={
            "action_id": pending.get("action_id"),
            "action_type": pending.get("action_type"),
            "ticket_ids": [c.get("id") for c in created],
        },
    )

    await store.update(
        session_id,
        status="completed",
        current_node="done",
        pending_action=None,
        executed_tickets=created,
        confirmation="confirmed",
    )
    return {
        "ok": True,
        "session_id": session_id,
        "tickets": created,
        "action_type": pending.get("action_type"),
    }


async def reject_pending_action(
    session_id: str,
    *,
    user_id: str = "local-dev",
    reason: str | None = None,
    store: SessionStore | None = None,
) -> dict[str, Any]:
    store = store or SessionStore()
    state = await store.load(session_id)
    if not state:
        return {"ok": False, "error": "SESSION_NOT_FOUND", "session_id": session_id}
    if state.get("status") != "awaiting_confirmation":
        return {
            "ok": False,
            "error": "NO_PENDING_ACTION",
            "session_id": session_id,
            "status": state.get("status"),
        }
    pending = state.get("pending_action") or {}
    write_audit(
        session_id=session_id,
        event_type="action_reject",
        agent="executor",
        user_id=user_id,
        detail={
            "action_id": pending.get("action_id"),
            "action_type": pending.get("action_type"),
            "reason": reason or "user_rejected",
        },
    )
    await store.update(
        session_id,
        status="rejected",
        current_node="done",
        pending_action=None,
        confirmation="rejected",
        reject_reason=reason or "user_rejected",
    )
    return {"ok": True, "session_id": session_id, "status": "rejected"}


async def get_pending_actions(
    session_id: str,
    *,
    store: SessionStore | None = None,
) -> dict[str, Any]:
    store = store or SessionStore()
    state = await store.load(session_id)
    if not state:
        return {"found": False, "session_id": session_id, "pending_actions": []}
    pending = state.get("pending_action")
    items = [pending] if isinstance(pending, dict) else []
    return {
        "found": True,
        "session_id": session_id,
        "status": state.get("status"),
        "pending_actions": items,
    }
