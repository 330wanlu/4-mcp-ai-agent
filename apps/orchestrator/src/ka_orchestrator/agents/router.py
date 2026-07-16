"""Router Agent：意图分类 + 检索查询改写。"""

from __future__ import annotations

from typing import Any, Literal

from ka_llm import ChatMessage, ChatProvider
from ka_orchestrator.json_util import extract_json_object

Intent = Literal["qa", "compare", "action"]


ROUTER_SYSTEM = """你是企业制度助手的 Router。
根据用户问题输出 JSON（不要其它文字）：
{
  "intent": "qa" | "compare" | "action",
  "search_query": "用于知识库检索的简洁中文查询",
  "reason": "一句话理由"
}
规则：
- 问制度规则、标准、流程 → qa
- 对比两个制度/边界/分别管什么 → compare
- 要求起草申请、创建待办/工单、生成草稿、帮我开单等写操作 → action
- search_query 保留关键实体（城市、职级、金额、假期类型等）
"""


def _heuristic_intent(question: str) -> str | None:
    q = question.replace(" ", "")
    action_markers = (
        "起草",
        "创建待办",
        "生成请假",
        "生成超标",
        "开一张",
        "帮我开",
        "创建「",
        "创建\"",
        "报销单草稿",
        "申请草稿",
        "提醒我提交",
    )
    if any(m in q for m in action_markers):
        return "action"
    if "分别管什么" in q or "冲突时听谁" in q or ("对比" in q):
        return "compare"
    return None


async def run_router(
    question: str,
    *,
    provider: ChatProvider,
) -> dict[str, Any]:
    raw = await provider.chat(
        [
            ChatMessage(role="system", content=ROUTER_SYSTEM),
            ChatMessage(role="user", content=question),
        ],
        temperature=0.1,
        max_tokens=512,
        thinking=False,
    )
    try:
        data = extract_json_object(raw)
    except ValueError:
        data = {
            "intent": "qa",
            "search_query": question,
            "reason": "JSON 解析失败，回退 qa",
        }

    intent = str(data.get("intent") or "qa").lower().strip()
    if intent not in ("qa", "compare", "action"):
        intent = "qa"
    # 启发式纠偏：明显写操作优先 action
    forced = _heuristic_intent(question)
    if forced == "action":
        intent = "action"
    elif forced == "compare" and intent == "qa":
        intent = "compare"

    search_query = str(data.get("search_query") or question).strip() or question
    reason = str(data.get("reason") or "")
    return {"intent": intent, "search_query": search_query, "reason": reason}
