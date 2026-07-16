"""Agent 流水线：Router → Researcher → Analyst →（action）Executor → Guard。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from ka_common.schema import AgentTraceStep
from ka_llm import ChatProvider, get_llm_provider
from ka_mcp_clients import KnowledgeMcpClient
from ka_orchestrator.agents import (
    run_analyst,
    run_executor,
    run_guard,
    run_researcher,
    run_router,
)
from ka_orchestrator.audit import write_audit
from ka_orchestrator.redis_state import SessionStore


async def run_qa_pipeline(
    question: str,
    *,
    session_id: str | None = None,
    user_id: str = "local-dev",
    top_k: int = 5,
    provider: ChatProvider | None = None,
    knowledge: KnowledgeMcpClient | None = None,
    store: SessionStore | None = None,
    persist: bool = True,
    enable_actions: bool = True,
) -> dict[str, Any]:
    """问答闭环；intent=action 时进入 Executor+Guard，确认前不写 tickets。"""
    session_id = session_id or str(uuid4())
    provider = provider or get_llm_provider()
    knowledge = knowledge or KnowledgeMcpClient(mode="local")
    store = store or SessionStore()
    trace: list[dict[str, Any]] = []

    async def _set_node(node: str, status: str = "running", **extra: Any) -> None:
        if not persist:
            return
        payload = {
            "user_id": user_id,
            "question": question,
            "current_node": node,
            "status": status,
            "agent_trace": trace,
            **extra,
        }
        await store.update(session_id, **payload)

    await _set_node("router", status="running")

    # --- Router ---
    routed = await run_router(question, provider=provider)
    trace.append(
        AgentTraceStep(agent="router", action="classify", detail=routed).model_dump()
    )
    if persist:
        write_audit(
            session_id=session_id,
            event_type="agent_router",
            agent="router",
            user_id=user_id,
            detail=routed,
        )
    await _set_node("researcher")

    # --- Researcher ---
    hits = await run_researcher(
        routed["search_query"], knowledge=knowledge, top_k=top_k
    )
    research_detail = {
        "search_query": routed["search_query"],
        "hit_count": len(hits),
        "titles": [h.get("title") for h in hits],
        "filenames": [h.get("filename") for h in hits],
    }
    trace.append(
        AgentTraceStep(
            agent="researcher", action="hybrid_search", detail=research_detail
        ).model_dump()
    )
    if persist:
        write_audit(
            session_id=session_id,
            event_type="agent_researcher",
            agent="researcher",
            user_id=user_id,
            detail=research_detail,
        )
    await _set_node("analyst")

    # --- Analyst ---
    analyzed = await run_analyst(
        question, intent=routed["intent"], hits=hits, provider=provider
    )
    answer = analyzed["answer"]
    citations = analyzed["citations"]
    trace.append(
        AgentTraceStep(
            agent="analyst",
            action="generate_answer",
            detail={
                "materials_used": analyzed["materials_used"],
                "citation_count": len(citations),
                "intent": routed["intent"],
            },
        ).model_dump()
    )

    action_plan: dict[str, Any] | None = None
    guard_result: dict[str, Any] | None = None
    pending_action: dict[str, Any] | None = None
    note: str | None = None
    final_status = "completed"
    final_node = "done"

    # --- Executor + Guard（仅 action）---
    if enable_actions and routed["intent"] == "action":
        await _set_node("executor")
        action_plan = await run_executor(
            question, answer=answer, hits=hits, provider=provider
        )
        trace.append(
            AgentTraceStep(
                agent="executor",
                action="draft_action_plan",
                detail={
                    "action_type": action_plan.get("action_type"),
                    "title": action_plan.get("title"),
                    "ticket_count": len(action_plan.get("tickets") or []),
                },
            ).model_dump()
        )
        if persist:
            write_audit(
                session_id=session_id,
                event_type="agent_executor",
                agent="executor",
                user_id=user_id,
                detail={
                    "action_type": action_plan.get("action_type"),
                    "action_id": action_plan.get("action_id"),
                },
            )

        await _set_node("critic_guard")
        guard_result = run_guard(question, action_plan)
        trace.append(
            AgentTraceStep(
                agent="critic_guard",
                action="review",
                detail=guard_result,
            ).model_dump()
        )
        if persist:
            write_audit(
                session_id=session_id,
                event_type="agent_guard",
                agent="critic_guard",
                user_id=user_id,
                detail=guard_result,
            )

        if guard_result.get("allowed"):
            pending_action = {
                "action_id": action_plan["action_id"],
                "action_type": action_plan["action_type"],
                "title": action_plan["title"],
                "summary": action_plan["summary"],
                "tickets": action_plan.get("tickets") or [],
                "policy_notes": action_plan.get("policy_notes") or [],
            }
            final_status = "awaiting_confirmation"
            final_node = "awaiting_confirmation"
            note = "写操作待确认：请调用 confirm 后才会创建工单。"
            answer = (
                f"{answer}\n\n"
                f"【待确认行动】{pending_action['title']}\n"
                f"{pending_action['summary']}\n"
                f"（确认前不会写入工单）"
            )
        else:
            final_status = "blocked"
            final_node = "blocked"
            note = str(guard_result.get("reason") or "行动被 Guard 拦截")
            answer = f"{answer}\n\n【行动已拦截】{note}"
            # 确保不保留可执行 tickets
            if action_plan:
                action_plan = {**action_plan, "tickets": []}

    result: dict[str, Any] = {
        "session_id": session_id,
        "intent": routed["intent"],
        "question": question,
        "answer": answer,
        "citations": citations,
        "agent_trace": trace,
        "note": note,
        "action_plan": action_plan,
        "guard": guard_result,
        "pending_action": pending_action,
        "status": final_status,
    }

    if persist:
        event = "qa_complete"
        if final_status == "awaiting_confirmation":
            event = "action_pending"
        elif final_status == "blocked":
            event = "action_blocked"
        write_audit(
            session_id=session_id,
            event_type=event,
            agent="analyst" if routed["intent"] != "action" else "critic_guard",
            user_id=user_id,
            detail={
                "intent": routed["intent"],
                "status": final_status,
                "action_type": (action_plan or {}).get("action_type"),
                "citation_count": len(citations),
            },
        )
        await store.update(
            session_id,
            user_id=user_id,
            question=question,
            current_node=final_node,
            status=final_status,
            intent=routed["intent"],
            answer=answer,
            citations=citations,
            agent_trace=trace,
            note=note,
            action_plan=action_plan,
            pending_action=pending_action,
            guard=guard_result,
        )

    return result
