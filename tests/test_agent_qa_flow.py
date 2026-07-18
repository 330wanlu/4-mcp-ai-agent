"""阶段 2：Agent 问答闭环测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def _env_loaded() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")


def _citation_hit(citations: list[dict], source_docs: list[str]) -> bool:
    if not citations or not source_docs:
        return False
    names: set[str] = set()
    titles = []
    for c in citations:
        if c.get("filename"):
            names.add(str(c["filename"]))
        if c.get("source_path"):
            names.add(Path(str(c["source_path"])).name)
        titles.append(str(c.get("title") or ""))
    title_blob = " ".join(titles)
    for doc in source_docs:
        stem = Path(doc).stem
        if doc in names or stem in names or (stem and stem in title_blob):
            return True
    return False


@pytest.mark.asyncio
async def test_chat_provider_basic(_env_loaded: None) -> None:
    from ka_llm import ChatMessage, get_llm_provider

    provider = get_llm_provider()
    text = await provider.chat(
        [ChatMessage(role="user", content="用一个汉字回答：猫")],
        temperature=0.1,
        max_tokens=64,
        thinking=False,
    )
    assert text
    assert len(text) < 200


@pytest.mark.asyncio
async def test_qa_pipeline_single_question(_env_loaded: None) -> None:
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    store = SessionStore()
    try:
        result = await run_qa_pipeline(
            "试用期员工年假怎么算？能不能请？",
            store=store,
            persist=True,
            top_k=5,
        )
    finally:
        await store.close()

    assert result["session_id"]
    assert result["answer"]
    assert result["citations"], "应有引用"
    agents = [s["agent"] for s in result["agent_trace"]]
    for required in ("memory", "router", "researcher", "analyst", "critic_guard"):
        assert required in agents, f"缺少 agent: {required}, got={agents}"
    assert result["status"] in ("completed", "degraded")

    # Redis
    store2 = SessionStore()
    try:
        state = await store2.load(result["session_id"])
    finally:
        await store2.close()
    assert state is not None
    assert state.get("status") in ("completed", "degraded")
    assert state.get("current_node") in ("done", "degraded")

    # audit
    from ka_common.db.models import AuditLog
    from ka_common.db.session import session_scope

    with session_scope() as session:
        rows = session.scalars(
            select(AuditLog).where(AuditLog.session_id == result["session_id"])
        ).all()
        types = {r.event_type for r in rows}
    assert "qa_complete" in types
    assert "agent_router" in types
    assert "agent_researcher" in types


@pytest.mark.asyncio
async def test_golden_qa_citation_ratio(_env_loaded: None) -> None:
    """黄金问答约 7/10 有合理引用。"""
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    data = json.loads(
        (ROOT / "data" / "golden_set" / "golden_set.json").read_text(encoding="utf-8")
    )
    items = data["qa"]
    store = SessionStore()
    hits = 0
    failures: list[str] = []
    try:
        for item in items:
            result = await run_qa_pipeline(
                item["question"],
                store=store,
                persist=True,
                top_k=5,
            )
            ok = _citation_hit(result.get("citations") or [], item.get("source_docs") or [])
            if ok:
                hits += 1
            else:
                failures.append(
                    f"{item['id']} expected={item['source_docs']} "
                    f"got={[c.get('filename') or c.get('title') for c in result.get('citations') or []]}"
                )
    finally:
        await store.close()

    assert hits >= 7, f"引用命中 {hits}/10 < 7；失败: {failures}"


def test_orchestrator_http_shape(_env_loaded: None) -> None:
    from fastapi.testclient import TestClient

    from ka_orchestrator.main import create_app

    client = TestClient(create_app())
    assert client.get("/health").json()["status"] == "ok"
    graph = client.get("/graph").json()
    assert graph["phase"] == 5
    assert "router" in graph["active_nodes"]
    assert "memory" in graph["active_nodes"]
    assert "executor" in graph["active_nodes"]
    assert "critic_guard" in graph["active_nodes"]
