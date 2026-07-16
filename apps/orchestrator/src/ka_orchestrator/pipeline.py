"""问答流水线：Router → Researcher → Analyst（阶段 2，无 Executor）。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from ka_common.schema import AgentTraceStep
from ka_llm import ChatProvider, get_llm_provider
from ka_mcp_clients import KnowledgeMcpClient
from ka_orchestrator.agents import run_analyst, run_researcher, run_router
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
) -> dict[str, Any]:
    """执行最小 Agent Graph 问答闭环，返回 answer / citations / agent_trace。"""
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
        AgentTraceStep(
            agent="router",
            action="classify",
            detail=routed,
        ).model_dump()
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
            agent="researcher",
            action="hybrid_search",
            detail=research_detail,
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

    # 阶段 2：action 意图仅标注，不执行写操作
    note = None
    if routed["intent"] == "action":
        note = "阶段2暂不执行写操作；将在阶段4由 Executor + 确认闸门处理。"

    result: dict[str, Any] = {
        "session_id": session_id,
        "intent": routed["intent"],
        "question": question,
        "answer": answer,
        "citations": citations,
        "agent_trace": trace,
        "note": note,
    }

    if persist:
        write_audit(
            session_id=session_id,
            event_type="qa_complete",
            agent="analyst",
            user_id=user_id,
            detail={
                "intent": routed["intent"],
                "citation_count": len(citations),
                "answer_preview": answer[:240],
                "filenames": [c.get("filename") for c in citations],
            },
        )
        await store.update(
            session_id,
            user_id=user_id,
            question=question,
            current_node="done",
            status="completed",
            intent=routed["intent"],
            answer=answer,
            citations=citations,
            agent_trace=trace,
            note=note,
        )

    return result
