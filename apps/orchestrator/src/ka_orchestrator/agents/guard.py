"""Critic / Guard：无引用降级/拒答 + 行动与制度冲突拦截。"""

from __future__ import annotations

from typing import Any


DEGRADE_MESSAGE = (
    "【资料不足，已降级】当前检索未找到可引用的制度原文，"
    "无法给出带依据的关键制度结论。请换个问法，或指定文档/章节后再问。"
)


def run_answer_guard(
    *,
    question: str,
    answer: str,
    citations: list[dict[str, Any]] | None,
    hits: list[dict[str, Any]] | None = None,
    intent: str = "qa",
) -> dict[str, Any]:
    """问答质检：无检索命中 / 无引用 / 域外闲聊 → 降级拒答关键结论。"""
    citations = citations or []
    hits = hits or []
    q = question or ""

    # 1) 明显域外/闲聊：即使向量有近邻命中，也不给制度结论
    if intent != "action" and _looks_out_of_domain(q):
        return {
            "allowed": False,
            "decision": "degraded",
            "reason": "问题超出制度语料域，降级拒答。",
            "scope": "answer",
            "citation_count": len(citations),
            "hit_count": len(hits),
            "degraded_answer": DEGRADE_MESSAGE,
            "out_of_domain": True,
        }

    # 2) 无命中 / 无引用
    if not hits and not citations:
        return {
            "allowed": False,
            "decision": "degraded",
            "reason": "无检索命中且无引用，拒答关键制度结论。",
            "scope": "answer",
            "citation_count": 0,
            "hit_count": 0,
            "degraded_answer": DEGRADE_MESSAGE,
        }

    if not citations:
        return {
            "allowed": False,
            "decision": "degraded",
            "reason": "答案缺少可核对引用，降级拒答。",
            "scope": "answer",
            "citation_count": 0,
            "hit_count": len(hits),
            "degraded_answer": DEGRADE_MESSAGE,
        }

    # 3) 检索分数过低：视为不可靠
    scores = [
        float(c.get("score") or 0) for c in citations if c.get("score") is not None
    ]
    if scores and max(scores) < 0.22 and intent != "action":
        return {
            "allowed": False,
            "decision": "degraded",
            "reason": "引用相关度过低，降级拒答。",
            "scope": "answer",
            "citation_count": len(citations),
            "hit_count": len(hits),
            "degraded_answer": DEGRADE_MESSAGE,
        }

    return {
        "allowed": True,
        "decision": "pass",
        "reason": "引用质检通过",
        "scope": "answer",
        "citation_count": len(citations),
        "hit_count": len(hits),
        "out_of_domain": False,
    }


def run_guard(
    question: str,
    action_plan: dict[str, Any],
) -> dict[str, Any]:
    """行动质检：与制度冲突则拦截，确认前不得落库。"""
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
            "scope": "action",
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
                    "scope": "action",
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
                "scope": "action",
            }

    # 4) 缺 tickets 的可写行动：拦截（避免空确认）
    writable = {
        "create_travel_draft_and_todo",
        "create_leave_draft_and_todo",
        "create_ticket",
        "create_document_draft_and_todo",
    }
    if action_type in writable and not tickets:
        return {
            "allowed": False,
            "decision": "blocked",
            "reason": "行动计划缺少可落库 tickets，Guard 拦截。",
            "action_type": action_type,
            "scope": "action",
        }

    # 5) MVP 权限：任何人可提草稿待确认（写死放行）
    return {
        "allowed": True,
        "decision": "awaiting_confirmation",
        "reason": "行动计划合规，等待用户确认后落库。",
        "action_type": action_type,
        "scope": "action",
    }


def _looks_out_of_domain(question: str) -> bool:
    q = (question or "").lower()
    domain_kw = (
        "年假",
        "请假",
        "差旅",
        "出差",
        "报销",
        "试用期",
        "住宿",
        "补助",
        "审批",
        "制度",
        "员工手册",
        "事假",
        "机票",
        "入职",
        "绩效",
        "招待",
    )
    if any(k in question for k in domain_kw):
        return False
    chat_kw = (
        "天气",
        "笑话",
        "今天中午吃什么",
        "写一首",
        "比特币",
        "股票",
        "足球比分",
        "唱一首",
        "讲个故事",
    )
    return any(k in q for k in chat_kw)
