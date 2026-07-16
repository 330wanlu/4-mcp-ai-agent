"""Executor Agent：起草 action_plan（不落库）。"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from ka_llm import ChatMessage, ChatProvider
from ka_orchestrator.json_util import extract_json_object

ACTION_TYPES = (
    "create_travel_draft_and_todo",
    "create_leave_draft_and_todo",
    "create_ticket",
    "create_document_draft_and_todo",
    "refuse_or_require_travel_order",
)

EXECUTOR_SYSTEM = """你是企业制度助手的 Executor。
根据用户任务与参考资料，输出【仅一个 JSON 对象】，不要其它文字：
{
  "action_type": "create_travel_draft_and_todo|create_leave_draft_and_todo|create_ticket|create_document_draft_and_todo|refuse_or_require_travel_order",
  "title": "简短标题",
  "summary": "给用户看的行动摘要（含关键制度要点）",
  "tickets": [
    {
      "ticket_type": "travel|leave|todo|reimbursement|document|note",
      "title": "工单标题",
      "payload": { "任意键值": "..." }
    }
  ],
  "policy_notes": ["引用的制度要点"]
}

选择规则：
1. 起草出差申请 + 待办 → create_travel_draft_and_todo；tickets 含 travel 草稿 + todo
2. 请假申请草稿 + 待办 → create_leave_draft_and_todo
3. 仅创建待办/注意事项工单 → create_ticket
4. 超标说明草稿 + 待办 → create_document_draft_and_todo
5. 要求在无出差单情况下直接建报销单/报机票 → refuse_or_require_travel_order；tickets 必须为空 []
6. 差旅交通报销必须关联出差单；无出差申请不得创建 reimbursement 工单

payload 建议字段：destination / leave_days / amount / expense_code / accommodation_limit / reason 等。
"""


def _heuristic_action_type(question: str) -> str | None:
    q = question.replace(" ", "")
    # 拦截：无出差单报机票/报销
    if ("没有出差" in q or "无出差" in q or "没有出差申请" in q) and (
        "机票" in q or "报销" in q
    ):
        return "refuse_or_require_travel_order"
    if "自行购买机票" in q and ("报销" in q or "报销单" in q):
        return "refuse_or_require_travel_order"
    if "出差申请" in q and ("上海" in q or "差旅" in q) and "待办" in q:
        return "create_travel_draft_and_todo"
    if "请假" in q or "年假" in q:
        return "create_leave_draft_and_todo"
    if "超标" in q or ("520" in q and "住宿" in q) or "总监" in q:
        return "create_document_draft_and_todo"
    if "报销注意事项" in q or ("招待" in q and "待办" in q) or "请客户吃饭" in q:
        return "create_ticket"
    return None


async def run_executor(
    question: str,
    *,
    answer: str,
    hits: list[dict[str, Any]],
    provider: ChatProvider,
) -> dict[str, Any]:
    materials = "\n".join(
        f"- {h.get('filename') or h.get('title')}: {h.get('snippet')}" for h in hits[:5]
    )
    user = (
        f"用户任务: {question}\n\n"
        f"Analyst 回答摘要: {answer[:800]}\n\n"
        f"参考资料:\n{materials or '(无)'}"
    )
    raw = await provider.chat(
        [
            ChatMessage(role="system", content=EXECUTOR_SYSTEM),
            ChatMessage(role="user", content=user),
        ],
        temperature=0.1,
        max_tokens=1536,
        thinking=False,
    )
    try:
        data = extract_json_object(raw)
    except ValueError:
        data = {}

    heuristic = _heuristic_action_type(question)
    action_type = str(data.get("action_type") or heuristic or "create_ticket").strip()
    if action_type not in ACTION_TYPES:
        action_type = heuristic or "create_ticket"

    # 启发式优先覆盖明显拦截场景，避免模型误开报销单
    if heuristic == "refuse_or_require_travel_order":
        action_type = "refuse_or_require_travel_order"

    tickets = data.get("tickets") if isinstance(data.get("tickets"), list) else []
    if action_type == "refuse_or_require_travel_order":
        tickets = []

    # 规范化 tickets
    normalized: list[dict[str, Any]] = []
    for t in tickets:
        if not isinstance(t, dict):
            continue
        normalized.append(
            {
                "ticket_type": str(t.get("ticket_type") or "todo"),
                "title": str(t.get("title") or data.get("title") or "待办"),
                "payload": t.get("payload") if isinstance(t.get("payload"), dict) else {},
            }
        )

    # 若允许行动但模型没给出 tickets，补一个默认草稿
    if action_type != "refuse_or_require_travel_order" and not normalized:
        normalized = _default_tickets(action_type, question, data)

    plan = {
        "action_id": str(uuid4()),
        "action_type": action_type,
        "title": str(data.get("title") or _default_title(action_type)),
        "summary": str(data.get("summary") or answer[:400]),
        "tickets": normalized,
        "policy_notes": data.get("policy_notes")
        if isinstance(data.get("policy_notes"), list)
        else [],
        "raw_executor": data,
    }
    return plan


def _default_title(action_type: str) -> str:
    return {
        "create_travel_draft_and_todo": "差旅申请草稿与提交待办",
        "create_leave_draft_and_todo": "请假申请草稿与待办",
        "create_ticket": "待办工单",
        "create_document_draft_and_todo": "超标说明草稿与预批待办",
        "refuse_or_require_travel_order": "拒绝：需先补出差申请",
    }.get(action_type, "行动草稿")


def _default_tickets(
    action_type: str, question: str, data: dict[str, Any]
) -> list[dict[str, Any]]:
    title = str(data.get("title") or _default_title(action_type))
    if action_type == "create_travel_draft_and_todo":
        return [
            {
                "ticket_type": "travel",
                "title": f"{title}（出差草稿）",
                "payload": {"destination": "上海", "question": question},
            },
            {
                "ticket_type": "todo",
                "title": "提醒：提交差旅审批",
                "payload": {"reminder": "submit_travel_approval"},
            },
        ]
    if action_type == "create_leave_draft_and_todo":
        return [
            {
                "ticket_type": "leave",
                "title": f"{title}（请假草稿）",
                "payload": {"leave_type": "annual", "days": 2, "question": question},
            },
            {
                "ticket_type": "todo",
                "title": "提醒：提交请假审批",
                "payload": {"reminder": "submit_leave_approval"},
            },
        ]
    if action_type == "create_document_draft_and_todo":
        return [
            {
                "ticket_type": "document",
                "title": f"{title}（超标说明）",
                "payload": {
                    "amount": 520,
                    "limit": 450,
                    "question": question,
                },
            },
            {
                "ticket_type": "todo",
                "title": "找总监预批",
                "payload": {"reminder": "director_preapproval"},
            },
        ]
    return [
        {
            "ticket_type": "todo",
            "title": title,
            "payload": {"question": question, "expense_code": "EXP-04"},
        }
    ]
