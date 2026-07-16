"""阶段 4：行动计划 + 确认闸门测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def _env_loaded() -> None:
    from dotenv import load_dotenv
    import os

    load_dotenv(ROOT / ".env")
    os.environ["ORCHESTRATOR_MODE"] = "local"
    from ka_common.config import get_settings

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_gate_no_ticket_before_confirm(_env_loaded: None) -> None:
    from ka_business_mcp.service import count_tickets
    from ka_orchestrator.confirmation import confirm_pending_action
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    store = SessionStore()
    try:
        result = await run_qa_pipeline(
            "按差旅政策起草一趟上海出差申请，并创建待办提醒我提交审批。",
            store=store,
            persist=True,
        )
        sid = result["session_id"]
        assert result["status"] == "awaiting_confirmation"
        assert result.get("pending_action")
        assert result["action_plan"]["action_type"] == "create_travel_draft_and_todo"
        assert count_tickets(session_id=sid) == 0

        confirmed = await confirm_pending_action(sid, store=store)
        assert confirmed["ok"] is True
        assert count_tickets(session_id=sid) >= 1

        from ka_common.db.models import AuditLog
        from ka_common.db.session import session_scope

        with session_scope() as session:
            rows = session.scalars(
                select(AuditLog).where(AuditLog.session_id == sid)
            ).all()
            types = {r.event_type for r in rows}
        assert "action_execute" in types
        assert "action_pending" in types
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_gate_block_reimbursement_without_travel(_env_loaded: None) -> None:
    from ka_business_mcp.service import count_tickets
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    store = SessionStore()
    try:
        result = await run_qa_pipeline(
            "帮我直接创建一个「报销上周自行购买机票」的报销单草稿（没有出差申请）。",
            store=store,
            persist=True,
        )
        sid = result["session_id"]
        assert result["status"] == "blocked"
        assert result["action_plan"]["action_type"] == "refuse_or_require_travel_order"
        assert count_tickets(session_id=sid) == 0
        assert result.get("pending_action") is None
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_reject_clears_pending_no_tickets(_env_loaded: None) -> None:
    from ka_business_mcp.service import count_tickets
    from ka_orchestrator.confirmation import reject_pending_action
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    store = SessionStore()
    try:
        result = await run_qa_pipeline(
            "我是 7 月入职的试用期员工，想请 2 天年假，请按制度生成请假申请草稿并创建待办。",
            store=store,
            persist=True,
        )
        sid = result["session_id"]
        assert result["status"] == "awaiting_confirmation"
        rejected = await reject_pending_action(sid, store=store, reason="user_cancel")
        assert rejected["ok"] is True
        assert count_tickets(session_id=sid) == 0

        from ka_common.db.models import AuditLog
        from ka_common.db.session import session_scope

        with session_scope() as session:
            types = {
                r.event_type
                for r in session.scalars(
                    select(AuditLog).where(AuditLog.session_id == sid)
                ).all()
            }
        assert "action_reject" in types
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_golden_action_types_at_least_three(_env_loaded: None) -> None:
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    data = json.loads(
        (ROOT / "data" / "golden_set" / "golden_set.json").read_text(encoding="utf-8")
    )
    store = SessionStore()
    hits = 0
    failures: list[str] = []
    try:
        for item in data["actions"]:
            result = await run_qa_pipeline(item["task"], store=store, persist=True)
            got = (result.get("action_plan") or {}).get("action_type")
            if got == item["expected_action_type"]:
                hits += 1
            else:
                failures.append(f"{item['id']} expected={item['expected_action_type']} got={got}")
    finally:
        await store.close()
    assert hits >= 3, f"action_type 命中 {hits}/5 < 3；失败: {failures}"


def test_api_pending_confirm_flow(_env_loaded: None) -> None:
    from ka_business_mcp.service import count_tickets
    from ka_api.main import create_app

    client = TestClient(create_app())
    created = client.post("/chat/sessions", json={"title": "action"}).json()
    sid = created["session_id"]

    posted = client.post(
        f"/chat/sessions/{sid}/messages",
        json={
            "content": "下周出差上海期间要请客户吃饭，帮我开一张「报销注意事项」待办工单，写清科目和补助影响。"
        },
    )
    assert posted.status_code == 200, posted.text
    assert count_tickets(session_id=sid) == 0

    pending = client.get(f"/chat/sessions/{sid}/pending-actions").json()
    assert pending["status"] == "awaiting_confirmation"
    assert pending["pending_actions"]

    confirmed = client.post(f"/chat/sessions/{sid}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["ok"] is True
    assert count_tickets(session_id=sid) >= 1


def test_orchestrator_graph_phase4(_env_loaded: None) -> None:
    from ka_orchestrator.main import create_app

    client = TestClient(create_app())
    graph = client.get("/graph").json()
    assert graph["phase"] == 4
    assert "executor" in graph["active_nodes"]
    assert "critic_guard" in graph["active_nodes"]
