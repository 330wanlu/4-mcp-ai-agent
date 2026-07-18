"""Agent 流水线：Memory → Router → Researcher → Analyst → Guard →（action）Executor。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from ka_common.schema import AgentTraceStep
from ka_llm import ChatProvider, get_llm_provider
from ka_mcp_clients import KnowledgeMcpClient, MemoryMcpClient
from ka_orchestrator.agents import (
    run_analyst,
    run_answer_guard,
    run_executor,
    run_guard,
    run_researcher,
    run_router,
)
from ka_orchestrator.audit import write_audit
from ka_orchestrator.redis_state import SessionStore


def _build_memory_context(
    session_mem: dict[str, Any],
    user_pref: dict[str, Any],
) -> str:
    parts: list[str] = []
    summary = (session_mem or {}).get("summary") or ""
    if summary:
        parts.append(f"历史摘要: {summary}")
    prefs = (user_pref or {}).get("preferences") or {}
    notes = (user_pref or {}).get("notes") or ""
    if prefs:
        parts.append(f"用户偏好: {prefs}")
    if notes:
        parts.append(f"偏好备注: {notes}")
    return "\n".join(parts)


def _summarize_turn(question: str, answer: str, intent: str, status: str) -> str:
    q = (question or "").strip().replace("\n", " ")
    a = (answer or "").strip().replace("\n", " ")
    if len(q) > 80:
        q = q[:80] + "…"
    if len(a) > 160:
        a = a[:160] + "…"
    return f"[{intent}/{status}] Q: {q} | A: {a}"


async def run_qa_pipeline(
    question: str,
    *,
    session_id: str | None = None,
    user_id: str = "local-dev",
    top_k: int = 5,
    provider: ChatProvider | None = None,
    knowledge: KnowledgeMcpClient | None = None,
    memory: MemoryMcpClient | None = None,
    store: SessionStore | None = None,
    persist: bool = True,
    enable_actions: bool = True,
) -> dict[str, Any]:
    """问答闭环；intent=action 时进入 Executor+Guard，确认前不写 tickets。"""
    session_id = session_id or str(uuid4())
    provider = provider or get_llm_provider()
    knowledge = knowledge or KnowledgeMcpClient(mode="local")
    memory = memory or MemoryMcpClient(mode="local")
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

    await _set_node("memory", status="running")

    # --- Memory 读取 ---
    session_mem = await memory.get_session_summary(session_id)
    user_pref = await memory.get_user_preference(user_id)
    memory_context = _build_memory_context(session_mem, user_pref)
    mem_detail = {
        "session_found": bool(session_mem.get("found")),
        "pref_found": bool(user_pref.get("found")),
        "has_context": bool(memory_context),
    }
    trace.append(
        AgentTraceStep(agent="memory", action="load", detail=mem_detail).model_dump()
    )
    if persist:
        write_audit(
            session_id=session_id,
            event_type="agent_memory_load",
            agent="memory",
            user_id=user_id,
            detail=mem_detail,
        )

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
        question,
        intent=routed["intent"],
        hits=hits,
        provider=provider,
        memory_context=memory_context or None,
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
    answer_guard_result: dict[str, Any] | None = None
    pending_action: dict[str, Any] | None = None
    note: str | None = None
    final_status = "completed"
    final_node = "done"

    # --- Answer Guard ---
    # qa/compare 必检；intent=action 但未开启行动时也检（避免跳过降级）
    run_answer_check = routed["intent"] != "action" or not enable_actions
    if run_answer_check:
        await _set_node("critic_guard")
        answer_guard_result = run_answer_guard(
            question=question,
            answer=answer,
            citations=citations,
            hits=hits,
            intent=routed["intent"] if routed["intent"] != "action" else "qa",
        )
        guard_result = answer_guard_result
        trace.append(
            AgentTraceStep(
                agent="critic_guard",
                action="review_answer",
                detail=answer_guard_result,
            ).model_dump()
        )
        if persist:
            write_audit(
                session_id=session_id,
                event_type="agent_guard",
                agent="critic_guard",
                user_id=user_id,
                detail=answer_guard_result,
            )
        if not answer_guard_result.get("allowed"):
            answer = str(answer_guard_result.get("degraded_answer") or answer)
            citations = []
            final_status = "degraded"
            final_node = "degraded"
            note = str(answer_guard_result.get("reason") or "答案已降级")

    # --- Executor + Action Guard（仅 action，且未被答案质检降级）---
    if (
        enable_actions
        and routed["intent"] == "action"
        and final_status != "degraded"
    ):
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
            if action_plan:
                action_plan = {**action_plan, "tickets": []}

    # --- Memory 写回 ---
    turn_summary = _summarize_turn(question, answer, routed["intent"], final_status)
    prev_summary = (session_mem.get("summary") or "").strip()
    new_summary = (
        f"{prev_summary}\n{turn_summary}".strip()
        if prev_summary
        else turn_summary
    )
    # 摘要截断
    if len(new_summary) > 2000:
        new_summary = new_summary[-2000:]
    mem_saved = await memory.upsert_session_summary(
        session_id,
        summary=new_summary,
        user_id=user_id,
        append_turn={
            "question": question,
            "intent": routed["intent"],
            "status": final_status,
            "citation_count": len(citations),
        },
        meta={"last_status": final_status, "last_intent": routed["intent"]},
    )
    # 轻量偏好：记录最近关注域
    domain_hint = None
    for kw, domain in (
        ("年假", "leave"),
        ("请假", "leave"),
        ("差旅", "travel"),
        ("出差", "travel"),
        ("报销", "reimbursement"),
        ("住宿", "travel"),
    ):
        if kw in question:
            domain_hint = domain
            break
    if domain_hint:
        await memory.upsert_user_preference(
            user_id,
            preferences={"last_domain": domain_hint},
            merge=True,
        )
    trace.append(
        AgentTraceStep(
            agent="memory",
            action="upsert",
            detail={
                "session_id": session_id,
                "summary_len": len(new_summary),
                "upserted": bool(mem_saved.get("upserted")),
            },
        ).model_dump()
    )

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
        "answer_guard": answer_guard_result,
        "pending_action": pending_action,
        "status": final_status,
        "memory": {
            "summary": new_summary,
            "preferences": (user_pref.get("preferences") or {}),
        },
    }

    if persist:
        event = "qa_complete"
        if final_status == "awaiting_confirmation":
            event = "action_pending"
        elif final_status == "blocked":
            event = "action_blocked"
        elif final_status == "degraded":
            event = "qa_degraded"
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
            memory=result["memory"],
        )

    return result
