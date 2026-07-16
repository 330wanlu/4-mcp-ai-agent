"""Critic / Guard：行动与制度冲突拦截（MVP 硬规则）。"""

from __future__ import annotations

from typing import Any


def run_guard(
    question: str,
    action_plan: dict[str, Any],
) -> dict[str, Any]:
    """返回 allowed / blocked 与原因。blocked 时不得进入确认写库。"""
    action_type = str(action_plan.get("action_type") or "")
    tickets = action_plan.get("tickets") or []
    q = question or ""

    # 1) 显式拒绝类型
    if action_type == "refuse_or_require_travel_order":
        return {
            "allowed": False,
            "decision": "blocked",
            "reason": "制度要求差旅交通报销须关联出差申请单；请先补出差单再报销。",
            "action_type": action_type,
        }

    # 2) 禁止无出差单的报销类工单
    for t in tickets:
        ttype = str((t or {}).get("ticket_type") or "").lower()
        payload = (t or {}).get("payload") or {}
        if ttype == "reimbursement":
            has_travel = bool(
                payload.get("travel_order_id")
                or payload.get("travel_ticket_id")
                or payload.get("linked_travel")
            )
            if not has_travel:
                return {
                    "allowed": False,
                    "decision": "blocked",
                    "reason": "报销工单未关联出差申请，Guard 拦截。",
                    "action_type": action_type,
                }

    # 3) 用户话术明确无出差单却要报机票
    if ("机票" in q or "报销单" in q) and (
        "没有出差" in q or "无出差" in q or "自行购买" in q
    ):
        if action_type != "refuse_or_require_travel_order":
            return {
                "allowed": False,
                "decision": "blocked",
                "reason": "无出差申请的机票报销被 Guard 拦截。",
                "action_type": action_type,
            }

    # 4) MVP 权限：任何人可提草稿待确认（写死放行）
    return {
        "allowed": True,
        "decision": "awaiting_confirmation",
        "reason": "行动计划合规，等待用户确认后落库。",
        "action_type": action_type,
    }
