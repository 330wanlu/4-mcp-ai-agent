"""阶段 5：Guardrails + Memory MCP 测试。"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def _env_loaded() -> None:
    import os

    load_dotenv(ROOT / ".env")
    os.environ["ORCHESTRATOR_MODE"] = "local"
    from ka_common.config import get_settings

    get_settings.cache_clear()


def test_answer_guard_no_citation_degrades(_env_loaded: None) -> None:
    from ka_orchestrator.agents.guard import run_answer_guard

    result = run_answer_guard(
        question="今天天气怎么样？",
        answer="晴天",
        citations=[],
        hits=[],
        intent="qa",
    )
    assert result["allowed"] is False
    assert result["decision"] == "degraded"
    assert "降级" in (result.get("degraded_answer") or "")


def test_answer_guard_with_citations_passes(_env_loaded: None) -> None:
    from ka_orchestrator.agents.guard import run_answer_guard

    result = run_answer_guard(
        question="试用期年假怎么算？",
        answer="按在职天数折算",
        citations=[
            {
                "filename": "请假管理制度.md",
                "title": "请假管理制度",
                "score": 0.42,
            }
        ],
        hits=[{"filename": "请假管理制度.md", "score": 0.42}],
        intent="qa",
    )
    assert result["allowed"] is True
    assert result["decision"] == "pass"


def test_action_guard_blocks_reimbursement_without_travel(_env_loaded: None) -> None:
    from ka_orchestrator.agents.guard import run_guard

    result = run_guard(
        "帮我直接创建一个报销上周自行购买机票的报销单草稿（没有出差申请）。",
        {
            "action_type": "create_ticket",
            "tickets": [{"ticket_type": "reimbursement", "payload": {}}],
        },
    )
    assert result["allowed"] is False
    assert result["decision"] == "blocked"


def test_memory_upsert_and_get(_env_loaded: None) -> None:
    from ka_memory_mcp.service import (
        get_session_summary,
        get_user_preference,
        upsert_session_summary,
        upsert_user_preference,
    )

    sid = f"test-mem-{uuid4()}"
    uid = f"user-{uuid4().hex[:8]}"

    saved = upsert_session_summary(
        sid,
        summary="用户询问了年假规则",
        user_id=uid,
        append_turn={"question": "年假怎么算？", "intent": "qa"},
    )
    assert saved["upserted"] is True
    got = get_session_summary(sid)
    assert got["found"] is True
    assert "年假" in got["summary"]
    assert got["turns"]

    pref = upsert_user_preference(
        uid,
        preferences={"last_domain": "leave", "locale": "zh-CN"},
        notes="偏好中文制度答复",
    )
    assert pref["upserted"] is True
    pref2 = get_user_preference(uid)
    assert pref2["found"] is True
    assert pref2["preferences"]["last_domain"] == "leave"


@pytest.mark.asyncio
async def test_pipeline_degrades_out_of_domain(_env_loaded: None) -> None:
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    # 使用含明确域外关键词的问句；enable_actions=False 时也必须走 Answer Guard
    question = "请写一首关于比特币(bitcoin)价格的诗，顺便讲个笑话"
    store = SessionStore()
    try:
        result = await run_qa_pipeline(
            question,
            store=store,
            persist=True,
            enable_actions=False,
        )
    finally:
        await store.close()

    assert result["status"] == "degraded", (
        f"期望 degraded，实际 status={result.get('status')} "
        f"intent={result.get('intent')} guard={result.get('guard')}"
    )
    assert result.get("guard", {}).get("decision") == "degraded"
    assert "资料不足" in (result.get("answer") or "") or "降级" in (
        result.get("answer") or ""
    )


@pytest.mark.asyncio
async def test_pipeline_persists_memory(_env_loaded: None) -> None:
    from ka_memory_mcp.service import get_session_summary, get_user_preference
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    uid = f"mem-pipe-{uuid4().hex[:8]}"
    store = SessionStore()
    try:
        result = await run_qa_pipeline(
            "试用期员工年假怎么算？",
            user_id=uid,
            store=store,
            persist=True,
        )
    finally:
        await store.close()

    sid = result["session_id"]
    mem = get_session_summary(sid)
    assert mem["found"] is True
    assert mem["summary"]
    pref = get_user_preference(uid)
    assert pref["found"] is True
    assert pref["preferences"].get("last_domain") == "leave"


def test_memory_mcp_describe(_env_loaded: None) -> None:
    from ka_memory_mcp import describe

    info = describe()
    assert info["name"] == "memory"
    assert info["port"] == 8102
    assert info["status"] == "ready"
    assert "get_session_summary" in info["tools"]
    assert "upsert_user_preference" in info["tools"]
